from fastapi import FastAPI, Request
import json

app = FastAPI()

@app.post("/tv-webhook")
async def tv_webhook(request: Request):
    data = await request.json()
    print("📩 Webhook received:", data)   # <-- extra logregel
    return {"status": "ok", "received": data}
