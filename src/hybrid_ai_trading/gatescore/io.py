from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, List

from .schemas import GateScoreDailyRow


def read_daily_csv(path: str | Path) -> List[GateScoreDailyRow]:
    p = Path(path)
    if not p.exists():
        return []
    rows: List[GateScoreDailyRow] = []
    with p.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for d in r:
            rows.append(
                GateScoreDailyRow(
                    as_of_date=str(d.get("as_of_date", ""))[:10],
                    symbol=str(d.get("symbol", "")).upper(),
                    count_signals=int(float(d.get("count_signals", 0) or 0)),
                    pnl_samples=int(float(d.get("pnl_samples", 0) or 0)),
                    mean_edge_ratio=float(d.get("mean_edge_ratio", 0) or 0),
                    mean_micro_score=float(d.get("mean_micro_score", 0) or 0),
                    mean_pnl=float(d.get("mean_pnl", 0) or 0),
                )
            )
    return rows


def write_daily_csv(path: str | Path, rows: Iterable[GateScoreDailyRow]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["as_of_date","symbol","count_signals","pnl_samples","mean_edge_ratio","mean_micro_score","mean_pnl"],
        )
        w.writeheader()
        for r in rows:
            w.writerow({
                "as_of_date": r.as_of_date,
                "symbol": r.symbol,
                "count_signals": r.count_signals,
                "pnl_samples": r.pnl_samples,
                "mean_edge_ratio": r.mean_edge_ratio,
                "mean_micro_score": r.mean_micro_score,
                "mean_pnl": r.mean_pnl,
            })