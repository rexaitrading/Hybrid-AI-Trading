from __future__ import annotations

"""
Phase-5 EV soft-veto helper (log-only).

This module is NOT yet wired into hard trading decisions.
It provides a small helper that can be called from risk_manager
or logging code to derive a "soft EV veto" flag and reason
from the EV-band flags produced by ev_band_flags.evaluate_ev_band_for_trade().

Example EV flags dict:

    {
        "ev_band_allowed": True | False | None,
        "ev_band_reason": "band_A" | "band_below_min" | ...,
        "ev_band_veto_applied": True | False,
        "ev_band_veto_reason": str | None,
        "locked_by_ev_band": False,
    }

We simply interpret `ev_band_veto_applied` as a soft veto signal.
"""


from typing import Any, Dict


def phase5_ev_soft_veto_from_flags(ev_flags: Dict[str, Any]) -> Dict[str, Any]:
    """
    Given EV-band flags for a trade, derive a soft EV veto flag.

    Returns a dict with keys:

        soft_ev_veto: bool
        soft_ev_reason: str | None

    This is log-only: it does not perform any hard blocking by itself.
    """
    veto_applied = bool(ev_flags.get("ev_band_veto_applied", False))
    reason = ev_flags.get("ev_band_veto_reason") or ev_flags.get("ev_band_reason")

    return {
        "soft_ev_veto": veto_applied,
        "soft_ev_reason": reason,
    }