from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _append_jsonl(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Deterministic JSON for diffability
    line = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(line + "\n")


def append_intent(*, payload: Dict, path: str = "logs/portfolio_order_intents.jsonl") -> None:
    """
    Append an order-intent record deterministically.
    """
    _append_jsonl(Path(path), payload)


def append_fill(*, payload: Dict, path: str = "logs/portfolio_fills.jsonl") -> None:
    """
    Append a fill record. In paper mode this may be a stub/synthetic fill.
    File is always created deterministically.
    """
    _append_jsonl(Path(path), payload)


def write_daily_summary(*, rows: List[Dict[str, object]], path: str) -> None:
    """
    Deterministic CSV writer for daily summaries.
    - Stable header ordering: sorted union of keys.
    - If rows empty: write header-only "as_of_date" for determinism.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        with p.open("w", encoding="utf-8", newline="") as f:
            f.write("as_of_date\n")
        return

    fieldnames = sorted({k for r in rows for k in r.keys()})
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fieldnames})