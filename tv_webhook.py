from fastapi import FastAPI, Request, HTTPException
import uvicorn, json, os
from typing import Optional
from config import SHARED_TOKEN, FORCE_CLOSE, TZ
from router import route_signal
from datetime import datetime

app = FastAPI()

def token_ok(query: str) -> bool:
    if not SHARED_TOKEN:
        return True
    return query == SHARED_TOKEN

@app.get("/")
def health():
    return {"ok": True, "msg": "TV connector up"}

@app.post("/tv-webhook")
async def tv_webhook(request: Request, token: Optional[str] = None):
    if not token_ok(token or ""):
        raise HTTPException(status_code=401, detail="Invalid token")

    raw = await request.body()
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception:
        data = await request.json()

    # Required
    symbol = str(data.get("symbol", "")).upper()
    side   = str(data.get("side", "")).upper()
    entry  = float(data.get("entry", 0.0))

    # Optional
    tp     = data.get("tp", None)
    sl     = data.get("sl", None)
    rr     = float(data.get("rr", 2.0))
    atr    = data.get("atr", None)
    venue  = data.get("venue", None)

    if not symbol or side not in {"BUY","SELL"} or entry <= 0:
        raise HTTPException(status_code=400, detail="Missing/invalid symbol/side/entry")

    result = route_signal(symbol=symbol, side=side, entry=entry, venue=venue, tp=tp, sl=sl, rr=rr, atr=atr)
    return result

@app.post("/force-close")
async def force_close_all():
    # Stub: call your bot(s) to close all open positions after FORCE_CLOSE time
    now = datetime.now(TZ).timetz()
    if now > FORCE_CLOSE:
        # TODO: implement: close_all_positions()
        return {"ok": True, "action": "force_close_triggered"}
    return {"ok": False, "reason": "Not past force-close time yet."}

if __name__ == "__main__":
    # Use $PORT for Render/Heroku-style dynos
    port = int(os.getenv("PORT", "10000"))
    uvicorn.run("tv_webhook:app", host="0.0.0.0", port=port)
