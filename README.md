# TradingView Connector (Cloud-ready)

FastAPI webhook to receive TradingView alerts and route them to your trading executors (IBKR/Bybit).

## Endpoints
- `GET /` — health check
- `POST /tv-webhook` — receive alerts (expects JSON with at least `symbol`, `side`, `entry`)
- `POST /force-close` — stub for closing all positions after force-close time

## Local run
```bash
pip install -r requirements.txt
python tv_webhook.py
```

## Render.com deployment (recommended)
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn tv_webhook:app --host 0.0.0.0 --port $PORT`

## Example TradingView JSON (Message field)
For a BUY alert:
```json
{"symbol":"{{ticker}}","tf":"{{interval}}","side":"BUY","entry":{{close}}}
```

For a SELL alert:
```json
{"symbol":"{{ticker}}","tf":"{{interval}}","side":"SELL","entry":{{close}}}
```
