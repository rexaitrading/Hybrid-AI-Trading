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
    #
    # For SPY/QQQ we prefer config-driven EV-band diagnostics using the
    # Phase-5 JSON configs (ev_bands.*). For other symbols (e.g. NVDA),
    # we keep the simpler EV<0 heuristic for now.
    phase5_ev_band_enabled = False
    phase5_ev_band_veto = False
    phase5_ev_band_reason = None

    ev_band_info_for_veto = None

    # Config-driven EV-band veto for SPY / QQQ (paper and live).
    if symbol in ("SPY", "QQQ") and ev_value is not None:
        try:
            from hybrid_ai_trading.risk.phase5_ev_band_helpers import compute_ev_bands_from_config  # type: ignore
        except Exception:
            ev_band_info_for_veto = None
        else:
            # At entry time, realized PnL is typically zero; we still want to
            # use the config thresholds as a banding / tolerance guide.
            ev_band_info_for_veto = compute_ev_bands_from_config(
                symbol=symbol,
                ev=ev_value,
                realized_pnl=0.0,
            )

    if ev_band_info_for_veto is not None:
        phase5_ev_band_enabled = True
        if ev_band_info_for_veto["ev_hard_veto"]:
            phase5_ev_band_veto = True
            phase5_ev_band_reason = "ev_band_hard_veto"
        else:
            phase5_ev_band_veto = False
            phase5_ev_band_reason = "ev_band_ok"
    else:
        # Fallback: original EV<0 heuristic (e.g. NVDA or missing config).
        if ev_value is not None:
            phase5_ev_band_enabled = True
            if ev_value < 0:
                phase5_ev_band_veto = True
                phase5_ev_band_reason = "ev_negative"
            else:
                phase5_ev_band_veto = False
                phase5_ev_band_reason = "ev_non_negative"

    # Synthetic test hook (guarded by explicit debug flag):
    # Only when PHASE5_DEBUG_ENABLE_TEST_HOOKS is true AND
    # PHASE5_FORCE_TEST_EV_VETO is set do we force an EV-band veto
    # for SPY/QQQ paper trades. Default behavior = no synthetic forcing.
    debug_flag = (os.getenv("PHASE5_DEBUG_ENABLE_TEST_HOOKS") or "").strip().lower()
    if debug_flag in ("1", "true", "yes", "on"):
        if symbol in ("SPY", "QQQ") and regime.endswith("_PAPER"):
            test_flag = (os.getenv("PHASE5_FORCE_TEST_EV_VETO") or "").strip().lower()
            if test_flag in ("1", "true", "yes", "on"):
                phase5_ev_band_enabled = True
                phase5_ev_band_veto = True
                phase5_ev_band_reason = "test_forced_ev_band_veto"

    # Hard veto flag.
    #
    # For SPY/QQQ ORB regimes (paper + live), use config-driven gating via
    # enable_ev_band_gating in the per-symbol Phase-5 JSON config.
    # For other regimes (e.g. NVDA live), keep the existing env-var toggle.
    enable_ev_band_hard_veto = False

    if symbol in ("SPY", "QQQ"):
        try:
            from hybrid_ai_trading.risk.phase5_ev_band_helpers import is_ev_band_gating_enabled  # type: ignore
        except Exception:
            enable_ev_band_hard_veto = False
        else:
            enable_ev_band_hard_veto = is_ev_band_gating_enabled(symbol)
    else:
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
        # Config-driven EV-band diagnostics for SPY/QQQ (log-only)
        _attach_ev_band_diag_to_result(symbol, ev_value, decision, result)

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

def _attach_ev_band_diag_to_result(symbol, ev_value, decision, result):
    """
    Attach config-driven EV-band diagnostics for SPY/QQQ into the result dict
    and decision.details. This is log-only and does not change allowed/blocked
    behavior.

    Parameters
    ----------
    symbol : str
        Trade symbol, e.g. "SPY", "QQQ", "NVDA".
    ev_value : Optional[float]
        Per-trade EV estimate extracted from the Phase-5 risk decision.
    decision : Phase5RiskDecision
        Phase-5 risk decision object that carries .details.
    result : Dict[str, Any]
        Order result dict returned by place_order_phase5.
    """
    # Only apply to SPY / QQQ ORB strategies for now.
    if symbol not in ("SPY", "QQQ"):
        return

    if ev_value is None:
        # No EV -> nothing to compute/log yet.
        return

    # Local import to avoid any potential import cycles at module load time.
    from hybrid_ai_trading.risk.phase5_ev_band_helpers import compute_ev_bands_from_config  # type: ignore

    realized_pnl = None
    if isinstance(result, dict):
        realized_pnl = result.get("realized_pnl")

    ev_band_info = compute_ev_bands_from_config(
        symbol=symbol,
        ev=ev_value,
        realized_pnl=realized_pnl,
    )

    # 1) Attach to result dict (for JSONL/CSV/Notion)
    if isinstance(result, dict):
        result.setdefault("ev_band_abs", ev_band_info["ev_band_abs"])
        result.setdefault("ev_gap_abs", ev_band_info["ev_gap_abs"])
        result.setdefault("ev_hit_flag", ev_band_info["ev_hit_flag"])
        result.setdefault("ev_hard_veto", ev_band_info["ev_hard_veto"])
        result.setdefault("ev_hard_veto_gap_abs", ev_band_info["ev_hard_veto_gap_abs"])
        result.setdefault("soft_veto_gap_threshold", ev_band_info["soft_veto_gap_threshold"])
        result.setdefault("hard_veto_gap_threshold", ev_band_info["hard_veto_gap_threshold"])

    # 2) Attach to decision.details (Phase-5 details)
    details = getattr(decision, "details", None)
    if isinstance(details, dict):
        details.setdefault("ev_band_abs", ev_band_info["ev_band_abs"])
        details.setdefault("ev_gap_abs", ev_band_info["ev_gap_abs"])
        details.setdefault("ev_hit_flag", ev_band_info["ev_hit_flag"])
        details.setdefault("ev_hard_veto", ev_band_info["ev_hard_veto"])
        details.setdefault("ev_hard_veto_gap_abs", ev_band_info["ev_hard_veto_gap_abs"])
        details.setdefault("soft_veto_gap_threshold", ev_band_info["soft_veto_gap_threshold"])
        details.setdefault("hard_veto_gap_threshold", ev_band_info["hard_veto_gap_threshold"])
