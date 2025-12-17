from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from hybrid_ai_trading.portfolio.router import route_one
from hybrid_ai_trading.strategies.registry import StrategySpec, register, clear_registry_for_tests
from hybrid_ai_trading.runtime.run_context import RunMode


@dataclass
class Ctx:
    mode: RunMode = RunMode.PAPER
    day_id: str = "PAPER"


class PaperEngine:
    # Router+Phase-5 guard will treat is_paper=True as paper-safe (Block-G bypass)
    is_paper = True
    risk_manager = None

    def place_order(self, **kwargs):
        return {"status": "ok", "engine_called": True}


def main() -> int:
    clear_registry_for_tests()

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

    out = route_one(
        engine=PaperEngine(),
        strategy_id="NVDA_BPLUS",
        market_state={},
        ctx=Ctx(),
        portfolio_state={},
    )
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())