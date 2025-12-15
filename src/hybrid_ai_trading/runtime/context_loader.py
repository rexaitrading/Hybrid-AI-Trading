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


def _load_run_context_json(trading_date: date, logs_dir: Path) -> dict | None:
    """Load logs/run_context.json if present and stamped for trading_date. Return dict or None."""
    try:
        p = logs_dir / "run_context.json"
        if not p.exists():
            return None
        j = json.loads(p.read_text(encoding="utf-8"))
        if str(j.get("as_of_date", "")) != trading_date.isoformat():
            return None
        return j if isinstance(j, dict) else None
    except Exception:
        return None

def load_run_context_from_env() -> RunContext:
    """
    Canonical RunContext loader (fail-safe default = PAPER).

    Precedence:
      1) HAT_RUN_MODE
      2) HAT_MODE
      3) default: paper

    Accepted: live, paper, premarket

    Phase-0: prefer logs/run_context.json if present for today, else fall back to legacy files.
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

    # Prefer schema-locked run_context.json (Phase-0)
    jctx = _load_run_context_json(trading_date, logs_dir)

    # Phase4
    if jctx is not None and "phase4_ok_today" in jctx:
        phase4_ok = bool(jctx.get("phase4_ok_today"))
    else:
        phase4_ok = _load_phase4_today(trading_date, logs_dir)

    # BlockG: if run_context.json exists, use nvda_blockg_ready as Phase-0 default
    if jctx is not None and "nvda_blockg_ready" in jctx:
        blockg_ok = bool(jctx.get("nvda_blockg_ready"))
    else:
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
