from fastapi import FastAPI, Request, HTTPException
import json
from typing import Optional
from config import SHARED_TOKEN, TZ
from router import route_signal

app = FastAPI()

def token_ok(query: str) -> bool:
    return True if not SHARED_TOKEN else (query == SHARED_TOKEN)

@app.post("/tv-webhook")
async def tv_webhook(request: Request, token: Optional[str] = None):
    if not token_ok(token or ""):
        raise HTTPException(status_code=401, detail="Invalid token")

    raw = await request.body()
    body_txt = (raw or b"").decode("utf-8", errors="ignore").strip()
    ct = (request.headers.get("content-type") or "").lower()

    if not body_txt:
        # Geen body ontvangen (bv. Message in TV leeg)
        print("⚠️ Empty POST body from", request.client, "content-type:", ct)
        raise HTTPException(status_code=400, detail="Empty body. Set a JSON Message in your TradingView alert.")

    # Probeer JSON te parsen; zo niet, geef nette fout terug
    try:
        data = json.loads(body_txt)
    except Exception:
        print("⚠️ Non-JSON body:", body_txt[:200])
        raise HTTPException(status_code=400, detail=f"Body is not valid JSON (content-type={ct}).")

    print("📩 Webhook received:", data)

    # Vereiste velden
    symbol = str(data.get("symbol", "")).upper()
    side   = str(data.get("side", "")).upper()
    entry  = float(data.get("entry", 0.0))
    if not symbol or side not in {"BUY","SELL"} or entry <= 0:
        raise HTTPException(status_code=400, detail=f"Missing/invalid fields in JSON: {data}")

    # Optioneel
    tp = data.get("tp"); sl = data.get("sl")
    rr = float(data.get("rr", 2.0)); atr = data.get("atr")
    venue = data.get("venue")

    result = route_signal(symbol=symbol, side=side, entry=entry, venue=venue, tp=tp, sl=sl, rr=rr, atr=atr)
    return result
