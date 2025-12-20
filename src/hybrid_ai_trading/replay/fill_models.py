from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Side = Literal["BUY", "SELL"]


@dataclass(frozen=True)
class FillResult:
    fill_price: float
    fee_usd: float
    slippage_usd: float


@dataclass(frozen=True)
class DeterministicFillModel:
    """
    Deterministic, reproducible fill model.
    - fee_bps: fixed fee in basis points
    - slip_bps: fixed slippage in basis points (applied against mid/price)
    """
    fee_bps: float = 1.0
    slip_bps: float = 2.0

    def fill(self, *, side: Side, qty: float, price: float) -> FillResult:
        px = float(price)
        q = float(qty)

        slip = (self.slip_bps / 1e4) * px
        fill_px = px + slip if side == "BUY" else px - slip

        fee = (self.fee_bps / 1e4) * abs(fill_px * q)
        slip_usd = abs((fill_px - px) * q)
        return FillResult(fill_price=fill_px, fee_usd=fee, slippage_usd=slip_usd)