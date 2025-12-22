from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


def _read_text_bom_safe(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def read_csv_rows(path: str | Path) -> List[Dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    raw = _read_text_bom_safe(p)
    if not raw.strip():
        return []
    reader = csv.DictReader(raw.splitlines())
    return [dict(r) for r in reader]


def write_csv_rows(path: str | Path, rows: Iterable[Dict[str, Any]], fieldnames: List[str]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    import io as _io
    s = _io.StringIO()
    w = csv.DictWriter(s, fieldnames=fieldnames, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in fieldnames})
    p.write_text(s.getvalue(), encoding="utf-8")


def append_jsonl(path: str | Path, obj: Dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(obj, ensure_ascii=True)
    with p.open("a", encoding="utf-8", newline="\n") as f:
        f.write(line + "\n")


def read_jsonl(path: str | Path) -> List[Dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    raw = _read_text_bom_safe(p)
    out: List[Dict[str, Any]] = []
    for ln in raw.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        out.append(json.loads(ln))
    return out
