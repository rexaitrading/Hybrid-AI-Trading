from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Iterable, List

from .schemas import GateScoreDailySummaryRow, GateScoreEventRow


def _open_text_bom_safe(path: Path, mode: str):
    # "utf-8-sig" strips BOM if present; safe for files written by PS 5.1
    return path.open(mode, encoding="utf-8-sig", newline="")


def read_csv_dicts(path: str) -> List[Dict[str, str]]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    with _open_text_bom_safe(p, "r") as f:
        r = csv.DictReader(f)
        return [dict(row) for row in r]


def write_csv_dicts(path: str, rows: Iterable[Dict[str, object]], fieldnames: List[str]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k) for k in fieldnames})


def append_jsonl(path: str, payload: Dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, ensure_ascii=False)
    with p.open("a", encoding="utf-8", newline="\n") as f:
        f.write(line + "\n")


def read_daily_summary_rows(path: str) -> List[GateScoreDailySummaryRow]:
    out: List[GateScoreDailySummaryRow] = []
    for d in read_csv_dicts(path):
        out.append(GateScoreDailySummaryRow.from_dict(d))
    return out


def append_event(path: str, ev: GateScoreEventRow) -> None:
    append_jsonl(path, asdict(ev))