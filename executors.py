from typing import Literal

Side = Literal["BUY","SELL"]

def compute_position_size(account_equity: float, entry: float, sl: float, risk_frac: float) -> int:
    """Very simple position sizing based on per-unit risk."""
    risk_per_unit = abs(entry - sl)
    if risk_per_unit <= 0:
        return 0
    units = int((account_equity * risk_frac) / risk_per_unit)
    return max(units, 0)

# --- Replace these with your real integrations ---

def place_order_ibkr(symbol: str, side: Side, qty: int, entry: float, tp: float | None, sl: float | None):
    """Stub: integrate with your IBKR bot (NasdaqRaptor) here."""
    print(f"[IBKR] {side} {symbol} x{qty} @~{entry} TP={tp} SL={sl}")

def place_order_bybit(symbol: str, side: Side, qty: int, entry: float, tp: float | None, sl: float | None):
    """Stub: integrate with your Bybit bot here."""
    print(f"[BYBIT] {side} {symbol} x{qty} @~{entry} TP={tp} SL={sl}")
