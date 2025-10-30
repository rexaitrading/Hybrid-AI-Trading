from __future__ import annotations

import argparse
import json
import sys

import pandas as pd

from hybrid_ai_trading.tools.bar_replay import run_replay


def main(argv=None):
    ap = argparse.ArgumentParser(description="Replay wrapper (JSON/Text summary)")
    ap.add_argument(
        "--csv",
        type=str,
        required=True,
        help="CSV with OHLCV (timestamp,open,high,low,close,volume)",
    )
    ap.add_argument("--symbol", type=str, default="TEST")
    ap.add_argument(
        "--mode", type=str, default="fast", choices=["step", "auto", "fast"]
    )
    ap.add_argument("--speed", type=float, default=5.0)
    ap.add_argument("--fees-per-share", type=float, default=0.003)
    ap.add_argument(
        "--slippage-ps", type=float, default=0.000, help="Slippage per share each side"
    )
    ap.add_argument("--orb-minutes", type=int, default=5)
    ap.add_argument("--risk-cents", type=float, default=20.0)
    ap.add_argument("--max-qty", type=int, default=200)
    ap.add_argument("--force-exit", action="store_true")
    ap.add_argument("--summary", type=str, choices=["text", "json"], default="json")
    args = ap.parse_args(argv)

    df = pd.read_csv(args.csv)
    res = run_replay(
        df,
        symbol=args.symbol,
        mode=args.mode,
        speed=args.speed,
        fees_per_share=args.fees_per_share,
        slippage_ps=args.slippage_ps,
        orb_minutes=args.orb_minutes,
        risk_cents=args.risk_cents,
        max_qty=args.max_qty,
        force_exit=args.force_exit,
    )

    if args.summary == "json":
        out = {
            "symbol": args.symbol,
            "bars": int(getattr(res, "bars", 0)),
            "trades": int(getattr(res, "trades", 0)),
            "pnl": float(getattr(res, "pnl", 0.0)),
            "final_qty": int(getattr(getattr(res, "final_pos", None), "qty", 0) or 0),
            "entry_px": (
                None if getattr(res, "entry_px", None) is None else float(res.entry_px)
            ),
            "exit_px": (
                None if getattr(res, "exit_px", None) is None else float(res.exit_px)
            ),
            "fees_ps": float(args.fees_per_share),
            "slippage_ps": float(args.slippage_ps),
        }
        print(json.dumps(out, separators=(",", ":")))
    else:
        print(
            f"Summary | symbol={args.symbol} "
            f"bars={getattr(res,'bars',0)} trades={getattr(res,'trades',0)} pnl={getattr(res,'pnl',0.0):.2f} "
            f"final_qty={getattr(getattr(res,'final_pos',None),'qty',0)} "
            f"entry_px={getattr(res,'entry_px',None)} exit_px={getattr(res,'exit_px',None)} "
            f"fees_ps={args.fees_per_share} slippage_ps={args.slippage_ps}"
        )


if __name__ == "__main__":
    main()
