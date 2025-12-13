from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class TradeRow:
    ts: str
    strategy: str
    broker: str
    symbol: str
    side: str
    qty: float
    px: float
    order_type: str
    order_id: str
    status: str
    pnl: float
    meta: str
    risk: str


_HEADER = [
    "ts","strategy","broker","symbol","side","qty","px","order_type",
    "order_id","status","pnl","meta","risk"
]


def _repo_root() -> Path:
    # src/hybrid_ai_trading/utils/trades_csv.py -> repo root is 3 parents up from src/
    return Path(__file__).resolve().parents[3]


def trades_csv_path() -> Path:
    return _repo_root() / "logs" / "trades.csv"


def append_trade_csv_row(row: TradeRow) -> Path:
    out = trades_csv_path()
    out.parent.mkdir(parents=True, exist_ok=True)

    must_write_header = (not out.exists()) or (out.stat().st_size == 0)

    with out.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_HEADER)
        if must_write_header:
            w.writeheader()
        w.writerow(asdict(row))

    return out


def now_ts() -> str:
    return datetime.now().isoformat(timespec="seconds")