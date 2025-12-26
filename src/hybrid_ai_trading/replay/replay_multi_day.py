from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from hybrid_ai_trading.replay.fill_models import DeterministicFillModel
from hybrid_ai_trading.replay.latency_models import DeterministicLatencyModel
from hybrid_ai_trading.replay.replay_session import (
    ReplaySessionArtifact,
    ReplaySummary,
    ReplayWindow,
    iso_utc_now,
    write_session_artifact,
    write_summary,
)

# Scaffold runner: deterministic outputs + Notion CSV.
# Replace synthetic trades with real bar replay engine later.


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="NVDA")
    ap.add_argument("--start-date", required=True)
    ap.add_argument("--end-date", required=True)
    ap.add_argument("--outdir", default="logs/replay")
    ap.add_argument("--fee-bps", type=float, default=1.0)
    ap.add_argument("--slip-bps", type=float, default=2.0)
    ap.add_argument("--lat-order-ms", type=int, default=50)
    ap.add_argument("--lat-fill-ms", type=int, default=80)
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    fill = DeterministicFillModel(fee_bps=args.fee_bps, slip_bps=args.slip_bps)
    lat = DeterministicLatencyModel(order_latency_ms=args.lat_order_ms, fill_latency_ms=args.lat_fill_ms)

    window = ReplayWindow(start_date=args.start_date, end_date=args.end_date)
    art = ReplaySessionArtifact(
        ts_utc=iso_utc_now(),
        as_of_date=datetime.now().astimezone().date().isoformat(),
        symbol=args.symbol.upper(),
        window=window,
        fill_model=f"deterministic_fee{args.fee_bps}_slip{args.slip_bps}",
        latency_model=f"deterministic_{lat.total_ms()}ms",
        bars_source="stub",
        notes="scaffold replay (replace with real multi-day bar replay engine)",
    )
    write_session_artifact(outdir / "replay_session.json", art)

    # Synthetic example (deterministic): 10 trades @ $100
    trades = 10
    px = 100.0
    qty = 1.0
    gross_pnl = 0.0
    fees = 0.0
    slips = 0.0
    for i in range(trades):
        side = "BUY" if (i % 2 == 0) else "SELL"
        fr = fill.fill(side=side, qty=qty, price=px)
        fees += fr.fee_usd
        slips += fr.slippage_usd

    net_pnl = gross_pnl - fees - slips
    summ = ReplaySummary(
        ts_utc=iso_utc_now(),
        as_of_date=art.as_of_date,
        symbol=art.symbol,
        window_start=args.start_date,
        window_end=args.end_date,
        trades=trades,
        gross_pnl=gross_pnl,
        net_pnl=net_pnl,
        est_fees=fees,
        est_slippage=slips,
        model_fill=art.fill_model,
        model_latency=art.latency_model,
    )
    write_summary(outdir / "replay_summary.json", summ)

    csv_path = outdir / "replay_summary_for_notion.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(asdict(summ).keys()))
        w.writeheader()
        w.writerow(asdict(summ))

    print(f"[replay] wrote {outdir / 'replay_session.json'}")
    print(f"[replay] wrote {outdir / 'replay_summary.json'}")
    print(f"[replay] wrote {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())