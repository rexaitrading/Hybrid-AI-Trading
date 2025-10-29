from typing import Any, Dict, List, Tuple


def load_guardrails() -> Dict[str, Any]:
    """
    Default guardrails. Tune as needed.
    spread_bps_limit: max allowed spread in basis points relative to last/mid price.
    per_symbol_notional_cap: max notional used for sizing per symbol.
    kelly_cap_by_regime: cap raw Kelly f by regime.
    daily_loss_cap: stop trading if running daily PnL <= this (runner enforces).
    """
    return {
        "max_qty": 1000,
        "allow": set(),
        "deny": set(),
        "spread_bps_limit": 8.0,
        "spread_bps_limit_by_symbol": {"AAPL": 6.0, "MSFT": 7.0, "TSLA": 10.0},
        "per_symbol_notional_cap": 250000.0,
        "kelly_cap_by_regime": {"bull": 0.08, "neutral": 0.04, "bear": 0.02},
        "daily_loss_cap": -2500.0,
        "orb_min": 5,
    }


def clamp_universe(symbols: List[str], g: Dict[str, Any]) -> List[str]:
    deny = g.get("deny", set())
    return [s for s in symbols if s not in deny]


def _get_spread_limit(sym: str, g: Dict[str, Any]) -> float:
    m = g.get("spread_bps_limit_by_symbol") or {}
    try:
        return float(m.get(sym, g.get("spread_bps_limit", 8.0)))
    except Exception:
        return float(g.get("spread_bps_limit", 8.0))


def vet_and_adjust(
    sym: str, dec: Dict[str, Any], g: Dict[str, Any]
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Spread gate + qty clamp.
    Decision may include microstructure fields: price, bid, ask, bidSize, askSize, volume.
    If (ask - bid)/price in bps exceeds limit -> block (qty=0).
    """
    d = dict(dec or {})
    px = d.get("price")
    bid = d.get("bid")
    ask = d.get("ask")
    qty = int(d.get("qty") or 1)

    max_qty = int(g.get("max_qty", 1000))
    spread_bps_limit = _get_spread_limit(sym, g)

    # Cap qty first
    if qty > max_qty:
        qty = max_qty
    d["qty"] = qty

    # Spread check (only if we have microstructure fields)
    if bid is not None and ask is not None and px:
        try:
            spread = max(0.0, float(ask) - float(bid))
            bps = (spread / float(px)) * 1e4
            if bps > float(spread_bps_limit):
                d["qty"] = 0
                return False, f"spread_{bps:.1f}bps_gt_{spread_bps_limit}bps", d
        except Exception:
            # If parsing fails, fall through as OK but keep clamped qty
            pass

    return True, "guardrails_ok", d
