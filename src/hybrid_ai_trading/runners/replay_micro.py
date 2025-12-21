# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
from datetime import date


def main() -> int:
    p = argparse.ArgumentParser("replay_micro")
    p.add_argument("--symbol", default="NVDA")
    p.add_argument("--as-of-date", default=date.today().isoformat())
    p.add_argument("--note", default="", help="Operator note (optional)")
    args = p.parse_args()

    print(
        {
            "status": "ok_stub_phase1_replay_micro",
            "symbol": str(args.symbol).upper(),
            "as_of_date": str(args.as_of_date)[:10],
            "note": args.note,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
