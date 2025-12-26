from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass(frozen=True)
class BlockGStatus:
    as_of_date: str
    nvda_blockg_ready: bool
    spy_blockg_ready: bool
    qqq_blockg_ready: bool
    reasons_not_ready: tuple[str, ...]


def _as_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    return s in ("1", "true", "yes", "y", "ok", "pass", "passed")


def load_blockg_status(path: str | Path) -> BlockGStatus:
    p = Path(path)
    raw = p.read_text(encoding="utf-8")
    j: Dict[str, Any] = json.loads(raw)

    reasons = j.get("reasons_not_ready") or []
    if not isinstance(reasons, list):
        reasons = [str(reasons)]

    return BlockGStatus(
        as_of_date=str(j.get("as_of_date", ""))[:10],
        nvda_blockg_ready=_as_bool(j.get("nvda_blockg_ready", False)),
        spy_blockg_ready=_as_bool(j.get("spy_blockg_ready", False)),
        qqq_blockg_ready=_as_bool(j.get("qqq_blockg_ready", False)),
        reasons_not_ready=tuple(str(x) for x in reasons),
    )


def require_blockg_ready_for_live_symbol(*, symbol: str, status_path: str | Path) -> None:
    sym = str(symbol).upper()
    s = load_blockg_status(status_path)

    if sym == "NVDA":
        ok = s.nvda_blockg_ready
    elif sym == "SPY":
        ok = s.spy_blockg_ready
    elif sym == "QQQ":
        ok = s.qqq_blockg_ready
    else:
        ok = False

    if not ok:
        raise RuntimeError(
            f"BLOCK-G FAIL-CLOSED: symbol={sym} as_of_date={s.as_of_date} reasons={list(s.reasons_not_ready)}"
        )