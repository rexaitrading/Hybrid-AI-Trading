from __future__ import annotations

from typing import Dict, Any

from core.fx.fx_risk import get_fx_snapshot, evaluate_fx_risk


def fx_health(instrument: str = "USD_CAD") -> Dict[str, Any]:
    """
    Convenience hook returning both FX snapshot and risk flags as dicts.

    Example shape:
    {
        "snapshot": {
            "instrument": "USD_CAD",
            "time": "...",
            "bid": 1.40,
            "ask": 1.40,
            "mid": 1.40,
            "spread": 0.0002,
        },
        "flags": {
            "ok": True,
            "spread_wide": False,
            "stale": False,
            "error": None,
        },
    }
    """
    snap = get_fx_snapshot(instrument)
    flags = evaluate_fx_risk(snap)

    snap_dict = {
        "instrument": snap.instrument,
        "time": snap.time,
        "bid": snap.bid,
        "ask": snap.ask,
        "mid": snap.mid,
        "spread": snap.spread,
    }

    return {
        "snapshot": snap_dict,
        "flags": flags.to_dict(),
    }