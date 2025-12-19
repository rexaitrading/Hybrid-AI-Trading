from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from hybrid_ai_trading.portfolio.router import route_one
from hybrid_ai_trading.strategies.registry import StrategySpec, register, clear_registry_for_tests
from hybrid_ai_trading.runtime.run_context import RunMode


class DummyEngine:
    # Phase-5 guard treats is_paper=True as paper-safe (never blocked by Block-G readiness)
    is_paper = True
    risk_manager = None

    def place_order(self, **kwargs):
        return {"status": "ok", "engine_called": True}


@dataclass
class DummyCtx:
    # Router only uses ctx.mode/day_id to log; Block-G enforcement uses is_live passed explicitly.
    mode: RunMode = RunMode.PAPER
    day_id: str = "2099-01-01"


def _dummy_signal_fn(_market_state: dict) -> dict:
    return {"ok": True}


def _dummy_order_plan_live(_signal: dict, _ctx: object, _pf: dict) -> list:
    return [{
        "symbol": "NVDA",
        "side": "BUY",
        "qty": 1.0,
        "price": 100.0,
        "regime": "NVDA_BPLUS_LIVE",  # LIVE intent boundary
        "day_id": "TEST",
    }]


def _dummy_order_plan_paper(_signal: dict, _ctx: object, _pf: dict) -> list:
    return [{
        "symbol": "NVDA",
        "side": "BUY",
        "qty": 1.0,
        "price": 100.0,
        "regime": "NVDA_BPLUS_PAPER",  # NOT live
        "day_id": "TEST",
    }]


@pytest.fixture(autouse=True)
def _clean_registry():
    clear_registry_for_tests()
    yield
    clear_registry_for_tests()


def test_phase6_blocks_live_intent_when_blockg_not_ready(monkeypatch, tmp_path):
    # Register dummy strategy
    register(StrategySpec(
        strategy_id="DUMMY",
        symbol="NVDA",
        timeframe="1m",
        supports_modes={"PAPER", "LIVE"},
        signal_fn=_dummy_signal_fn,
        order_plan_fn=_dummy_order_plan_live,
        logs_schema_version=1,
    ))

    # Force Block-G contract fail deterministically
    import hybrid_ai_trading.execution.blockg_runtime as br

    class _D:
        ready = False
        reason = "not_ready_test"
        symbol = "NVDA"
        as_of_date = "2099-01-01"

    monkeypatch.setattr(br, "require_blockg_ready", lambda symbol: _D())

    eng = DummyEngine()
    ctx = DummyCtx()

    out = route_one(engine=eng, strategy_id="DUMMY", market_state={}, ctx=ctx, portfolio_state={})
    assert out["status"] == "ok"
    assert out["intents"], "expected at least 1 intent"
    assert out["intents"][0]["status"] == "blocked"
    assert "not_ready_test" in out["intents"][0]["reason"]


def test_phase6_allows_paper_intent_even_if_blockg_not_ready(monkeypatch):
    # Register dummy strategy
    register(StrategySpec(
        strategy_id="DUMMY",
        symbol="NVDA",
        timeframe="1m",
        supports_modes={"PAPER"},
        signal_fn=_dummy_signal_fn,
        order_plan_fn=_dummy_order_plan_paper,
        logs_schema_version=1,
    ))

    # Even if Block-G is not ready, PAPER intent must not be blocked by Block-G
    import hybrid_ai_trading.execution.blockg_runtime as br

    class _D:
        ready = False
        reason = "not_ready_test"
        symbol = "NVDA"
        as_of_date = "2099-01-01"

    monkeypatch.setattr(br, "require_blockg_ready", lambda symbol: _D())

    eng = DummyEngine()
    ctx = DummyCtx()

    out = route_one(engine=eng, strategy_id="DUMMY", market_state={}, ctx=ctx, portfolio_state={})
    assert out["status"] == "ok"
    assert out["intents"], "expected at least 1 intent"
    # PAPER regime => is_live=False => enforce_blockg_if_live returns ok=True => should send
    assert out["intents"][0]["status"] == "sent"
    assert out["intents"][0]["result"]["status"] == "ok_stub_engine"


def test_phase6_writes_portfolio_order_intents_jsonl_best_effort(monkeypatch, tmp_path):
    # Register dummy strategy (paper)
    register(StrategySpec(
        strategy_id="DUMMY",
        symbol="NVDA",
        timeframe="1m",
        supports_modes={"PAPER"},
        signal_fn=_dummy_signal_fn,
        order_plan_fn=_dummy_order_plan_paper,
        logs_schema_version=1,
    ))

    # Ensure Block-G would not block even if evaluated
    import hybrid_ai_trading.execution.blockg_runtime as br

    class _D:
        ready = True
        reason = "ok"
        symbol = "NVDA"
        as_of_date = "2099-01-01"

    monkeypatch.setattr(br, "require_blockg_ready", lambda symbol: _D())

    # Route once, should append logs/portfolio_order_intents.jsonl
    eng = DummyEngine()
    ctx = DummyCtx()
    out = route_one(engine=eng, strategy_id="DUMMY", market_state={}, ctx=ctx, portfolio_state={})
    assert out["intents"][0]["status"] == "sent"

    p = Path("logs") / "portfolio_order_intents.jsonl"
    assert p.exists(), "expected best-effort log file to exist"
    txt = p.read_text(encoding="utf-8")
    assert '"strategy_id": "DUMMY"' in txt or '"strategy_id": "DUMMY"' in txt.replace("\\u0022", '"')