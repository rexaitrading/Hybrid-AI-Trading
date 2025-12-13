from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional


@dataclass
class Sample:
    as_of_date: str
    score: float


def _today_local() -> str:
    # local date is correct for "today-ness" checks in your PS scripts
    return datetime.now().strftime("%Y-%m-%d")


def _safe_float(x: object) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _iter_jsonl(path: Path) -> Iterable[Sample]:
    """
    Accepts JSONL lines with any of these keys:
      - date / as_of_date / day
      - score / gatescore / gate_score
    If date missing -> ignored (fail-closed).
    """
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue

            day = (obj.get("as_of_date") or obj.get("date") or obj.get("day") or "")
            day = str(day).strip()
            if not day:
                continue

            s = _safe_float(obj.get("score") or obj.get("gatescore") or obj.get("gate_score"))
            if s is None:
                continue

            yield Sample(as_of_date=day[:10], score=s)


def _iter_csv(path: Path) -> Iterable[Sample]:
    """
    Accepts CSV with any of these columns:
      - as_of_date / date / day
      - score / gatescore / gate_score
    """
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            day = (row.get("as_of_date") or row.get("date") or row.get("day") or "")
            day = str(day).strip()
            if not day:
                continue
            s = _safe_float(row.get("score") or row.get("gatescore") or row.get("gate_score"))
            if s is None:
                continue
            yield Sample(as_of_date=day[:10], score=s)


def compute_daily_summary(input_path: Path, out_path: Path, today: str) -> int:
    if not input_path.exists():
        return 2

    ext = input_path.suffix.lower()
    if ext == ".jsonl":
        samples = list(_iter_jsonl(input_path))
    elif ext == ".csv":
        samples = list(_iter_csv(input_path))
    else:
        # unsupported -> fail-closed
        return 3

    todays = [s.score for s in samples if s.as_of_date == today]
    # Write header always; write today row only if we have data.
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["as_of_date", "samples", "score"])
        if todays:
            avg = sum(todays) / float(len(todays))
            w.writerow([today, len(todays), f"{avg:.6f}"])

    # exit 0 even if no today row written (fail-closed happens upstream)
    return 0


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: python compute_gatescore_daily_summary.py <input.(jsonl|csv)> <out.csv>")
        return 1
    inp = Path(sys.argv[1])
    out = Path(sys.argv[2])
    today = _today_local()
    return compute_daily_summary(inp, out, today)


if __name__ == "__main__":
    raise SystemExit(main())