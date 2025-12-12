from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from hybrid_ai_trading.microstructure import classify_micro_regime


RegimeLabel = Literal["GREEN", "CAUTION", "RED"]


@dataclass
class MicroGateDecision:
    allowed: bool
    regime: RegimeLabel
    reason: str


def micro_gate_for_symbol(symbol: str, ms_range_pct: float, est_spread_bps: float, est_fee_bps: float) -> MicroGateDecision:
    """
    Phase-2 micro gate decision for SPY/QQQ (can be extended).

    Returns:
      - allowed: False when regime is RED
      - regime: GREEN / CAUTION / RED
      - reason: short human-readable string
    """
    regime = classify_micro_regime(ms_range_pct, est_spread_bps, est_fee_bps)

    symbol = symbol.upper()
    base_reason = f"micro_regime={regime}, ms_range_pct={ms_range_pct}, cost_bps={est_spread_bps + est_fee_bps}"

    if symbol not in ("SPY", "QQQ"):
        # For now we do not gate other symbols here
        return MicroGateDecision(allowed=True, regime=regime, reason=base_reason + " (symbol not gated)")

    if regime == "RED":
        return MicroGateDecision(allowed=False, regime=regime, reason=base_reason + " (Phase-2 micro gate: RED)")

    # GREEN/CAUTION -> allowed, but reason still recorded
    return MicroGateDecision(allowed=True, regime=regime, reason=base_reason)
