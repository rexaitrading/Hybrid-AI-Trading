"""
Hybrid AI Trading - Main Entrypoint (Hedge Fund Grade)
------------------------------------------------------
Responsibilities:
- Load configuration and environment
- Initialize trading engine
- Provide CLI for pipelines (backtest, live, daily close, etc.)
"""

import argparse
import logging
import sys

from hybrid_ai_trading.config.settings import load_config
from hybrid_ai_trading.trade_engine import TradeEngine

logger = logging.getLogger("hybrid_ai_trading.main")


def main(argv: list[str] | None = None) -> int:
    """
    Main entrypoint for the Hybrid AI Trading system.

    Args:
        argv: Optional CLI arguments (defaults to sys.argv[1:]).

    Returns:
        int exit code (0=success, 1=error).
    """
    parser = argparse.ArgumentParser(description="Hybrid AI Trading CLI")
    parser.add_argument(
        "--pipeline",
        choices=["backtest", "daily_close", "paper_trade"],
        default="backtest",
        help="Which pipeline to run (default: backtest)",
    )
    args = parser.parse_args(argv)

    try:
        config = load_config()
        logger.info("Config loaded | project=%s", config.get("project", "UNKNOWN"))

        engine = TradeEngine(config=config)
        logger.info("Hybrid AI Trading Engine initialized.")

        if args.pipeline == "backtest":
            from hybrid_ai_trading.pipelines.backtest import run_backtest
            run_backtest(engine)
        elif args.pipeline == "daily_close":
            from hybrid_ai_trading.pipelines.daily_close import run_daily_close
            run_daily_close(engine)
        elif args.pipeline == "paper_trade":
            from hybrid_ai_trading.pipelines.paper_trade_demo import run_paper_trade
            run_paper_trade(engine)

        return 0
    except Exception as exc:  # noqa: BLE001
        logger.error("Fatal error during system startup: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
