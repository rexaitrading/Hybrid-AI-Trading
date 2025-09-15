"""
Unit Tests: Paper Trade Demo (Hybrid AI Quant Pro v16.8 – 100% Coverage)
-------------------------------------------------------------------------
Covers all branches of paper_trade_demo.py:
- run_demo() success path for BUY/SELL/HOLD
- run_demo() error path when breakout_signal raises
- _now patched for deterministic datetime
- __main__ execution via runpy with fake breakout_signal
"""

import runpy
import pytest
from datetime import datetime
from hybrid_ai_trading.pipelines import paper_trade_demo


# --- Fixtures ---------------------------------------------------------
class FixedDatetime(datetime):
    @classmethod
    def utcnow(cls):
        return datetime(2025, 1, 1, 12, 0, 0)


@pytest.fixture(autouse=True)
def patch_now(monkeypatch):
    """Patch _now() globally for deterministic output in all tests."""
    monkeypatch.setattr(paper_trade_demo, "_now", lambda: FixedDatetime.utcnow())
    yield


# --- Tests: run_demo() ------------------------------------------------
@pytest.mark.parametrize("signal", ["BUY", "SELL", "HOLD"])
def test_run_demo_signals(monkeypatch, capsys, signal):
    """run_demo prints breakout_signal output with fixed datetime."""
    monkeypatch.setattr(paper_trade_demo, "breakout_signal", lambda _: signal)
    paper_trade_demo.run_demo()
    captured = capsys.readouterr()
    assert f"Breakout signal: {signal}" in captured.out
    assert "[2025-01-01 12:00:00]" in captured.out


def test_run_demo_error(monkeypatch, capsys):
    """Simulate breakout_signal raising error → prints error gracefully."""

    def bad_signal(_):
        raise RuntimeError("boom")

    monkeypatch.setattr(paper_trade_demo, "breakout_signal", bad_signal)
    paper_trade_demo.run_demo()
    captured = capsys.readouterr()
    assert "Breakout signal failed: boom" in captured.out
    assert "[2025-01-01 12:00:00]" in captured.out


# --- Tests: __main__ --------------------------------------------------
def test_main_entrypoint(monkeypatch, capsys):
    """Ensure __main__ block executes run_demo() with deterministic output."""
    import sys, types

    # Fake breakout_signal always returns BUY
    fake_mod = types.ModuleType("hybrid_ai_trading.signals.breakout_v1")
    fake_mod.breakout_signal = lambda _: "BUY"
    sys.modules["hybrid_ai_trading.signals.breakout_v1"] = fake_mod

    # Run module fresh under __main__
    runpy.run_module("hybrid_ai_trading.pipelines.paper_trade_demo", run_name="__main__")

    # Patch _now inside the loaded module
    import hybrid_ai_trading.pipelines.paper_trade_demo as demo_mod
    monkeypatch.setattr(demo_mod, "_now", lambda: datetime(2025, 1, 1, 12, 0, 0))

    # Call run_demo again to verify deterministic output
    demo_mod.run_demo()
    captured = capsys.readouterr()

    assert "Breakout signal: BUY" in captured.out
    assert "[2025-01-01 12:00:00]" in captured.out
