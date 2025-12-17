from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


LOGS_DIR = Path("logs")
CONTRACT_PATH = LOGS_DIR / "blockg_status_stub.json"


@dataclass(frozen=True)
class BlockGDecision:
    as_of_date: str
    symbol: str
    ready: bool
    reason: str


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _get_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        t = v.strip().lower()
        if t in {"true", "1", "yes", "y"}:
            return True
        if t in {"false", "0", "no", "n"}:
            return False
    return False


def _load_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8")
    # BOM-safe
    if raw and ord(raw[0]) == 65279:
        raw = raw.lstrip("\ufeff")
    return json.loads(raw)


def require_blockg_ready(symbol: str) -> BlockGDecision:
    """
    Contract-only Block-G gate. No recomputation. Fail-closed.
    """
    sym = (symbol or "").strip().upper()
    if not sym:
        return BlockGDecision(False, "symbol_empty", "")
    c = _load_contract()
    if not c:
        return BlockGDecision(False, "contract_missing", "")

    today = _today_str()
    as_of = str(c.get("as_of_date") or "")
    if as_of != today:
        return BlockGDecision(as_of_date=as_of, symbol=sym, ready=False, reason=f"stale_contract as_of={as_of} today={today}")

    # required common fields
    if not _get_bool(c.get("phase4_ok_today")):
        return BlockGDecision(as_of_date=as_of, symbol=sym, ready=False, reason="phase4_not_ok")
    if not _get_bool(c.get("phase23_health_ok_today")):
        return BlockGDecision(as_of_date=as_of, symbol=sym, ready=False, reason="phase23_not_ok")
    if not _get_bool(c.get("ev_hard_daily_ok_today")):
        return BlockGDecision(as_of_date=as_of, symbol=sym, ready=False, reason="ev_hard_not_ok")

    # gatescore ok (prefer per-symbol)
    per = f"{sym.lower()}_gatescore_ok_today"
    gs_ok = _get_bool(c.get(per)) if per in c else _get_bool(c.get("gatescore_ok_today"))
    if not gs_ok:
        return BlockGDecision(as_of_date=as_of, symbol=sym, ready=False, reason="gatescore_not_ok")

    # per-symbol ready flag
    flag_map = {"NVDA": "nvda_blockg_ready", "SPY": "spy_blockg_ready", "QQQ": "qqq_blockg_ready"}
    f = flag_map.get(sym)
    if not f or f not in c:
        return BlockGDecision(as_of_date=as_of, symbol=sym, ready=False, reason="symbol_flag_missing")
    if not _get_bool(c.get(f)):
        return BlockGDecision(as_of_date=as_of, symbol=sym, ready=False, reason="symbol_not_ready")

    return BlockGDecision(True, "ok", as_of)



