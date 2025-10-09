"""
Unit Tests: main.py
(Hybrid AI Quant Pro – Hedge Fund Grade v1.3, 100% Coverage)
============================================================
Covers:
- Successful run (backtest, daily_close, paper_trade pipelines)
- Config load error branch
- TradeEngine init error branch
- CLI parsing and exit codes
- __main__ entrypoint execution (via runpy)
"""

import runpy
import sys
import types

import pytest

import hybrid_ai_trading.main as main


# ----------------------------------------------------------------------
# Dummy TradeEngine for patching
# ----------------------------------------------------------------------
class DummyEngine:
    def __init__(self, config=None):
        self.config = config
        self.ran = []

    def run(self):
        self.ran.append("run")


# ----------------------------------------------------------------------
# Autouse fixture: patch load_config + TradeEngine
# ----------------------------------------------------------------------
@pytest.fixture(autouse=True)
def patch_load_and_engine(monkeypatch):
    """Patch load_config + TradeEngine with dummy implementations."""
    monkeypatch.setattr(main, "load_config", lambda: {"project": "TEST"})
    monkeypatch.setattr(main, "TradeEngine", lambda config: DummyEngine(config))


# ----------------------------------------------------------------------
# Pipeline success branches
# ----------------------------------------------------------------------
def test_main_backtest(monkeypatch):
    called = {}

    def fake_run_backtest(engine):
        called["pipeline"] = "backtest"

    monkeypatch.setitem(
        sys.modules,
        "hybrid_ai_trading.pipelines.backtest",
        types.SimpleNamespace(run_backtest=fake_run_backtest),
    )

    exit_code = main.main(["--pipeline", "backtest"])
    assert exit_code == 0
    assert called["pipeline"] == "backtest"


def test_main_daily_close(monkeypatch):
    called = {}

    def fake_run_daily_close(engine):
        called["pipeline"] = "daily_close"

    monkeypatch.setitem(
        sys.modules,
        "hybrid_ai_trading.pipelines.daily_close",
        types.SimpleNamespace(run_daily_close=fake_run_daily_close),
    )

    exit_code = main.main(["--pipeline", "daily_close"])
    assert exit_code == 0
    assert called["pipeline"] == "daily_close"


def test_main_paper_trade(monkeypatch):
    called = {}

    def fake_run_paper_trade(engine):
        called["pipeline"] = "paper_trade"

    monkeypatch.setitem(
        sys.modules,
        "hybrid_ai_trading.pipelines.paper_trade_demo",
        types.SimpleNamespace(run_paper_trade=fake_run_paper_trade),
    )

    exit_code = main.main(["--pipeline", "paper_trade"])
    assert exit_code == 0
    assert called["pipeline"] == "paper_trade"


# ----------------------------------------------------------------------
# Error branches
# ----------------------------------------------------------------------
def test_main_config_error(monkeypatch):
    monkeypatch.setattr(
        main, "load_config", lambda: (_ for _ in ()).throw(RuntimeError("config fail"))
    )
    exit_code = main.main(["--pipeline", "backtest"])
    assert exit_code == 1


def test_main_engine_error(monkeypatch):
    def bad_engine(config):
        raise RuntimeError("engine fail")

    monkeypatch.setattr(main, "TradeEngine", bad_engine)
    exit_code = main.main(["--pipeline", "backtest"])
    assert exit_code == 1


# ----------------------------------------------------------------------
# __main__ entrypoint
# ----------------------------------------------------------------------
def test_main_called_as_script(monkeypatch):
    """Simulate `python -m hybrid_ai_trading.main` via run_module safely."""

    # Fake pipeline modules so imports succeed
    monkeypatch.setitem(
        sys.modules,
        "hybrid_ai_trading.pipelines.backtest",
        types.SimpleNamespace(run_backtest=lambda e: None),
    )
    monkeypatch.setitem(
        sys.modules,
        "hybrid_ai_trading.pipelines.daily_close",
        types.SimpleNamespace(run_daily_close=lambda e: None),
    )
    monkeypatch.setitem(
        sys.modules,
        "hybrid_ai_trading.pipelines.paper_trade_demo",
        types.SimpleNamespace(run_paper_trade=lambda e: None),
    )

    # Safe argv (so argparse sees something valid)
    monkeypatch.setattr(sys, "argv", ["python", "--pipeline", "backtest"])

    with pytest.raises(SystemExit) as e:
        runpy.run_module("hybrid_ai_trading.main", run_name="__main__")

    assert e.value.code == 0
