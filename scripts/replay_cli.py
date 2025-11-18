#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from hybrid_ai_trading.tools.bar_replay import load_bars, run_replay


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Bar replay JSON wrapper")
    p.add_argument("--csv", "--file", dest="csv", required=True)
    p.add_argument("--symbol", required=True)
    p.add_argument("--mode", choices=["fast", "step", "auto"], default="fast")
    p.add_argument("--speed", type=float, default=10.0)
    p.add_argument("--fees-per-share", dest="fees_per_share", type=float, default=0.0)
    p.add_argument("--slippage-ps", dest="slippage_ps", type=float, default=0.0)
    p.add_argument("--orb-minutes", type=int, default=5)
    p.add_argument("--risk-cents", type=float, default=20.0)
    p.add_argument("--max-qty", type=int, default=200)
    p.add_argument("--force-exit", action="store_true")
    p.add_argument("--summary", choices=["json", "text"], default="json")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    path = Path(args.csv)
    df = load_bars(str(path))

    # Map "fast" to auto mode for bar_replay
    mode = "auto" if args.mode == "fast" else args.mode

    # Call run_replay with the arguments that exist in bar_replay.run_replay
    res = run_replay(
        df=df,
        symbol=args.symbol,
        mode=mode,
        speed=args.speed,
        fees_per_share=args.fees_per_share,
        orb_minutes=args.orb_minutes,
        risk_cents=args.risk_cents,
        max_qty=args.max_qty,
        force_exit=args.force_exit,
    )

    # Defensive extraction of summary fields
    try:
        bars = int(getattr(res, "bars", len(df)))
    except Exception:
        bars = len(df)

    try:
        trades = int(getattr(res, "trades", 0))
    except Exception:
        trades = 0

    try:
        pnl = float(getattr(res, "pnl", 0.0))
    except Exception:
        pnl = 0.0

    final_qty = 0
    try:
        pos = getattr(res, "final_pos", None)
        if pos is not None and hasattr(pos, "qty"):
            final_qty = int(pos.qty or 0)
    except Exception:
        final_qty = 0

    summary = {
        "symbol": args.symbol,
        "bars": bars,
        "trades": trades,
        "pnl": pnl,
        "final_qty": final_qty,
        "fees_ps": float(args.fees_per_share),
        "slippage_ps": float(args.slippage_ps),
    }

    # tests expect the last line of stdout to be a JSON object (one object, one real newline)
    line = json.dumps(summary, separators=(",", ":")) + "\n"
    sys.stdout.write(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())