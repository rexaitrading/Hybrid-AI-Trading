from __future__ import annotations

import json
import os
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional

from hybrid_ai_trading.runtime.run_context import RunContext, RunMode


def _repo_root() -> Path:
    # src/hybrid_ai_trading/runtime/run_context_builder.py -> repo root = ../../..
    return Path(__file__).resolve().parents[3]


def _logs_dir(repo_root: Optional[Path] = None) -> Path:
    rr = repo_root or _repo_root()
    return rr / "logs"


def _today() -> date:
    return date.today()


def _parse_mode(val: Optional[str]) -> RunMode:
    v = (val or "").strip().lower()
    if v in ("premarket", "pre-market", "pre_market"):
        return RunMode.PREMARKET
    if v in ("paper", "sim", "sandbox"):
        return RunMode.PAPER
    if v in ("live",):
        return RunMode.LIVE
    if v in ("notion", "export"):
        return RunMode.NOTION
    # Default: PAPER (fail-safe)
    return RunMode.PAPER


def load_run_context(
    *,
    repo_root: Optional[Path] = None,
    mode: Optional[str] = None,
    symbol: Optional[str] = None,
    trading_date: Optional[date] = None,
) -> RunContext:
    """
    Single source of truth builder.
    Priority:
      explicit args > env vars > safe defaults.

    Env vars (backward compatible):
      HAT_RUN_MODE, HAT_SYMBOL, HAT_TRADING_DATE(YYYY-MM-DD)
    """
    rr = repo_root or _repo_root()
    logs = _logs_dir(rr)

    env_mode = os.getenv("HAT_RUN_MODE")
    env_symbol = os.getenv("HAT_SYMBOL")
    env_day = os.getenv("HAT_TRADING_DATE")

    m = _parse_mode(mode or env_mode)
    s = (symbol or env_symbol)
    if s:
        s = s.strip().upper()

    d = trading_date
    if d is None and env_day:
        try:
            d = date.fromisoformat(env_day.strip()[:10])
        except Exception:
            d = None
    if d is None:
        d = _today()

    # Read-only safety snapshots (best-effort)
    phase4_passed = False
    try:
        phase4_passed = bool((logs / "phase4_validation_passed.json").exists())
    except Exception:
        phase4_passed = False

    blockg_ready = False
    try:
        p = logs / "blockg_status_stub.json"
        if p.exists():
            obj: Dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
            as_of = str(obj.get("as_of_date", "")).strip()[:10]
            if as_of == d.isoformat():
                if s:
                    key = f"{s.lower()}_blockg_ready"
                    blockg_ready = bool(obj.get(key)) is True
                else:
                    # if no symbol scope, we don’t claim ready
                    blockg_ready = False
    except Exception:
        blockg_ready = False

    return RunContext(
        mode=m,
        trading_date=d,
        symbol=s,
        phase4_passed=phase4_passed,
        blockg_ready=blockg_ready,
        repo_root=rr,
        logs_dir=logs,
    )


def with_symbol(ctx: RunContext, symbol: str) -> RunContext:
    return replace(ctx, symbol=str(symbol).strip().upper())


def with_mode(ctx: RunContext, mode: RunMode) -> RunContext:
    return replace(ctx, mode=mode)
