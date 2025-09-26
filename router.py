from datetime import datetime
from typing import Optional, Tuple
from config import ALLOWED_SYMBOLS, DENY_SYMBOLS, DEFAULT_VENUE, RISK_PER_TRADE, MIN_QTY, NASDQ_OPEN, NASDQ_CLOSE, FORCE_CLOSE, TZ
from executors import compute_position_size, place_order_ibkr, place_order_bybit

def within_session(now: datetime) -> bool:
    t = now.astimezone(TZ).timetz()
    return (t >= NASDQ_OPEN and t <= NASDQ_CLOSE)

def derive_targets(entry: float, rr: float = 2.0, atr: Optional[float] = None, atr_mult: float = 2.0, side: str = "BUY") -> Tuple[Optional[float], Optional[float]]:
    """Derive TP/SL if not provided. Very simple: SL via ATR if given else 1% of entry; TP = RR * risk."""
    risk = (atr_mult * atr) if (atr and atr > 0) else (0.01 * entry)
    if side == "BUY":
        sl = entry - risk
        tp = entry + rr * risk
    else:
        sl = entry + risk
        tp = entry - rr * risk
    return tp, sl

def route_signal(
    symbol: str, side: str, entry: float,
    venue: Optional[str] = None,
    account_equity: float = 10_000.0,
    tp: Optional[float] = None,
    sl: Optional[float] = None,
    rr: float = 2.0,
    atr: Optional[float] = None
) -> dict:
    now = datetime.now(TZ)

    # Deny/allow logic
    if symbol in DENY_SYMBOLS:
        return {"ok": False, "reason": f"Symbol {symbol} on denylist."}
    if ALLOWED_SYMBOLS and symbol not in ALLOWED_SYMBOLS:
        return {"ok": False, "reason": f"Symbol {symbol} not in allowlist."}

    # Session check
    if not within_session(now):
        return {"ok": False, "reason": "Outside trading session."}

    # Derive TP/SL if needed
    if tp is None or sl is None:
        tp, sl = derive_targets(entry, rr=rr, atr=atr, side=side)

    # Position sizing
    qty = compute_position_size(account_equity, entry, sl, RISK_PER_TRADE)
    qty = max(qty, MIN_QTY)
    if qty <= 0:
        return {"ok": False, "reason": "Qty computed as 0; check SL/entry."}

    # Route to venue
    use_venue = (venue or DEFAULT_VENUE).upper()
    if use_venue == "IBKR":
        place_order_ibkr(symbol, side, qty, entry, tp, sl)
    elif use_venue == "BYBIT":
        place_order_bybit(symbol, side, qty, entry, tp, sl)
    else:
        return {"ok": False, "reason": f"Unknown venue {use_venue}"}

    return {"ok": True, "symbol": symbol, "side": side, "qty": qty, "entry": entry, "tp": tp, "sl": sl, "venue": use_venue}
