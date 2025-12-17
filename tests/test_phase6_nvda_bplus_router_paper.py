from __future__ import annotations

import json
from pathlib import Path

import pytest

from hybrid_ai_trading.portfolio.router import route_one
from hybrid_ai_trading.strategies.registry import StrategySpec, register, clear_registry_for_tests
from hybrid_ai_trading.runtime.run_context import RunMode


class DummyEngine:
    is_paper = True
    risk_manager = None

    def place_order(self, **kwargs):
        return {"status": "ok", "engine_called": True}


class Ctx:
    mode = RunMode.PAPER
    day_id = "PAPER"


@pytest.fixture(autouse=True)
def _clean_registry():
    clear_registry_for_tests()
    yield
    clear_registry_for_tests()


def test_phase6_nvda_bplus_paper_routes_and_logs(tmp_path, monkeypatch):
    # Create minimal logs/paper_trades.jsonl in temp cwd
    monkeypatch.chdir(tmp_path)
    (tmp_path / "logs").mkdir(parents=True, exist_ok=True)

    # Minimal NVDA candidates
    rows = [
        {"ts": "2099-01-01T09:30:00Z", "symbol": "NVDA", "signal": "LONG", "qty": 1, "price": 100.0},
        {"ts": "2099-01-01T09:31:00Z", "symbol": "NVDA", "signal": "SHORT", "qty": 1, "price": 101.0},
    ]
    p = tmp_path / "logs" / "paper_trades.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    from hybrid_ai_trading.strategies import nvda_bplus

    register(
        StrategySpec(
            strategy_id="NVDA_BPLUS",
            symbol="NVDA",
            timeframe="1m",
            supports_modes={"PAPER"},
            signal_fn=nvda_bplus.signal_fn,
            order_plan_fn=nvda_bplus.order_plan_fn,
            logs_schema_version=1,
        )
    )

    out = route_one(engine=DummyEngine(), strategy_id="NVDA_BPLUS", market_state={}, ctx=Ctx(), portfolio_state={})
    assert out["status"] == "ok"
    assert out["intents"], "expected intents"
    assert out["intents"][0]["status"] == "sent"

    # Best-effort log file
    logp = tmp_path / "logs" / "portfolio_order_intents.jsonl"
    assert logp.exists()
    txt = logp.read_text(encoding="utf-8")
    assert '"strategy_id": "NVDA_BPLUS"' in txt