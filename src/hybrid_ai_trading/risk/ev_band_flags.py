from __future__ import annotations

from typing import Any, Dict, Optional

try:
    # Shared EV-band helper used elsewhere in Phase-5
    from hybrid_ai_trading.risk.risk_phase5_ev_bands import require_ev_band
except Exception:  # pragma: no cover - defensive fallback
    require_ev_band = None


def evaluate_ev_band_for_trade(regime: str, ev: Optional[float]) -> Dict[str, Any]:
    """
    Compute EV-band flags for a trade in a *log-only* fashion.

    Returns a dict with the following keys:

        ev_band_allowed: Optional[bool]
        ev_band_reason: Optional[str]
        ev_band_veto_applied: bool
        ev_band_veto_reason: Optional[str]
        locked_by_ev_band: bool

    Log-only semantics (Phase-5 now):

        - locked_by_ev_band is always False.
        - ev_band_veto_applied tells you whether the EV-band logic
          *would* veto the trade in a future hard-veto mode.
        - No actual routing / blocking is performed here.
    """
    result: Dict[str, Any] = {
        "ev_band_allowed": None,
        "ev_band_reason": None,
        "ev_band_veto_applied": False,
        "ev_band_veto_reason": None,
        "locked_by_ev_band": False,
    }

    # If EV-band helper is unavailable, log that fact and bail.
    if require_ev_band is None:
        result["ev_band_reason"] = "ev_band_helper_unavailable"
        return result

    # EV missing or non-numeric -> cannot evaluate band.
    if ev is None:
        result["ev_band_reason"] = "ev_missing"
        return result

    try:
        ev_float = float(ev)
    except (TypeError, ValueError):
        result["ev_band_reason"] = "ev_not_numeric"
        return result

    # Use shared Phase-5 EV-band rule (per-regime).
    try:
        allowed, reason = require_ev_band(regime, ev_float)
    except Exception as exc:  # defensive
        result["ev_band_reason"] = f"ev_band_eval_error:{exc}"
        return result

    result["ev_band_allowed"] = allowed
    result["ev_band_reason"] = reason

    # Log-only: record whether EV-band *would* veto.
    if allowed is False:
        result["ev_band_veto_applied"] = True
        result["ev_band_veto_reason"] = reason
    else:
        result["ev_band_veto_applied"] = False
        result["ev_band_veto_reason"] = reason

    # Phase-5 now: no hard veto. locked_by_ev_band remains False.
    return result