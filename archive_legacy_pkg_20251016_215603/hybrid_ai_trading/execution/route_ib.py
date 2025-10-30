from __future__ import annotations

import os
from dataclasses import dataclass

from ib_insync import IB, LimitOrder, Stock


@dataclass
class RiskConfig:
    equity: float
    per_symbol_bp: float  # bps of equity per trade (e.g., 20 = 0.20%)
    per_symbol_gross_cap: float  # % gross exposure cap per symbol (e.g., 15)
    allow_short: bool
    allow_margin: bool


def dollars_for_symbol(rc: RiskConfig, price: float) -> float:
    base = rc.equity * (rc.per_symbol_bp / 10000.0)
    cap = rc.equity * (rc.per_symbol_gross_cap / 100.0)
    return max(0.0, min(base, cap))


def size_from_dollars(dollars: float, px: float) -> int:
    if px <= 0 or dollars <= 0:
        return 0
    return max(1, int(dollars // px))


def place_entry(ib, symbol, side, last_px, rc):
    # DRY-RUN guard: skip placing real orders when DRY_RUN=1
    if os.environ.get("DRY_RUN", "0") == "1":
        print(f"[dry-run] {symbol} {side} (px~{last_px})", flush=True)
        return None
    # ... existing order build + ib.placeOrder(...) logic ...


def place_entry(
    ib: IB, symbol: str, side: str, px: float, rc: RiskConfig, limit_pad_bps: int = 5
):
    """
    Simple risk-aware entry as padded limit order.
    """
    qty_dollars = dollars_for_symbol(rc, px)
    qty = size_from_dollars(qty_dollars, px)
    if qty <= 0:
        return None

    if side == "SELL" and not rc.allow_short:
        return None

    pad = px * (limit_pad_bps / 10000.0)
    if side == "BUY":
        order = LimitOrder("BUY", qty, px + pad)
    elif side == "SELL":
        order = LimitOrder("SELL", qty, px - pad)
    else:
        return None

    contract = Stock(symbol, "SMART", "USD")
    return ib.placeOrder(contract, order)
