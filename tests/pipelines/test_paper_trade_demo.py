import logging
import runpy
from datetime import datetime
from unittest.mock import patch

import hybrid_ai_trading.pipelines.paper_trade_demo as demo


def test_run_demo_success(capsys, monkeypatch, caplog):
    """run_demo prints a success line and logs info when breakout_signal returns."""
    monkeypatch.setattr(demo, "_now", lambda: datetime(2025, 1, 1, 0, 0, 0))
    monkeypatch.setattr(demo, "breakout_signal", lambda sym: "BUY")

    caplog.set_level(logging.INFO, logger=demo.__name__)
    demo.run_demo()

    out = capsys.readouterr().out
    assert "[2025-01-01 00:00:00]" in out
    assert "Breakout signal: BUY" in out
    assert "Breakout signal: BUY" in caplog.text


def test_run_demo_exception(capsys, monkeypatch, caplog):
    """run_demo prints an error line and logs error when breakout_signal raises."""
    monkeypatch.setattr(demo, "_now", lambda: datetime(2025, 1, 2, 0, 0, 0))

    def boom(_sym=""):
        raise RuntimeError("network fail")

    monkeypatch.setattr(demo, "breakout_signal", boom)

    caplog.set_level(logging.ERROR, logger=demo.__name__)
    demo.run_demo()

    out = capsys.readouterr().out
    assert "[2025-01-02 00:00:00]" in out
    assert "Breakout signal failed: network fail" in out
    assert "failed" in caplog.text.lower()


def test_demo_as_script_success(capsys):
    """
    Run the module as a script via runpy.
    We patch the source function BEFORE import so paper_trade_demo binds to our patched version.
    """
    with patch("hybrid_ai_trading.signals.breakout_v1.breakout_signal", return_value="SELL"):
        runpy.run_module("hybrid_ai_trading.pipelines.paper_trade_demo", run_name="__main__")

    out = capsys.readouterr().out
    assert "Breakout signal: SELL" in out


def test_demo_as_script_exception(capsys):
    """Script path when breakout_signal raises."""
    with patch(
        "hybrid_ai_trading.signals.breakout_v1.breakout_signal",
        side_effect=Exception("boom"),
    ):
        runpy.run_module("hybrid_ai_trading.pipelines.paper_trade_demo", run_name="__main__")

    out = capsys.readouterr().out
    assert "Breakout signal failed: boom" in out
