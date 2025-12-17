from __future__ import annotations

import json
from pathlib import Path

import pytest

from hybrid_ai_trading.portfolio.router import route_one
from hybrid_ai_trading.strategies.registry import StrategySpec, register, clear_registry_for_tests
from hybrid_ai_trading.runtime.run_context import RunMode


class DummyEngine:
    is_paper = True  # paper-safe engine (Phase-5 guard never blocks)
    risk_manager = None

    def place_order(self, **kwargs):
        return {"status": "ok", "engine_called": True}


class Ctx:
    mode = RunMode.PAPER
    day_id = "PAPER"


def _sig(_ms: dict) -> dict:
    return {"ok": True}


def _plan_live(symbol: str) -> list:
    return [{
        "symbol": symbol,
        "side": "BUY",
        "qty": 1.0,
        "price": 100.0,
        "regime": f"{symbol}_ORB_LIVE",  # LIVE intent boundary
        "day_id": "TEST",
    }]


def _plan_paper(symbol: str) -> list:
    return [{
        "symbol": symbol,
        "side": "BUY",
        "qty": 1.0,
        "price": 100.0,
        "regime": f"{symbol}_ORB_PAPER",
        "day_id": "TEST",
    }]


@pytest.fixture(autouse=True)
def _clean_registry():
    clear_registry_for_tests()
    yield
    clear_registry_for_tests()


def test_spy_live_blocks_when_blockg_not_ready(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "logs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "logs" / "paper_trades.jsonl").write_text(
        json.dumps({"ts":"2099-01-01T00:00:00Z","symbol":"SPY","signal":"LONG","qty":1,"price":100.0})+"\n",
        encoding="utf-8",
    )

    register(StrategySpec("SPY_ORB", "SPY", "1m", {"PAPER","LIVE"}, _sig, lambda s,c,p: _plan_live("SPY"), 1))

    import hybrid_ai_trading.execution.blockg_runtime as br
    class _D:
        ready = False
        reason = "spy_not_ready"
        symbol = "SPY"
        as_of_date = "2099-01-01"
    monkeypatch.setattr(br, "require_blockg_ready", lambda symbol: _D())

    out = route_one(engine=DummyEngine(), strategy_id="SPY_ORB", market_state={}, ctx=Ctx(), portfolio_state={})
    assert out["intents"][0]["status"] == "blocked"
    assert "spy_not_ready" in out["intents"][0]["reason"]


def test_qqq_paper_allows_even_if_blockg_not_ready(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "logs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "logs" / "paper_trades.jsonl").write_text(
        json.dumps({"ts":"2099-01-01T00:00:00Z","symbol":"QQQ","signal":"LONG","qty":1,"price":100.0})+"\n",
        encoding="utf-8",
    )

    register(StrategySpec("QQQ_ORB", "QQQ", "1m", {"PAPER"}, _sig, lambda s,c,p: _plan_paper("QQQ"), 1))

    import hybrid_ai_trading.execution.blockg_runtime as br
    class _D:
        ready = False
        reason = "qqq_not_ready"
        symbol = "QQQ"
        as_of_date = "2099-01-01"
    monkeypatch.setattr(br, "require_blockg_ready", lambda symbol: _D())

    out = route_one(engine=DummyEngine(), strategy_id="QQQ_ORB", market_state={}, ctx=Ctx(), portfolio_state={})
    assert out["intents"][0]["status"] == "sent"
    assert out["intents"][0]["result"]["status"] == "ok_stub_engine"

    logp = tmp_path / "logs" / "portfolio_order_intents.jsonl"
    assert logp.exists()