"""
Phase-5 EV vs realized PnL report.

Reads Phase-5 LIVE CSVs (NVDA/SPY/QQQ) and computes, per regime:

- Number of SELL trades in the last N days.
- Average realized PnL per SELL.
- Average EV.
- Average (realized PnL - EV).

Usage:
    python tools/phase5_ev_vs_realized_report.py --days-back 5
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
from pathlib import Path
from typing import Dict, List, Tuple, Any


REGIMES = [
    "NVDA_BPLUS_LIVE",
    "SPY_ORB_LIVE",
    "QQQ_ORB_LIVE",
]

CSV_MAP = {
    "NVDA_BPLUS_LIVE": Path("logs/nvda_phase5_paper_for_notion.csv"),
    "SPY_ORB_LIVE": Path("logs/spy_phase5_paper_for_notion.csv"),
    "QQQ_ORB_LIVE": Path("logs/qqq_phase5_paper_for_notion.csv"),
}


def parse_iso_ts_to_date(ts: str) -> dt.date | None:
    """
    Parse ISO timestamp string to date (UTC), falling back to None on failure.
    Examples of accepted ts:
        "2025-11-30T19:04:17Z"
        "2025-11-30T19:04:17"
    """
    if not ts:
        return None
    s = ts.strip()
    if not s:
        return None
    # Remove trailing 'Z' if present
    if s.endswith("Z"):
        s = s[:-1]
    try:
        # fromisoformat handles "YYYY-MM-DDTHH:MM:SS"
        dt_obj = dt.datetime.fromisoformat(s)
    except Exception:
        return None
    return dt_obj.date()


def try_parse_float(val: Any) -> float | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def collect_regime_stats(days_back: int) -> Dict[str, Dict[str, Any]]:
    """
    For each regime, collect SELL trades from the last N days and compute stats.
    """
    today = dt.date.today()
    cutoff = today - dt.timedelta(days=days_back)

    stats: Dict[str, Dict[str, Any]] = {}
    for regime in REGIMES:
        stats[regime] = {
            "n_sell": 0,
            "realized_list": [],  # type: List[float]
            "ev_list": [],        # type: List[float]
        }

    for regime, csv_path in CSV_MAP.items():
        if not csv_path.exists():
            continue

        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row_regime = (row.get("regime") or "").strip()
                if row_regime != regime:
                    continue

                side = (row.get("side") or "").strip().upper()
                if side != "SELL":
                    continue

                ts_str = row.get("ts") or ""
                d = parse_iso_ts_to_date(ts_str)
                if d is None or d < cutoff:
                    continue

                realized = try_parse_float(row.get("realized_pnl"))
                ev = try_parse_float(row.get("ev"))

                if realized is None:
                    continue

                stats[regime]["n_sell"] += 1
                stats[regime]["realized_list"].append(realized)

                if ev is not None:
                    stats[regime]["ev_list"].append(ev)

    # Compute aggregates
    for regime, s in stats.items():
        n = s["n_sell"]
        if n > 0:
            r_list: List[float] = s["realized_list"]
            e_list: List[float] = s["ev_list"]
            s["avg_realized"] = sum(r_list) / len(r_list)
            s["avg_ev"] = sum(e_list) / len(e_list) if e_list else None
            if e_list:
                # Align lengths by min length
                m = min(len(r_list), len(e_list))
                gaps = [r_list[i] - e_list[i] for i in range(m)]
                s["avg_gap"] = sum(gaps) / len(gaps)
            else:
                s["avg_gap"] = None
        else:
            s["avg_realized"] = None
            s["avg_ev"] = None
            s["avg_gap"] = None

    return stats


def format_float(val: float | None) -> str:
    if val is None:
        return "   -   "
    return f"{val: .6f}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase-5 EV vs realized PnL report.")
    parser.add_argument(
        "--days-back",
        type=int,
        default=5,
        help="Number of calendar days back from today to include (default: 5)",
    )
    args = parser.parse_args()

    stats = collect_regime_stats(days_back=args.days_back)

    print(f"\n[EV-REPORT] Phase-5 EV vs realized PnL (last {args.days_back} day(s))")
    print("  Today:", dt.date.today().isoformat())
    print("\n  Per-regime SELL-trade stats:\n")

    header = (
        f"{'Regime':<20} {'#SELL':>5} {'AvgRealized':>12} {'AvgEV':>12} {'Avg(realized-EV)':>18}"
    )
    print(header)
    print("-" * len(header))

    for regime in REGIMES:
        s = stats.get(regime, {})
        n_sell = s.get("n_sell", 0)
        avg_r = s.get("avg_realized")
        avg_e = s.get("avg_ev")
        avg_gap = s.get("avg_gap")

        print(
            f"{regime:<20} "
            f"{n_sell:>5d} "
            f"{format_float(avg_r):>12} "
            f"{format_float(avg_e):>12} "
            f"{format_float(avg_gap):>18}"
        )

    print("\n[NOTE] This report uses SELL rows only, over the last N calendar days,")
    print("       based on ts date from the Phase-5 LIVE CSVs.")
    print("       Use this as a promotion check before Phase 6.")
    

if __name__ == "__main__":
    main()