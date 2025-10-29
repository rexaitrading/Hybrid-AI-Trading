from __future__ import annotations

from typing import Dict


def kelly_capped_qty(
    notional_cap: float,
    price: float,
    f_raw: float,
    kelly_cap_by_regime: Dict[str, float],
    regime: str,
) -> int:
    if price is None or price <= 0:
        return 0
    f_cap = min(float(kelly_cap_by_regime.get(regime, 0.05)), float(f_raw))
    target_notional = f_cap * notional_cap
    qty = int(max(0, target_notional // price))
    return qty
