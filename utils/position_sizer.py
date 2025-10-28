from typing import Any, Dict, Literal, Optional

from utils.ib_whatif import whatif_margins


def compute_size(
    symbol: str,
    risk_cap_cad: float,
    kelly_fraction: float = 1.0,
    use: Literal["init", "maint"] = "init",
    lot_size: int = 1,
    safety_buffer_pct: float = 0.02,  # +2% safety on margin/unit
    max_qty: Optional[int] = None,
) -> Dict[str, Any]:
    assert risk_cap_cad >= 0, "risk_cap_cad must be >= 0"
    assert 0 <= kelly_fraction <= 1.0, "kelly_fraction must be in [0,1]"
    assert lot_size >= 1, "lot_size must be >= 1"
    assert safety_buffer_pct >= 0

    pv = whatif_margins(symbol=symbol)  # 1-share market preview
    init = pv.get("initMargin")
    maint = pv.get("maintMargin")

    margin_per_unit = (init if use == "init" else maint) or (maint if use == "init" else init)
    if not margin_per_unit or margin_per_unit <= 0:
        raise RuntimeError(f"Bad margin preview for {symbol}: {pv}")

    margin_per_unit *= 1.0 + safety_buffer_pct

    raw_qty = (risk_cap_cad / margin_per_unit) * float(kelly_fraction)
    qty = max(0, (int(raw_qty) // lot_size) * lot_size)
    if max_qty is not None:
        qty = min(qty, max_qty)

    return {
        "symbol": symbol,
        "qty": qty,
        "margin_per_unit_buffered": margin_per_unit,
        "risk_cap_cad": risk_cap_cad,
        "kelly_fraction": kelly_fraction,
        "lot_size": lot_size,
        "safety_buffer_pct": safety_buffer_pct,
        "preview": pv,
    }
