from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/tv-webhook")
async def tv_webhook(request: Request):
    try:
        # --- RAW input log ---
        try:
            raw = await request.body()
            print(f"📥 RAW: {raw.decode('utf-8','ignore')}")
        except Exception as _e:
            print(f"📥 RAW: <unavailable> ({_e})")

        # JSON parsen
        data = await request.json()

        # --- Parsed log ---
        print(
            "[Webhook] Parsed:",
            "symbol=", data.get("symbol"),
            "side=",   data.get("side"),
            "tf=",     data.get("tf"),
            "entry=",  data.get("entry"),
        )

        # Basis data
        symbol = data.get("symbol")
        side   = data.get("side")
        entry  = float(data.get("entry", 0))
        tf     = data.get("tf")

        # Order sizing en targets (voorbeeld!)
        qty = max(1, int(10000 / entry))  # voorbeeld berekening
        tp  = round(entry * 1.02, 3)
        sl  = round(entry * 0.99, 3)

        # --- Order prep log ---
        print(f"🛠️ Order prep: symbol={symbol}, side={side}, qty={qty}, entry={entry}, tp={tp}, sl={sl}")

        # TODO: hier zou je echte broker-functie komen
        # bijv. ib.placeOrder(...) of bybit.place_order(...)
        print(f"📡 Sending order → broker (simulatie): {side} {qty} {symbol} @ {entry}")

        # Resultaat teruggeven
        result = {
            "ok": True,
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "entry": entry,
            "tp": tp,
            "sl": sl,
            "venue": "IBKR"
        }

        # --- Response log ---
        print(f"📤 Response: {result}")

        return result

    except Exception as e:
        print(f"[Error] {e}")
        return {"ok": False, "reason": str(e)}
