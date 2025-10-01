from fastapi import FastAPI, Request
import uvicorn

app = FastAPI()

@app.post("/tv-webhook")
async def tv_webhook(request: Request):
    try:
        data = await request.json()
        print(f"📩 RAW: {data}")

        # Parse data uit webhook
        symbol = data.get("symbol")
        side   = data.get("side")
        tf     = data.get("tf")
        entry  = float(data.get("entry", 0))

        print(f"[Webhook] Parsed: symbol={symbol} side={side} tf={tf} entry={entry}")

        # Order berekening (dummy logic)
        qty = 39  # testhoeveelheid
        tp = round(entry * 1.02, 3)
        sl = round(entry * 0.99, 3)

        print(f"📝 Order prep: symbol={symbol}, side={side}, qty={qty}, entry={entry}, tp={tp}, sl={sl}")

        # Order simulatie sturen
        print(f"📤 Sending order → broker (simulate): {side} {qty} {symbol} @ {entry}")

        # Dummy response (hier komt straks IBKR API respons)
        response = {
            "ok": True,
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "entry": entry,
            "tp": tp,
            "sl": sl,
            "venue": "IBKR"
        }

        # ✅ Extra logging
        if response.get("ok"):
            print(f"✅ ORDER SUCCEEDED: {side} {qty} {symbol} @ {entry}, TP {tp}, SL {sl}")
        else:
            print(f"❌ ORDER FAILED: {side} {qty} {symbol} @ {entry} – reason: {response}")

        return response

    except Exception as e:
        print(f"❌ ERROR processing webhook: {e}")
        return {"ok": False, "error": str(e)}


@app.get("/")
async def root():
    return {"status": "running", "service": "tv-webhook"}


if __name__ == "__main__":
    uvicorn.run("tv_webhook:app", host="0.0.0.0", port=8000)
