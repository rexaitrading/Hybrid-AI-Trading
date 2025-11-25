"""
QQQ ORB EV sweep.

Reads:
  research/qqq_orb_replay_trades_enriched.jsonl

Computes EV stats grouped by (orb_minutes, tp_pct):
  - n_trades
  - win_rate
  - avg_r
  - ev_r
  - avg_gross_pnl_pct

Writes:
  research/qqq_orb_ev_threshold_sweep.csv
"""

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, Any


def sweep_ev(input_path: Path, output_path: Path) -> None:
    if not input_path.exists():
        print(f"[qqq_orb_ev] Input file not found: {input_path}")
        return

    counts: Dict[tuple, int] = defaultdict(int)
    wins: Dict[tuple, int] = defaultdict(int)
    sum_r: Dict[tuple, float] = defaultdict(float)
    sum_pct: Dict[tuple, float] = defaultdict(float)

    with input_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue

            orb_minutes = rec.get("orb_minutes")
            tp_pct = rec.get("tp_pct")
            if orb_minutes is None or tp_pct is None:
                continue

            key = (int(orb_minutes), float(tp_pct))

            r = rec.get("r_multiple")
            if r is None:
                r = rec.get("gross_pnl_pct", 0.0)

            try:
                r_val = float(r)
            except (TypeError, ValueError):
                continue

            gross_pct = rec.get("gross_pnl_pct")
            try:
                gross_val = float(gross_pct) if gross_pct is not None else 0.0
            except (TypeError, ValueError):
                gross_val = 0.0

            counts[key] += 1
            sum_r[key] += r_val
            sum_pct[key] += gross_val

            outcome = rec.get("outcome")
            if outcome == "TP" or r_val > 0:
                wins[key] += 1

    if not counts:
        print("[qqq_orb_ev] No trades with orb_minutes+tp_pct metadata found.")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as csv_f:
        writer = csv.writer(csv_f)
        writer.writerow([
            "orb_minutes",
            "tp_pct",
            "n_trades",
            "win_rate",
            "avg_r",
            "ev_r",
            "avg_gross_pnl_pct",
        ])

        for (orb_minutes, tp_pct), n in sorted(counts.items()):
            n_trades = n
            if n_trades == 0:
                continue

            win_rate = wins[(orb_minutes, tp_pct)] / n_trades
            avg_r = sum_r[(orb_minutes, tp_pct)] / n_trades
            ev_r = avg_r
            avg_pct = sum_pct[(orb_minutes, tp_pct)] / n_trades

            writer.writerow([
                orb_minutes,
                tp_pct,
                n_trades,
                round(win_rate, 4),
                round(avg_r, 4),
                round(ev_r, 4),
                round(avg_pct, 6),
            ])

    print(f"[qqq_orb_ev] Wrote EV sweep to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="QQQ ORB EV sweep")
    parser.add_argument(
        "--input",
        default="research/qqq_orb_replay_trades_enriched.jsonl",
        help="Input enriched JSONL file",
    )
    parser.add_argument(
        "--output",
        default="research/qqq_orb_ev_threshold_sweep.csv",
        help="Output CSV path",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    sweep_ev(input_path=input_path, output_path=output_path)


if __name__ == "__main__":
    main()