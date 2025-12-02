from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from hybrid_ai_trading.risk.ev_band_flags import evaluate_ev_band_for_trade


LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "ev_band_debug.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Log-only EV-band probe for a single (regime, EV) pair."
    )
    parser.add_argument("--regime", required=True, help="Trading regime, e.g. NVDA_BPLUS_LIVE")
    parser.add_argument("--ev", required=True, type=float, help="Expected value (EV) for the trade")
    parser.add_argument("--symbol", default=None, help="Optional symbol tag, e.g. NVDA / SPY")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    flags: Dict[str, Any] = evaluate_ev_band_for_trade(regime=args.regime, ev=args.ev)

    record: Dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "symbol": args.symbol,
        "regime": args.regime,
        "ev": args.ev,
    }
    record.update(flags)

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()