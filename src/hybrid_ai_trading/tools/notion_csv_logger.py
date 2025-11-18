#!/usr/bin/env python
"""
hybrid_ai_trading.tools.notion_csv_logger

Minimal shim used by bar_replay via replay_logger_hook.log_closed_trade.

For Phase-8 bar replay, we just append each closed trade to
.intel/replay_trades.csv so you can later import into Notion or analyze.

This keeps the dependency surface tiny and avoids breaking bar replay
if full Notion integration is not wired yet.
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Mapping, Any

LOG_PATH = Path(".intel") / "replay_trades.csv"

FIELDNAMES = [
    "ts",
    "symbol",
    "side",
    "qty",
    "entry",
    "exit",
    "pnl",
    "R",
    "pattern",
    "regime",
    "notes",
]


def _coalesce(mapping: Mapping[str, Any], *keys: str, default: str = "") -> str:
    for k in keys:
        if k in mapping and mapping[k] not in (None, ""):
            return str(mapping[k])
    return default


def log_trade(trade: Mapping[str, Any]) -> None:
    """
    Append a single closed trade to .intel/replay_trades.csv.

    The exact shape of 	rade depends on bar_replay; we gracefully
    coalesce a few common key names so this stays robust:
      - symbol / ticker
      - side / direction
      - qty / size / quantity
      - entry / entry_price
      - exit / exit_price
      - pnl / pnl_realized
      - R / r_multiple
      - pattern / tag
      - regime
      - notes

    If some fields are missing, they are left blank instead of raising.
    """
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    row = {k: "" for k in FIELDNAMES}
    row["ts"] = _coalesce(trade, "ts", default=datetime.utcnow().isoformat())
    row["symbol"] = _coalesce(trade, "symbol", "ticker")
    row["side"] = _coalesce(trade, "side", "direction")
    row["qty"] = _coalesce(trade, "qty", "size", "quantity")
    row["entry"] = _coalesce(trade, "entry", "entry_price")
    row["exit"] = _coalesce(trade, "exit", "exit_price")
    row["pnl"] = _coalesce(trade, "pnl", "pnl_realized")
    row["R"] = _coalesce(trade, "R", "r_multiple")
    row["pattern"] = _coalesce(trade, "pattern", "tag")
    row["regime"] = _coalesce(trade, "regime")
    row["notes"] = _coalesce(trade, "notes")

    new_file = not LOG_PATH.exists()
    with LOG_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if new_file:
            writer.writeheader()
        writer.writerow(row)