from __future__ import annotations

import csv
from pathlib import Path


def log_trade(path: str, **fields) -> None:
    """
    Append a row to CSV at `path` (UTF-8 no BOM). If file is new, write header.
    Keys of `fields` become columns; values are written as-is (converted to str).
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    is_new = not p.exists()
    with p.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(fields.keys()))
        if is_new:
            w.writeheader()
        w.writerow({k: ("" if v is None else v) for k, v in fields.items()})
