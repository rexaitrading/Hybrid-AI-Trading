"""
Phase-5 execution guard helpers.

This module exposes place_order_phase5_with_guard(engine, **kwargs),
which wraps the existing place_order_phase5 with Phase-5 risk checks.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

from hybrid_ai_trading.execution.execution_engine import place_order_phase5
from hybrid_ai_trading.risk.risk_phase5_engine_guard import guard_phase5_trade
from hybrid_ai_trading.risk.risk_phase5_types import Phase5RiskDecision


def _extract_phase5_ev(decision: Phase5RiskDecision) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Best-effort extraction of EV-style metrics from a Phase-5 risk decision.

    We don't enforce any particular schema here; we just look into
    decision.details for common keys so that, once the risk engine starts
    emitting EV metrics, they automatically flow through into the results.
    """
    ev_value: Optional[float] = None
    ev_band_abs: Optional[float] = None
    gate_score_v2: Optional[float] = None

    details: Dict[str, Any] = {}
    try:
        details = decision.details or {}  # type: ignore[attr-defined]
    except AttributeError:
        details = {}

    if isinstance(details, dict):
        # EV "mu" style value
        ev_value = (
            details.get("ev")
            or details.get("ev_mu")
            or (details.get("ev_info") or {}).get("mu")
        )
        # Absolute EV band / tolerance
        ev_band_abs = (
            details.get("ev_band_abs")
            or details.get("ev_band")
            or (details.get("ev_info") or {}).get("band_abs")
            or (details.get("ev_info") or {}).get("band")
        )
        # GateScore / EV-based score
        gate_score_v2 = details.get("gate_score_v2") or details.get("gate_score")

    return ev_value, ev_band_abs, gate_score_v2


def place_order_phase5_with_guard(engine: Any, **kwargs: Any) -> Dict[str, Any]:
    """
    Guarded version of place_order_phase5 for Phase-5 runners.

    Expected kwargs include at least:
        symbol, side, qty, price, maybe regime, day_id

    If engine.risk_manager is missing, this behaves like the original
    place_order_phase5 (no Phase-5 risk applied).
    """
    rm = getattr(engine, "risk_manager", None)
    if rm is None:
        # No risk manager available; fall back to original behavior.
        return place_order_phase5(engine=engine, **kwargs)

    symbol = str(kwargs.get("symbol", kwargs.get("sym", "UNKNOWN")))
    side = str(kwargs.get("side", "")).upper()
    qty = kwargs.get("qty", kwargs.get("size", 0.0))
    price = float(kwargs.get("price", 0.0) or 0.0)
    regime = str(kwargs.get("regime", "SPY_ORB_LIVE"))
    day_id = (
        kwargs.get("day_id")
        or kwargs.get("session_date")
        or str(kwargs.get("ts", ""))[:10]
        or "UNKNOWN"
    )

    try:
        qty_f = float(qty)
    except (TypeError, ValueError):
        qty_f = 0.0

    trade: Dict[str, Any] = {
        "symbol": symbol,
        "side": side,
        "qty": qty_f,
        "price": price,
        "regime": regime,
        "day_id": day_id,
    }

    decision: Phase5RiskDecision = guard_phase5_trade(rm, trade)
    ev_value, ev_band_abs, gate_score_v2 = _extract_phase5_ev(decision)

    # Advisory + optional hard EV-band veto.
    # Simple heuristic:
    #   ev is None        -> disabled
    #   ev < 0            -> "bad" EV
    #   ev >= 0           -> "good" EV
    phase5_ev_band_enabled = False
    phase5_ev_band_veto = False
    phase5_ev_band_reason = None

    if ev_value is not None:
        phase5_ev_band_enabled = True
        if ev_value < 0:
            phase5_ev_band_veto = True
            phase5_ev_band_reason = "ev_negative"
        else:
            phase5_ev_band_veto = False
            phase5_ev_band_reason = "ev_non_negative"

    # Hard veto flag (default = OFF, so behavior stays log-only unless enabled).
    enable_ev_band_hard_veto = bool(
        (os.getenv("PHASE5_ENABLE_EV_BAND_HARD_VETO") or "").strip().lower()
        in ("1", "true", "yes", "on")
    )

    if (
        enable_ev_band_hard_veto
        and phase5_ev_band_enabled
        and phase5_ev_band_veto
        and getattr(decision, "allowed", True)
    ):
        # Override decision.allowed but keep Phase-5 details for logging.
        decision.allowed = False
        reason = getattr(decision, "reason", None) or ""
        if reason:
            reason = f"{reason}|ev_band_hard_veto"
        else:
            reason = "ev_band_hard_veto"
        setattr(decision, "reason", reason)

    # --- Case 0: blocked by Phase-5 risk ------------------------------------
    if not decision.allowed:
        # Blocked by Phase-5 risk; return a synthetic result.
        return {
            "status": "blocked_phase5",
            "symbol": symbol,
            "side": side,
            "qty": qty_f,
            "reason": decision.reason,
            "phase5_details": getattr(decision, "details", None),
            # EV / GateScore hooks (may be None if not provided yet)
            "ev": ev_value,
            "ev_band_abs": ev_band_abs,
            "phase5_ev_band_enabled": phase5_ev_band_enabled,
            "phase5_ev_band_veto": phase5_ev_band_veto,
            "phase5_ev_band_reason": phase5_ev_band_reason,
            "gate_score_v2": gate_score_v2,
            # No fill happened -> no realized PnL
            "realized_pnl": None,
        }

    # --- Case 1: real engine with place_order -> call full place_order_phase5 --
    if hasattr(engine, "place_order"):
        # Ensure entry_ts exists for the underlying engine
        if "entry_ts" not in kwargs:
            day_id_for_ts = (
                kwargs.get("day_id")
                or kwargs.get("session_date")
                or str(kwargs.get("ts", ""))[:10]
                or "1970-01-01"
            )
            kwargs["entry_ts"] = f"{day_id_for_ts}T00:00:00Z"

        # Remove Phase-5-only helper key before calling the underlying engine
        kwargs.pop("day_id", None)

        result: Dict[str, Any] = place_order_phase5(engine=engine, **kwargs)

        # Attach Phase-5 metadata and EV hooks if they are not already present.
        if isinstance(result, dict):
            result.setdefault("phase5_reason", decision.reason)
            result.setdefault("phase5_details", getattr(decision, "details", None))

            # EV metrics
            if "ev" not in result and ev_value is not None:
                result["ev"] = ev_value
            if "ev_band_abs" not in result and ev_band_abs is not None:
                result["ev_band_abs"] = ev_band_abs
            if "gate_score_v2" not in result and gate_score_v2 is not None:
                result["gate_score_v2"] = gate_score_v2

            # EV-band veto advisory fields
            result.setdefault("phase5_ev_band_enabled", phase5_ev_band_enabled)
            result.setdefault("phase5_ev_band_veto", phase5_ev_band_veto)
            result.setdefault("phase5_ev_band_reason", phase5_ev_band_reason)

            # realized_pnl will typically come from the underlying engine's
            # order_result / PnL accounting. We don't synthesize it here,
            # but we keep the hook name consistent.
            result.setdefault("realized_pnl", None)

        return result

    # --- Case 2: Dummy/test engine with no place_order ------------------------
    return {
        "status": "ok_phase5_stub",
        "symbol": symbol,
        "side": side,
        "qty": qty_f,
        "price": price,
        "regime": regime,
        "phase5_reason": decision.reason,
        "phase5_details": getattr(decision, "details", None),
        # EV / GateScore hooks (may be None)
        "ev": ev_value,
        "ev_band_abs": ev_band_abs,
        "phase5_ev_band_enabled": phase5_ev_band_enabled,
        "phase5_ev_band_veto": phase5_ev_band_veto,
        "phase5_ev_band_reason": phase5_ev_band_reason,
        "gate_score_v2": gate_score_v2,
        # No real fill -> no realized PnL
        "realized_pnl": None,
    }