from __future__ import annotations

import csv
from pathlib import Path


def log_trade(
    *,
    path: str,
    Date: str,
    Ticker: str,
    Setup: str,
    Context: str,
    EntryTime: str,
    ExitTime: str,
    Entry: float,
    Exit: float,
    Qty: int,
    Fees: float,
    Slippage: float,
    RM: float,
    PnL: float,
    Notes: str,
    ReplayID: str,
) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    header = [
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
    new_file = (not p.exists()) or p.stat().st_size == 0
    with p.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(header)
        w.writerow(
            [
                Date,
                Ticker,
                Setup,
                Context,
                EntryTime,
                ExitTime,
                Entry,
                Exit,
                Qty,
                Fees,
                Slippage,
                RM,
                PnL,
                Notes,
                ReplayID,
            ]
        )
