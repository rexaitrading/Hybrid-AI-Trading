from __future__ import annotations

from dataclasses import dataclass

from hybrid_ai_trading.portfolio.router import route_one
from hybrid_ai_trading.strategies.registry import StrategySpec, register, clear_registry_for_tests
from hybrid_ai_trading.runtime.run_context import RunMode


@dataclass
class Ctx:
    mode: RunMode = RunMode.PAPER
    day_id: str = "PAPER"


class PaperEngine:
    is_paper = True
    risk_manager = None

    def place_order(self, **kwargs):
        return {"status": "ok", "engine_called": True}


def main() -> int:
    clear_registry_for_tests()

    from hybrid_ai_trading.strategies import nvda_bplus, spy_orb, qqq_orb

    register(StrategySpec("NVDA_BPLUS", "NVDA", "1m", {"PAPER"}, nvda_bplus.signal_fn, nvda_bplus.order_plan_fn, 1))
    register(StrategySpec("SPY_ORB",   "SPY",  "1m", {"PAPER"}, spy_orb.signal_fn,  spy_orb.order_plan_fn,  1))
    register(StrategySpec("QQQ_ORB",   "QQQ",  "1m", {"PAPER"}, qqq_orb.signal_fn,  qqq_orb.order_plan_fn,  1))

    eng = PaperEngine()
    ctx = Ctx()
    for sid in ("NVDA_BPLUS", "SPY_ORB", "QQQ_ORB"):
        out = route_one(engine=eng, strategy_id=sid, market_state={}, ctx=ctx, portfolio_state={})
        print(out)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())