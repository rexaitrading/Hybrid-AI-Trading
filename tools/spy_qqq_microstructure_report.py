"""
Phase-2 GateScore-adjacent microstructure / EV / PnL summary for SPY & QQQ.

Input:
- logs/spy_phase5_paper_for_notion_ev_diag_micro.csv
- logs/qqq_phase5_paper_for_notion_ev_diag_micro.csv

Output:
- logs/spy_qqq_microstructure_report.csv

For each (symbol, regime, ms_range_bucket, ms_trend_label) it computes:
- trade_count
- avg_ev
- avg_realized_pnl_paper
- win_rate (fraction of trades with realized_pnl_paper > 0)
- avg_ev_gap_abs (if present)

This is LOG-ONLY analysis; it does not affect any risk or gating.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional


INPUT_FILES = [
    ("SPY", Path("logs") / "spy_phase5_paper_for_notion_ev_diag_micro.csv"),
    ("QQQ", Path("logs") / "qqq_phase5_paper_for_notion_ev_diag_micro.csv"),
]


@dataclass
class Row:
    symbol: str
    regime: str
    ev: float
    pnl: float
    ev_gap_abs: Optional[float]
    ms_range_pct: float
    ms_trend_flag: int


def _to_float(val, default: float = 0.0) -> float:
    try:
        if val is None or val == "":
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def _to_int(val, default: int = 0) -> int:
    try:
        if val is None or val == "":
            return default
        return int(float(val))
    except (TypeError, ValueError):
        return default


def load_rows(path: Path, symbol_hint: str) -> List[Row]:
    if not path.exists():
        print(f"[MICRO-REPORT] SKIP {symbol_hint}: {path} not found.")
        return []

    print(f"[MICRO-REPORT] Loading {symbol_hint} from {path} ...")
    rows: List[Row] = []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            symbol = (raw.get("symbol") or "").strip() or symbol_hint
            regime = (raw.get("regime") or "").strip()

            ev = _to_float(raw.get("ev"), 0.0)
            pnl = _to_float(raw.get("realized_pnl_paper"), 0.0)
            ev_gap_abs = raw.get("ev_gap_abs")
            ev_gap_val = _to_float(ev_gap_abs, 0.0) if ev_gap_abs not in (None, "",) else None

            ms_range_pct = _to_float(raw.get("ms_range_pct"), 0.0)
            ms_trend_flag = _to_int(raw.get("ms_trend_flag"), 0)

            rows.append(
                Row(
                    symbol=symbol,
                    regime=regime,
                    ev=ev,
                    pnl=pnl,
                    ev_gap_abs=ev_gap_val,
                    ms_range_pct=ms_range_pct,
                    ms_trend_flag=ms_trend_flag,
                )
            )

    print(f"[MICRO-REPORT] Loaded {len(rows)} rows for {symbol_hint}.")
    return rows


def bucket_range(ms_range_pct: float) -> str:
    """
    Very simple buckets for now (can be tuned later):

    - < 0.002  -> 'flat'
    - < 0.010  -> 'normal'
    - >= 0.010 -> 'wide'
    """
    if ms_range_pct < 0.002:
        return "flat"
    if ms_range_pct < 0.010:
        return "normal"
    return "wide"


def label_trend(flag: int) -> str:
    if flag > 0:
        return "up"
    if flag < 0:
        return "down"
    return "flat"


def build_summary(all_rows: List[Row]) -> List[Dict[str, object]]:
    groups: Dict[Tuple[str, str, str, str], List[Row]] = defaultdict(list)

    for r in all_rows:
        r_bucket = bucket_range(r.ms_range_pct)
        t_label = label_trend(r.ms_trend_flag)
        key = (r.symbol, r.regime, r_bucket, t_label)
        groups[key].append(r)

    summary_rows: List[Dict[str, object]] = []

    for (symbol, regime, r_bucket, t_label), rows in sorted(groups.items()):
        if not rows:
            continue

        n = len(rows)
        avg_ev = sum(r.ev for r in rows) / n if n else 0.0
        avg_pnl = sum(r.pnl for r in rows) / n if n else 0.0
        wins = sum(1 for r in rows if r.pnl > 0)
        win_rate = wins / n if n else 0.0

        ev_gaps = [r.ev_gap_abs for r in rows if r.ev_gap_abs is not None]
        avg_ev_gap = sum(ev_gaps) / len(ev_gaps) if ev_gaps else 0.0

        summary_rows.append(
            {
                "symbol": symbol,
                "regime": regime,
                "ms_range_bucket": r_bucket,
                "ms_trend_label": t_label,
                "trade_count": n,
                "avg_ev": round(avg_ev, 6),
                "avg_realized_pnl_paper": round(avg_pnl, 6),
                "win_rate": round(win_rate, 3),
                "avg_ev_gap_abs": round(avg_ev_gap, 6),
            }
        )

    return summary_rows


def write_report(rows: List[Dict[str, object]], out_path: Path) -> None:
    if not rows:
        print("[MICRO-REPORT] No data to write.")
        return

    fieldnames = [
        "symbol",
        "regime",
        "ms_range_bucket",
        "ms_trend_label",
        "trade_count",
        "avg_ev",
        "avg_realized_pnl_paper",
        "win_rate",
        "avg_ev_gap_abs",
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"[MICRO-REPORT] Wrote summary report to {out_path}")


def main() -> None:
    print("[MICRO-REPORT] === SPY/QQQ microstructure EV/PnL summary ===")
    all_rows: List[Row] = []
    for symbol, path in INPUT_FILES:
        all_rows.extend(load_rows(path, symbol))

    if not all_rows:
        print("[MICRO-REPORT] No rows loaded; nothing to summarize.")
        return

    summary = build_summary(all_rows)
    out = Path("logs") / "spy_qqq_microstructure_report.csv"
    write_report(summary, out)

    # Also print a small sample to console for quick inspection
    print("\n[MICRO-REPORT] Top summary rows:")
    for row in summary[:20]:
        print(
            f"  {row['symbol']:3s} {row['regime']:15s} "
            f"range={row['ms_range_bucket']:<6s} trend={row['ms_trend_label']:<4s} "
            f"n={row['trade_count']:2d} ev={row['avg_ev']:.4f} "
            f"pnl={row['avg_realized_pnl_paper']:.4f} win={row['win_rate']:.2f}"
        )

    print("\n[MICRO-REPORT] === End SPY/QQQ microstructure EV/PnL summary ===")


if __name__ == "__main__":
    main()