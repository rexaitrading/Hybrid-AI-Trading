"""
Block-G contract helper.

- Reads logs/blockg_status_stub.json
- Validates "today-ness" & freshness
- Exposes per-symbol readiness checks for live trading.

Contract expectations from PowerShell builders:
- logs/blockg_status_stub.json has fields:
    ts_utc: ISO timestamp
    as_of_date: "YYYY-MM-DD"
    phase23_health_ok_today: bool
    ev_hard_daily_ok_today: bool
    gatescore_fresh_today: bool
    nvda_blockg_ready: bool
    spy_blockg_ready: bool
    qqq_blockg_ready: bool
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_STATUS_PATH = Path(__file__).resolve().parents[3] / "logs" / "blockg_status_stub.json"


@dataclass
class BlockGStatus:
    ts_utc: str
    as_of_date: str
    phase23_health_ok_today: bool
    ev_hard_daily_ok_today: bool
    gatescore_fresh_today: bool
    nvda_blockg_ready: bool
    spy_blockg_ready: bool
    qqq_blockg_ready: bool
    raw: Dict[str, Any]

    @property
    def is_today(self) -> bool:
        """Return True if as_of_date == today's date (local)."""
        try:
            return self.as_of_date == date.today().isoformat()
        except Exception:
            return False


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"true", "1", "yes", "y"}:
            return True
        if v in {"false", "0", "no", "n"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return False


def load_blockg_status(path: Optional[Path] = None) -> BlockGStatus:
    """
    Load Block-G status stub JSON and map to BlockGStatus.

    Raises FileNotFoundError if the JSON does not exist.
    """
    status_path = path or DEFAULT_STATUS_PATH

    # BOM-safe read: some writers may include UTF-8 BOM.
    text = status_path.read_text(encoding="utf-8")
    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff")

    data = json.loads(text)

    return BlockGStatus(
        ts_utc=str(data.get("ts_utc", "")),
        as_of_date=str(data.get("as_of_date", "")),
        phase23_health_ok_today=_coerce_bool(data.get("phase23_health_ok_today", False)),
        ev_hard_daily_ok_today=_coerce_bool(data.get("ev_hard_daily_ok_today", False)),
        gatescore_fresh_today=_coerce_bool(data.get("gatescore_fresh_today", False)),
        nvda_blockg_ready=_coerce_bool(data.get("nvda_blockg_ready", False)),
        spy_blockg_ready=_coerce_bool(data.get("spy_blockg_ready", False)),
        qqq_blockg_ready=_coerce_bool(data.get("qqq_blockg_ready", False)),
        raw=data,
    )


def _is_nvda_ready(status: BlockGStatus) -> bool:
    """
    NVDA contract readiness:

    - status.is_today
    - phase23_health_ok_today
    - ev_hard_daily_ok_today
    - gatescore_fresh_today
    - nvda_blockg_ready
    """
    return (
        status.is_today
        and status.phase23_health_ok_today
        and status.ev_hard_daily_ok_today
        and status.gatescore_fresh_today
        and status.nvda_blockg_ready
    )


def _is_spy_ready(status: BlockGStatus) -> bool:
    return status.is_today and status.spy_blockg_ready


def _is_qqq_ready(status: BlockGStatus) -> bool:
    return status.is_today and status.qqq_blockg_ready


def is_symbol_ready(symbol: str, status: Optional[BlockGStatus] = None) -> bool:
    """
    Return True if the given symbol is Block-G ready for *today*.

    - symbol: "NVDA", "SPY", "QQQ" (case-insensitive)
    - status: optional pre-loaded BlockGStatus
    """
    status = status or load_blockg_status()
    sym = symbol.strip().upper()

    if sym == "NVDA":
        return _is_nvda_ready(status)
    if sym == "SPY":
        return _is_spy_ready(status)
    if sym == "QQQ":
        return _is_qqq_ready(status)

    # Unknown symbol: conservative default
    return False


class BlockGNotReadyError(RuntimeError):
    """Raised when Block-G contract does not permit live trading for the symbol."""


def assert_symbol_ready_for_live(symbol: str, status: Optional[BlockGStatus] = None) -> None:
    """
    Hard contract enforcement:

    Raises BlockGNotReadyError if Block-G does not allow symbol for live trading.
    """
    status = status or load_blockg_status()
    if not is_symbol_ready(symbol, status=status):
        msg = (
            f"Block-G contract does NOT allow live trading for {symbol}. "
            f"as_of_date={status.as_of_date!r}, "
            f"phase23_health_ok_today={status.phase23_health_ok_today}, "
            f"ev_hard_daily_ok_today={status.ev_hard_daily_ok_today}, "
            f"gatescore_fresh_today={status.gatescore_fresh_today}, "
            f"nvda_blockg_ready={status.nvda_blockg_ready}, "
            f"spy_blockg_ready={status.spy_blockg_ready}, "
            f"qqq_blockg_ready={status.qqq_blockg_ready}"
        )
        raise BlockGNotReadyError(msg)


def ensure_symbol_blockg_ready(symbol: str, status: Optional[BlockGStatus] = None) -> None:
    """
    Legacy helper used by guards/tests.

    Raises BlockGNotReadyError if Block-G does not allow the symbol
    to trade live today.
    """
    assert_symbol_ready_for_live(symbol, status=status)