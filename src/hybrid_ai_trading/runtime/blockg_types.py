from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class BlockGStatus:
    ts_utc: str
    as_of_date: str

    phase4_ok_today: bool
    phase23_health_ok_today: bool
    ev_hard_daily_ok_today: bool

    gatescore_fresh_today: bool
    gatescore_samples_ok_today: bool
    gatescore_threshold_ok_today: bool
    gatescore_ok_today: bool

    nvda_blockg_ready: bool
    spy_blockg_ready: bool
    qqq_blockg_ready: bool

    raw: Optional[Dict[str, Any]] = None

    @property
    def is_today(self) -> bool:
        try:
            return self.as_of_date == date.today().isoformat()
        except Exception:
            return False


def _bool(d: Dict[str, Any], key: str, default: bool = False) -> bool:
    return bool(d.get(key, default))


def _str(d: Dict[str, Any], key: str, default: str = "") -> str:
    v = d.get(key, default)
    return "" if v is None else str(v)


def load_blockg_status(path: Path) -> BlockGStatus:
    if not path.exists():
        return BlockGStatus(
            ts_utc="",
            as_of_date="",
            phase4_ok_today=False,
            phase23_health_ok_today=False,
            ev_hard_daily_ok_today=False,
            gatescore_fresh_today=False,
            gatescore_samples_ok_today=False,
            gatescore_threshold_ok_today=False,
            gatescore_ok_today=False,
            nvda_blockg_ready=False,
            spy_blockg_ready=False,
            qqq_blockg_ready=False,
            raw={"error": "missing_blockg_status_stub", "path": str(path)},
        )

    with path.open("r", encoding="utf-8") as f:
        d = json.load(f)

    return BlockGStatus(
        ts_utc=_str(d, "ts_utc", ""),
        as_of_date=_str(d, "as_of_date", ""),
        phase4_ok_today=_bool(d, "phase4_ok_today", False),
        phase23_health_ok_today=_bool(d, "phase23_health_ok_today", False),
        ev_hard_daily_ok_today=_bool(d, "ev_hard_daily_ok_today", False),
        gatescore_fresh_today=_bool(d, "gatescore_fresh_today", False),
        gatescore_samples_ok_today=_bool(d, "gatescore_samples_ok_today", False),
        gatescore_threshold_ok_today=_bool(d, "gatescore_threshold_ok_today", False),
        gatescore_ok_today=_bool(d, "gatescore_ok_today", False),
        nvda_blockg_ready=_bool(d, "nvda_blockg_ready", False),
        spy_blockg_ready=_bool(d, "spy_blockg_ready", False),
        qqq_blockg_ready=_bool(d, "qqq_blockg_ready", False),
        raw=d,
    )