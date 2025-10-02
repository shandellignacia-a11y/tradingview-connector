# tv_webhook.py
# FastAPI webhook die TradingView alerts omzet naar IBKR orders (via ib_insync).
# Veilig / eenvoudig: MarketOrders, DAY. Optionele qty uit alert; anders DEFAULT_QTY.

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from ib_insync import IB, Stock, MarketOrder
import os
import asyncio
from typing import Optional
import time

app = FastAPI()

# ---- Config uit omgevingsvariabelen (met veilige defaults) ----
IB_HOST       = os.getenv("IB_HOST", "127.0.0.1")     # zelfde machine als IB Gateway/TWS
IB_PORT       = int(os.getenv("IB_PORT", "7497"))     # 7497 Paper, 7496/4002 Live
IB_CLIENT_ID  = int(os.getenv("IB_CLIENT_ID", "1"))
DEFAULT_QTY   = int(os.getenv("DEFAULT_QTY", "1"))
PRIMARY_EXCH  = os.getenv("PRIMARY_EXCHANGE", "NASDAQ")  # hint voor contract
CURRENCY      = os.getenv("CURRENCY", "USD")

# Eenvoudige de-bouncer zodat we niet dubbel schieten binnen een paar seconden
LAST_ORDER_TS = {}      # key: (symbol, side) -> epoch seconds
ORDER_COOLDOWN_SEC = 5  # minimaal 5s tussen identieke signalen

ib = IB()

async def ensure_connected():
    """Zorgt dat IB verbonden is (of wordt) en wacht kort op verbinding."""
    if not ib.isConnected():
        try:
            await ib.connectAsync(IB_HOST, IB_PORT, IB_CLIENT_ID, timeout=5)
        except Exception as e:
            return False, f"IB connect failed: {e}"
    return True, "connected"

def _contract_for_symbol(symbol: str):
    """
    Maak een SMART-route Stock contract. primaryExchange als hint voor routing/identify.
    IBKR resolve’t dit naar de juiste venue.
    """
    return Stock(symbol.upper(), 'SMART', CURRENCY, primaryExchange=PRIMARY_EXCH)

async def place_market_order(symbol: str, side: str, qty: int):
    """
    Plaats een MarketOrder (DAY). side: 'BUY' of 'SELL'.
    Wacht kort op fill/confirm, geef resultaat terug.
    """
    contract = _contract_for_symbol(symbol)
    action = 'BUY' if side.upper() == 'BUY' else 'SELL'
    order  = MarketOrder(action, qty)
    trade  = ib.placeOrder(contract, order)

    # Wacht (kort) op status; niet blokkeren voor altijd
    t0 = time.time()
    while not trade.isDone():
        await asyncio.sleep(0.25)
        if time.time() - t0 > 8:  # 8 seconden max wachten
            break
    status = trade.orderStatus.status
    return {
        "symbol": symbol,
        "side": action,
        "qty": qty,
        "status": status,
        "filled": trade.orderStatus.filled,
        "avgFillPrice": trade.orderStatus.avgFillPrice
    }

async def flatten_all_positions():
    """
    Sluit alle open posities met een MarketOrder (tegenovergestelde richting).
    Geeft per positie het resultaat terug.
    """
    results = []
    positions = ib.positions()  # synchronously available in ib_insync
    for pos in positions:
        symbol = pos.contract.symbol
        qty = abs(int(pos.position))
        if qty == 0:
            continue
        side = 'SELL' if pos.position > 0 else 'BUY'
        res = await place_market_order(symbol, side, qty)
        results.append(res)
    return results

@app.post("/tv-webhook")
async def tv_webhook(request: Request):
    # ---------- JSON ophalen ----------
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "reason": "Invalid JSON"}, status_code=400)

    # Command mode?
    cmd = (data.get("cmd") or "").lower().strip()
    if cmd == "flatten_all":
        ok, msg = await ensure_connected()
        if not ok:
            return JSONResponse({"ok": False, "reason": msg}, status_code=500)
        results = await flatten_all_positions()
        return JSONResponse({"ok": True, "action": "flatten_all", "results": results})

    # ---------- TradingView payload ----------
    symbol: Optional[str] = data.get("symbol")
    side:   Optional[str] = data.get("side")  # "BUY" / "SELL"
    qty_in  = data.get("qty")                 # optioneel, als je dat meestuurt
    entry   = data.get("entry")               # niet nodig voor MarketOrder, maar gelogd
    tf      = data.get("tf")

    # Validatie
    if not symbol or side not in ("BUY", "SELL"):
        return JSONResponse({"ok": False, "reason": "Missing or invalid symbol/side"}, status_code=400)

    # Rate-limit identieke signalen kort
    key = (symbol.upper(), side.upper())
    now = time.time()
    if key in LAST_ORDER_TS and (now - LAST_ORDER_TS[key]) < ORDER_COOLDOWN_SEC:
        return JSONResponse({"ok": True, "skipped": "cooldown", "symbol": symbol, "side": side})

    qty = None
    try:
        if qty_in is not None:
            # vanuit TV kan qty als string/float komen
            qty = int(float(qty_in))
    except Exception:
        qty = None
    if not qty or qty <= 0:
        qty = DEFAULT_QTY

    # ---------- Verbinden & order sturen ----------
    ok, msg = await ensure_connected()
    if not ok:
        return JSONResponse({"ok": False, "reason": msg}, status_code=500)

    try:
        result = await place_market_order(symbol, side, qty)
        LAST_ORDER_TS[key] = now
        return JSONResponse({
            "ok": True,
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "entryFromAlert": entry,
            "tf": tf,
            "ibResult": result
        })
    except Exception as e:
        return JSONResponse({"ok": False, "reason": f"Order failed: {e}"}, status_code=500)
