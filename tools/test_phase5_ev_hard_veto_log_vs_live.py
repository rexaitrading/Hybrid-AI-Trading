from typing import Any, Dict

try:
    from tools.phase5_gating_helpers import (
        attach_ev_band_hard_veto,
        maybe_apply_ev_hard_veto,
    )
except Exception:  # pragma: no cover
    from phase5_gating_helpers import (  # type: ignore[no-redef]
        attach_ev_band_hard_veto,
        maybe_apply_ev_hard_veto,
    )


def _make_decision(ev: float, phase5_allowed: bool = True) -> Dict[str, Any]:
    return {
        "ev": ev,
        "phase5_allowed": phase5_allowed,
        "phase5_reason": "BASE",
        "realized_pnl_paper": 0.0,
        "ev_gap_abs": 0.0,
    }


def test_ev_hard_veto_log_only_vs_live_gate():
    """
    In log-only mode (enable=False), we expect hard-veto fields to be attached
    but the effective phase5_allowed/phase5_reason should remain unchanged.

    In live-gate mode (enable=True), we expect the decision itself to be modified
    according to the hard-veto decision.
    """

    base_ev = -2.0
    realized_pnl = -0.1
    gap_threshold = 0.7

    # Start with a simple "allowed" decision
    decision = _make_decision(base_ev, phase5_allowed=True)

    # Attach the hard-veto fields based on EV gap
    decision_with_hard = attach_ev_band_hard_veto(
        decision=decision,
        realized_pnl=realized_pnl,
        gap_threshold=gap_threshold,
    )

    # 1) Log-only mode: enable=False -> fields attached but no gating
    log_only = maybe_apply_ev_hard_veto(
        dict(decision_with_hard),
        enable=False,
    )

    assert log_only["phase5_allowed"] is True
    assert log_only["phase5_reason"] == "BASE"
    # Hard-veto information still present for logging:
    assert "ev_hard_veto" in log_only

    # 2) Live-gate mode: enable=True -> decision is actually gated
    live_gate = maybe_apply_ev_hard_veto(
        dict(decision_with_hard),
        enable=True,
    )

    # When enable=True, we expect the veto to actually gate the trade.
    assert live_gate["phase5_allowed"] is False
    # Reason must change from BASE to some hard-veto-specific reason (e.g. "ev<0")
    assert live_gate["phase5_reason"] != "BASE"
    assert live_gate["ev_hard_veto"] is True