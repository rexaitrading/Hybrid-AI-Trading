import argparse
import json

from hybrid_ai_trading.config.settings import CONFIG, load_config
from hybrid_ai_trading.execution.execution_engine import ExecutionEngine


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", required=True)
    p.add_argument("--side", required=True, choices=["BUY", "SELL", "buy", "sell"])
    p.add_argument("--qty", required=True, type=float)
    p.add_argument(
        "--price",
        type=float,
        default=None,
        help="Leave blank for market (engine may simulate fill)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Force dry_run regardless of config (debug)",
    )
    args = p.parse_args()

    load_config(force=True)
    engine = ExecutionEngine(dry_run=args.dry_run, config=CONFIG)
    res = engine.place_order(args.symbol, args.side.upper(), args.qty, price=args.price)
    print(json.dumps(res, indent=2, default=str))


if __name__ == "__main__":
    main()
