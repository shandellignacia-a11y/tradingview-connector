import os
import json
import logging
from pathlib import Path
from typing import Optional, Literal

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field, validator
from ib_insync import IB, Stock, MarketOrder, util

# =============== Config & Logging ===============
from dotenv import load_dotenv
load_dotenv()

IB_HOST = os.getenv("IB_HOST", "127.0.0.1")
IB_PORT = int(os.getenv("IB_PORT", "7497"))   # Paper: 7497, Live: 7496
IB_CLIENT_ID = int(os.getenv("IB_CLIENT_ID", "19"))  # kies vrij ID
DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "USD")
ROUTING = os.getenv("ROUTING", "SMART")  # of "LSE" etc.
REQUIRE_TOKEN = os.getenv("REQUIRE_TOKEN", "false").lower() == "true"
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "set-a-strong-token-if-required")

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "tv_webhook.log", encoding="utf-8")
    ],
)
logger = logging.getLogger("tv_webhook")

# =============== FastAPI ===============
app = FastAPI(title="TradingView → IBKR Webhook", version="1.0.0")

# =============== Models ===============
class TVAlert(BaseModel):
    # Variant 1: trading signal
    symbol: Optional[str] = Field(None, description="Ticker, bv. AAPL of AMS:ASML")
    tf: Optional[str] = Field(None, description="TradingView {{interval}}")
    side: Optional[Literal["BUY", "SELL"]] = None
    entry: Optional[str] = None
    qty: Optional[float] = Field(None, description="Aantal stuks")
    # Variant 2: command
    cmd: Optional[Literal["flatten_all"]] = None

    @validator("qty")
    def _qty_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("qty must be > 0")
        return v

# =============== IBKR Client (lazy singleton) ===============
_ib: Optional[IB] = None

def get_ib() -> IB:
    global _ib
    if _ib is not None and _ib.isConnected():
        return _ib
    ib = IB()
    logger.info(f"Connecting to IB @ {IB_HOST}:{IB_PORT} (clientId={IB_CLIENT_ID}) ...")
    ib.connect(IB_HOST, IB_PORT, clientId=IB_CLIENT_ID, timeout=5)
    logger.info("Connected to IB.")
    util.startLoop()  # ensure event loop integration if needed
    _ib = ib
    return _ib

# =============== Helpers ===============
def parse_symbol(symbol: str):
    """
    Accepts 'AAPL' or 'NASDAQ:AAPL' or 'AMS:ASML'.
    Returns (exchange, localSymbol).
    """
    if ":" in symbol:
        exch, local = symbol.split(":", 1)
        return exch.upper(), local.upper()
    return ROUTING, symbol.upper()

def place_market_order(symbol: str, action: Literal["BUY", "SELL"], qty: float):
    ib = get_ib()
    exch, local = parse_symbol(symbol)
    logger.info(f"Placing {action} {qty} {local} via {exch} ...")

    contract = Stock(local, exchange=exch if exch != "SMART" else "SMART", currency=DEFAULT_CURRENCY)
    ib.qualifyContracts(contract)
    order = MarketOrder(action, qty)
    trade = ib.placeOrder(contract, order)
    logger.info(f"Submitted orderId={trade.order.orderId} status={trade.orderStatus.status}")
    # Wait a tiny moment for status update (non-blocking friendly)
    ib.sleep(0.2)
    return {
        "orderId": trade.order.orderId,
        "status": trade.orderStatus.status,
        "filled": trade.orderStatus.filled or 0.0,
        "remaining": trade.orderStatus.remaining or qty,
        "avgFillPrice": trade.orderStatus.avgFillPrice or 0.0,
        "symbol": local,
        "exchange": exch,
    }

def flatten_all_positions():
    ib = get_ib()
    ib.sleep(0.1)
    positions = ib.positions()  # list of Position(account, contract, position, avgCost)
    results = []
    if not positions:
        logger.info("No open positions to flatten.")
        return {"flattened": 0, "details": []}

    for p in positions:
        pos = float(p.position)
        if pos == 0:
            continue
        local = p.contract.localSymbol or p.contract.symbol
        exch = p.contract.primaryExchange or p.contract.exchange or ROUTING
        action = "SELL" if pos > 0 else "BUY"
        qty = abs(pos)
        logger.info(f"Flattening {local} on {exch}: pos={pos} -> {action} {qty}")
        # Ensure contract is tradable as Stock (fallback to symbol)
        contract = Stock(local, exchange="SMART", currency=DEFAULT_CURRENCY)
        ib.qualifyContracts(contract)
        order = MarketOrder(action, qty)
        trade = ib.placeOrder(contract, order)
        ib.sleep(0.2)
        results.append({
            "symbol": local,
            "action": action,
            "qty": qty,
            "orderId": trade.order.orderId,
            "status": trade.orderStatus.status,
        })

    return {"flattened": len(results), "details": results}

def ensure_auth(x_token: Optional[str]):
    if REQUIRE_TOKEN and (not x_token or x_token != AUTH_TOKEN):
        raise HTTPException(status_code=401, detail="Unauthorized")

# =============== Routes ===============
@app.get("/")
def root():
    return {"ok": True, "service": "TV→IBKR webhook", "version": "1.0.0"}

@app.post("/tv-webhook")
async def tv_webhook(
    payload: TVAlert,
    request: Request,
    x_token: Optional[str] = Header(default=None, convert_underscores=False),
):
    ensure_auth(x_token)

    # Raw body for logging
    try:
        raw = await request.body()
        logger.info(f"Incoming alert: {raw.decode('utf-8', 'ignore')}")
    except Exception:
        pass

    # Command path
    if payload.cmd == "flatten_all":
        try:
            res = flatten_all_positions()
            return {"ok": True, "mode": "cmd", "cmd": "flatten_all", "result": res}
        except Exception as e:
            logger.exception("Error in flatten_all")
            raise HTTPException(status_code=500, detail=f"flatten_all failed: {e}")

    # Trade signal path
    if not payload.symbol or not payload.side or not payload.qty:
        raise HTTPException(
            status_code=400,
            detail="Missing required fields for trade signal: symbol, side, qty.",
        )

    try:
        res = place_market_order(symbol=payload.symbol, action=payload.side, qty=float(payload.qty))
        return {
            "ok": True,
            "mode": "signal",
            "signal": {
                "symbol": payload.symbol,
                "side": payload.side,
                "qty": float(payload.qty),
                "tf": payload.tf,
                "entry": payload.entry,
            },
            "ib": res,
        }
    except Exception as e:
        logger.exception("Error placing order")
        raise HTTPException(status_code=500, detail=f"Order failed: {e}")
