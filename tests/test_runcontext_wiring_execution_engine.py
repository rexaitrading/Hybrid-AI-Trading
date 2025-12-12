from __future__ import annotations

from datetime import date

from hybrid_ai_trading.execution.execution_engine import ExecutionEngine
from hybrid_ai_trading.runtime.run_context import RunContext, RunMode


def test_execution_engine_accepts_and_stores_run_context():
    ctx = RunContext(mode=RunMode.PAPER, trading_date=date.today(), symbol="NVDA")
    eng = ExecutionEngine(dry_run=True, config={}, run_context=ctx)
    assert eng.run_context is ctx
