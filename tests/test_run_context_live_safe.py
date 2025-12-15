from datetime import date

import pytest

from hybrid_ai_trading.runtime.run_context import RunContext, RunMode


def test_require_live_safe_blocks_when_any_phase1a_flag_missing():
    ctx = RunContext(
        mode=RunMode.LIVE,
        trading_date=date(2025, 12, 14),
        phase4_passed=True,
        blockg_ready=True,
        phase23_ok=False,
        ev_hard_ok=True,
        gatescore_fresh=True,
    )
    with pytest.raises(RuntimeError, match="Phase23"):
        ctx.require_live_safe()

    ctx2 = RunContext(
        mode=RunMode.LIVE,
        trading_date=date(2025, 12, 14),
        phase4_passed=True,
        blockg_ready=True,
        phase23_ok=True,
        ev_hard_ok=False,
        gatescore_fresh=True,
    )
    with pytest.raises(RuntimeError, match="EV-hard"):
        ctx2.require_live_safe()

    ctx3 = RunContext(
        mode=RunMode.LIVE,
        trading_date=date(2025, 12, 14),
        phase4_passed=True,
        blockg_ready=True,
        phase23_ok=True,
        ev_hard_ok=True,
        gatescore_fresh=False,
    )
    with pytest.raises(RuntimeError, match="GateScore"):
        ctx3.require_live_safe()


def test_require_live_safe_noop_when_not_live():
    ctx = RunContext(
        mode=RunMode.PAPER,
        trading_date=date(2025, 12, 14),
        phase4_passed=False,
        blockg_ready=False,
        phase23_ok=False,
        ev_hard_ok=False,
        gatescore_fresh=False,
    )
    ctx.require_live_safe()
