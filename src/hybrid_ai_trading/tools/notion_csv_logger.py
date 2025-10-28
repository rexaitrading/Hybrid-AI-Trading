from __future__ import annotations

import csv
import os
import time
from dataclasses import asdict, dataclass
from typing import Iterable, Optional

# Columns align to your Notion DB import
COLUMNS = [
    "Date",
    "Ticker",
    "Setup",
    "Context",
    "EntryTime",
    "ExitTime",
    "Entry",
    "Exit",
    "Qty",
    "Fees",
    "Slippage",
    "RM",
    "PnL",
    "Notes",
    "ReplayID",
]


@dataclass
class TradeRow:
    Date: str
    Ticker: str
    Setup: str
    Context: str  # semicolon-joined multi-select, e.g. "TrendUp;HighVol"
    EntryTime: str  # ISO 8601 local, e.g. "2025-10-24T09:31"
    ExitTime: str
    Entry: float
    Exit: float
    Qty: int
    Fees: float
    Slippage: float
    RM: float  # R multiple
    PnL: float
    Notes: str
    ReplayID: str


class NotionCSVLogger:
    """
    Append-only CSV writer for trade rows (UTF-8, no BOM).
    Ensures header once; idempotent across runs.
    """

    def __init__(self, path: str):
        self.path = path
        self._fh = None
        self._writer = None
        os.makedirs(os.path.dirname(path), exist_ok=True)

        # Create file if missing and write header
        if not os.path.exists(self.path):
            with open(self.path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(COLUMNS)

    def __enter__(self):
        # append mode; newline='' for correct CSV on Windows
        self._fh = open(self.path, "a", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._fh, fieldnames=COLUMNS)
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if self._fh:
                self._fh.flush()
                os.fsync(self._fh.fileno())
        finally:
            if self._fh:
                self._fh.close()
            self._fh = None
            self._writer = None

    def log(self, row: TradeRow):
        self._writer.writerow(asdict(row))


# Convenience helper for quick logging without dataclass construction
def log_trade(path: str, **kwargs):
    row = TradeRow(**kwargs)
    with NotionCSVLogger(path) as log:
        log.log(row)
