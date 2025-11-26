"""
Phase-5 engine guard helpers.

These helpers are designed to be called from trade_engine / paper runners
before placing a paper or live order.

They route the trade dict through RiskManager.check_trade_phase5 and
return a Phase5RiskDecision that the caller can use to allow/block.
"""

from __future__ import annotations

from typing import Any, Dict

from hybrid_ai_trading.risk.risk_phase5_types import Phase5RiskDecision
from hybrid_ai_trading.risk.risk_manager import RiskManager

from hybrid_ai_trading.risk.phase5_config import SPY_ORB_EV_BAND_A, QQQ_ORB_EV_BAND_A


def phase5_spy_orb_gate(ctx, risk_state, cfg=None):
    """
    Phase-5 EV-band gate for SPY ORB.

    This is intentionally lightweight and tolerant:
    - Only applies when symbol = SPY and regime is a SPY ORB regime.
    - If ctx.tp_r is present and outside the configured EV band, block.
    - Otherwise, return allowed / not_applicable and let other Phase-5
      gates (daily loss, no-averaging-down, etc.) decide in risk_manager.
    """
    if cfg is None:
        cfg = SPY_ORB_EV_BAND_A

    symbol = getattr(ctx, "symbol", None) or str(getattr(ctx, "sym", "") or "")
    regime = getattr(ctx, "regime", None)

    if symbol != cfg["symbol"] or regime not in (
        "SPY_ORB_REPLAY",
        "SPY_ORB_LIVE",
        "SPY_ORB_PAPER",
    ):
        return True, "not_applicable"

    tp_r = getattr(ctx, "tp_r", None)
    if tp_r is None:
        # No explicit TP in R on context -> do not block here.
        return True, "no_tp_r"

    tp_primary = cfg.get("tp_r_primary")
    tp_fallback = cfg.get("tp_r_fallback")
    allowed_tps = {tp_primary, tp_fallback}

    if tp_r not in allowed_tps:
        return False, f"tp_out_of_band(tp_r={tp_r})"

    return True, "spy_orb_ev_band_ok"


def phase5_qqq_orb_gate(ctx, risk_state, cfg=None):
    """
    Phase-5 EV-band gate for QQQ ORB.

    Same pattern as SPY:
    - Applies only to QQQ ORB regimes.
    - Enforces that tp_r is within the configured EV band if present.
    """
    if cfg is None:
        cfg = QQQ_ORB_EV_BAND_A

    symbol = getattr(ctx, "symbol", None) or str(getattr(ctx, "sym", "") or "")
    regime = getattr(ctx, "regime", None)

    if symbol != cfg["symbol"] or regime not in (
        "QQQ_ORB_REPLAY",
        "QQQ_ORB_LIVE",
        "QQQ_ORB_PAPER",
    ):
        return True, "not_applicable"

    tp_r = getattr(ctx, "tp_r", None)
    if tp_r is None:
        return True, "no_tp_r"

    tp_primary = cfg.get("tp_r_primary")
    tp_fallback = cfg.get("tp_r_fallback")
    allowed_tps = {tp_primary, tp_fallback}

    if tp_r not in allowed_tps:
        return False, f"tp_out_of_band(tp_r={tp_r})"

    return True, "qqq_orb_ev_band_ok"


def allow_trade_phase5(ctx, risk_state):
    """
    Top-level Phase-5 EV-band gate for ORB strategies.

    Expected to be called *after* generic Phase-5 risk checks
    (daily loss, no-averaging-down, account caps) have run in the
    risk_manager._check_trade_phase5 pipeline.

    Parameters
    ----------
    ctx : object
        Trade context (symbol, regime, tp_r, etc.).
    risk_state : object
        Optional Phase-5 risk state (currently unused by these EV gates,
        but kept for future extension).

    Returns
    -------
    allowed : bool
    reason  : str
        'phase5_ok' if all symbol-specific gates accept, or a
        'xxx_blocked:...' reason if any EV-band gate blocks.
    """
    # 1) SPY ORB EV gate
    allowed, reason = phase5_spy_orb_gate(ctx, risk_state)
    if not allowed:
        return False, f"spy_orb_blocked:{reason}"

    # 2) QQQ ORB EV gate
    allowed, reason = phase5_qqq_orb_gate(ctx, risk_state)
    if not allowed:
        return False, f"qqq_orb_blocked:{reason}"

    # 3) Other Phase-5 strategy gates (NVDA_BPLUS, etc.) can be added later.

    return True, "phase5_ok"

def guard_phase5_trade(
    rm: RiskManager,
    trade: Dict[str, Any],
) -> Phase5RiskDecision:
    """
    Run a proposed trade through Phase-5 risk checks.

    This is the single entrypoint that runners and engines should use
    before placing an order (paper or live).

    It simply forwards to rm.check_trade_phase5(trade) for now, but
    having a dedicated helper makes it easier to adapt later (e.g.
    adding logging, metrics, or engine-specific behavior).
    """
    decision = rm.check_trade_phase5(trade)
    if not isinstance(decision, Phase5RiskDecision):
        # Defensive: normalize non-conforming results.
        return Phase5RiskDecision(
            allowed=bool(getattr(decision, "allowed", True)),
            reason=str(getattr(decision, "reason", "phase5_risk_unknown")),
            details=getattr(decision, "details", {}),
        )
    return decision