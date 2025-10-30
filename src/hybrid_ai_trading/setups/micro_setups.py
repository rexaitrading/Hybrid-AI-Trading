from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    import pandas as pd  # type: ignore
except Exception:
    pd = None

from ..runners.decision_schema import Decision
from ..runners.sizing import kelly_capped_qty


def _calc_orb_levels(bars_1m: "pd.DataFrame", orb_min: int = 5):
    head = bars_1m.iloc[:orb_min]
    hi = float(head["high"].max())
    lo = float(head["low"].min())
    rng = max(0.01, hi - lo)
    return hi, lo, rng


def detect_orb_break(
    symbol: str, last_price: float, bars_1m, micro: Dict[str, Any], g: Dict[str, Any]
) -> Optional[Decision]:
    if bars_1m is None or len(bars_1m) < int(g.get("orb_min", 5)):
        return None
    hi, lo, rng = _calc_orb_levels(bars_1m, orb_min=int(g.get("orb_min", 5)))
    # Long break
    if last_price is not None and hi is not None and last_price > hi:
        entry = float(last_price)
        stop = float(hi - 0.25 * rng)
        target = float(entry + 1.0 * rng)
        f_raw = 0.05
        qty = kelly_capped_qty(
            g.get("per_symbol_notional_cap", 250000.0),
            entry,
            f_raw,
            g.get("kelly_cap_by_regime", {}),
            regime="neutral",
        )
        return Decision(
            symbol=symbol,
            setup="ORB_Break",
            side="long",
            entry_px=entry,
            stop_px=stop,
            target_px=target,
            qty=qty,
            kelly_f=f_raw,
            regime="neutral",
            regime_conf=0.5,
            sentiment=0.0,
            sent_conf=0.5,
            price=micro.get("price"),
            bid=micro.get("bid"),
            ask=micro.get("ask"),
            bidSize=micro.get("bidSize"),
            askSize=micro.get("askSize"),
            volume=micro.get("volume"),
            reason="orb_break_long",
        )
    return None


def build_micro_decisions(
    symbols: List[str],
    snapshots: List[Dict[str, Any]],
    bars_1m_by_symbol: Dict[str, Any],
    g: Dict[str, Any],
) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    snap_map = {
        s["symbol"]: s for s in snapshots if isinstance(s, dict) and "symbol" in s
    }
    for s in symbols:
        snap = snap_map.get(s, {})
        price = snap.get("price")
        bars = bars_1m_by_symbol.get(s)
        dec: Optional[Decision] = detect_orb_break(s, price, bars, snap, g)
        if dec:
            items.append(dec.to_item())
    return items
