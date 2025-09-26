from datetime import time, timezone, timedelta

# --- Symbols ---
ALLOWED_SYMBOLS = {"AAPL","MSFT","AVGO","NVDA"}   # adjust to your watchlist
DENY_SYMBOLS    = {"ASML","PRX","UNA"}            # example denylist; set to empty set() if not needed

# --- Default venue (route) ---
# Choose "IBKR" (for your Nasdaq bot) or "BYBIT" (for your crypto bot)
DEFAULT_VENUE = "IBKR"

# --- Risk / Position sizing ---
RISK_PER_TRADE = 0.005    # 0.5% of equity
MIN_QTY        = 1

# --- Trading session (Amsterdam time) ---
# Adjust for winter/summer if needed
TZ = timezone(timedelta(hours=2))  # CEST; in winter use +1
NASDQ_OPEN   = time(15, 30, tzinfo=TZ)
NASDQ_CLOSE  = time(22, 30, tzinfo=TZ)

# Force-close time (close all positions)
FORCE_CLOSE  = NASDQ_CLOSE

# --- Optional security token ---
# If set, require ?token=<value> on webhook calls
SHARED_TOKEN = ""
