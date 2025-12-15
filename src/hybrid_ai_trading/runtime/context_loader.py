from __future__ import annotations

import os
import json
from datetime import date, datetime
from pathlib import Path
from hybrid_ai_trading.runtime.run_context import RunContext, RunMode


def _norm_mode(s: str) -> str:
    return (s or "").strip().lower()


def _env_trading_date() -> date:
    """
    trading_date authority:
      1) HAT_TRADING_DATE=YYYY-MM-DD (optional override)
      2) date.today() (default)
    """
    raw = (os.getenv("HAT_TRADING_DATE", "") or "").strip()
    if raw:
        try:
            return datetime.strptime(raw, "%Y-%m-%d").date()
        except Exception:
            pass
    return date.today()



def _load_phase4_today(trading_date: date, logs_dir: Path) -> bool:
    try:
        p = logs_dir / "phase4_validation_passed.json"
        if not p.exists():
            return False
        j = json.loads(p.read_text(encoding="utf-8"))
        return (
            str(j.get("as_of_date", "")) == trading_date.isoformat()
            and bool(j.get("phase4_ok_today"))
        )
    except Exception:
        return False


def _load_blockg_today(trading_date: date, logs_dir: Path) -> bool:
    try:
        p = logs_dir / "blockg_status_stub.json"
        if not p.exists():
            return False
        j = json.loads(p.read_text(encoding="utf-8"))
        return (
            str(j.get("as_of_date", "")) == trading_date.isoformat()
            and bool(j.get("nvda_blockg_ready"))
        )
    except Exception:
        return False

def load_run_context_from_env() -> RunContext:
    """
    Canonical RunContext loader (fail-safe default = PAPER).

    Precedence:
      1) HAT_RUN_MODE
      2) HAT_MODE
      3) default: paper

    Accepted: live, paper, premarket
    """
    m = _norm_mode(os.getenv("HAT_RUN_MODE", ""))
    if not m:
        m = _norm_mode(os.getenv("HAT_MODE", ""))

    if m == "live":
        mode = RunMode.LIVE
    elif m == "premarket":
        mode = RunMode.PREMARKET
    else:
        mode = RunMode.PAPER

    trading_date = _env_trading_date()
    repo_root = Path(".")
    logs_dir = repo_root / "logs"

    phase4_ok = _load_phase4_today(trading_date, logs_dir)
    blockg_ok = _load_blockg_today(trading_date, logs_dir)

    return RunContext(
        mode=mode,
        trading_date=trading_date,
        phase4_passed=phase4_ok,
        blockg_ready=blockg_ok,
        repo_root=repo_root,
        logs_dir=logs_dir,
    )


def is_live_env() -> bool:
    """
    Legacy-friendly check: True only when env resolves to LIVE.
    """
    return load_run_context_from_env().is_live
