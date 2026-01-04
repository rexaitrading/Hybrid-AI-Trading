from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict
from hybrid_ai_trading.execution.blockg_errors import BlockGNotReady


def _as_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    return s in ("1", "true", "yes", "y", "ok", "pass", "passed")


def _repo_root_from_here() -> Path:
    # .../src/hybrid_ai_trading/execution/blockg_contract_reader.py -> repo root = parents[3]
    # execution -> hybrid_ai_trading -> src -> repo_root
    try:
        return Path(__file__).resolve().parents[3]
    except Exception:
        return Path.cwd()


def get_default_blockg_status_path() -> Path:
    """
    Env override precedence (institutional, deterministic):
      1) HAT_BLOCKG_STATUS_PATH   (canonical)
      2) HAT_BLOCKG_CONTRACT_PATH (legacy/back-compat)
      3) repo_root/logs/blockg_status_stub.json
    """
    p = os.environ.get("HAT_BLOCKG_STATUS_PATH", "").strip()
    if p:
        return Path(p)
    p = os.environ.get("HAT_BLOCKG_CONTRACT_PATH", "").strip()
    if p:
        return Path(p)
    return _repo_root_from_here() / "logs" / "blockg_status_stub.json"

@dataclass(frozen=True)
class BlockGStatus:
    # Contract dates
    as_of_date: str
    date: str

    # Market calendar / clarity
    market_closed_today: bool

    # Per-symbol readiness
    nvda_blockg_ready: bool
    spy_blockg_ready: bool
    qqq_blockg_ready: bool

    # Policy booleans (top-level)
    phase4_ok_today: bool
    phase23_health_ok_today: bool
    ev_hard_daily_ok_today: bool
    gatescore_fresh_today: bool
    gatescore_ok_today: bool

    reasons_not_ready: tuple[str, ...]


def load_blockg_status(path: str | Path) -> BlockGStatus:
    p = Path(path)
    raw = p.read_text(encoding="utf-8")
    j: Dict[str, Any] = json.loads(raw)

    reasons = j.get("reasons_not_ready") or []
    if not isinstance(reasons, list):
        reasons = [str(reasons)]

    as_of = str(j.get("as_of_date", ""))[:10]
    date = str(j.get("date", ""))[:10]  # may be empty on older contracts

    return BlockGStatus(
        as_of_date=as_of,
        date=date,

        market_closed_today=_as_bool(j.get("market_closed_today", False)),

        nvda_blockg_ready=_as_bool(j.get("nvda_blockg_ready", False)),
        spy_blockg_ready=_as_bool(j.get("spy_blockg_ready", False)),
        qqq_blockg_ready=_as_bool(j.get("qqq_blockg_ready", False)),

        phase4_ok_today=_as_bool(j.get("phase4_ok_today", False)),
        phase23_health_ok_today=_as_bool(j.get("phase23_health_ok_today", False)),
        ev_hard_daily_ok_today=_as_bool(j.get("ev_hard_daily_ok_today", False)),
        gatescore_fresh_today=_as_bool(j.get("gatescore_fresh_today", False)),
        gatescore_ok_today=_as_bool(j.get("gatescore_ok_today", False)),

        reasons_not_ready=tuple(str(x) for x in reasons),
    )


def require_blockg_date_today(*, status: BlockGStatus, today: str) -> None:
    """
    Fail-closed: contract must explicitly match today's date.
    Prefer `date` if present, otherwise fallback to `as_of_date` for backward compatibility.
    """
    today10 = str(today).strip()[:10]
    contract10 = (str(status.date).strip()[:10] or str(status.as_of_date).strip()[:10])

    if not contract10:
        raise BlockGNotReady(f"BLOCK-G FAIL-CLOSED: contract_date_missing today={today10}")


    if contract10 != today10:
        raise BlockGNotReady(
            f"BLOCK-G FAIL-CLOSED: contract_not_today contract_date={contract10} today={today10}"
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
        raise BlockGNotReady(
            f"BLOCK-G FAIL-CLOSED: symbol={sym} as_of_date={s.as_of_date} reasons={list(s.reasons_not_ready)}"
        )
