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
        j = json.loads(p.read_text(encoding="utf-8-sig"))
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
        j = json.loads(p.read_text(encoding="utf-8-sig"))
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
        j = json.loads(p.read_text(encoding="utf-8-sig"))
        if str(j.get("as_of_date", "")) != trading_date.isoformat():
            return None
        return j if isinstance(j, dict) else None
    except Exception:
        return None

def load_run_context_from_env() -> RunContext:
    """
    Canonical RunContext loader (fail-safe default = PAPER).

    Phase-1B: hydrate Phase-1A safety flags from logs/run_context.json when present.
    Missing fields are FAIL-SAFE defaults (False).
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

    # Prefer schema-locked run_context.json (Phase-0/1A)
    jctx = _load_run_context_json(trading_date, logs_dir) if "_load_run_context_json" in globals() else None

    # Phase4 (legacy fallback)
    if jctx is not None and "phase4_ok_today" in jctx:
        phase4_ok = bool(jctx.get("phase4_ok_today"))
    else:
        phase4_ok = _load_phase4_today(trading_date, logs_dir)

    # BlockG (Phase-0 default: nvda readiness)
    if jctx is not None and "nvda_blockg_ready" in jctx:
        blockg_ok = bool(jctx.get("nvda_blockg_ready"))
    else:
        blockg_ok = _load_blockg_today(trading_date, logs_dir)

    # Phase-1A flags (hydrate from run_context.json only; fail-safe defaults)
    phase23_ok = bool(jctx.get("phase23_health_ok_today")) if jctx is not None else False
    ev_hard_ok = bool(jctx.get("ev_hard_daily_ok_today")) if jctx is not None else False
    gatescore_fresh = bool(jctx.get("gatescore_fresh_today")) if jctx is not None else False

    return RunContext(
        mode=mode,
        trading_date=trading_date,
        phase4_passed=phase4_ok,
        blockg_ready=blockg_ok,
        phase23_ok=phase23_ok,
        ev_hard_ok=ev_hard_ok,
        gatescore_fresh=gatescore_fresh,
        repo_root=repo_root,
        logs_dir=logs_dir,
    )

def is_live_env(ctx: RunContext | None = None) -> bool:
    """
    Unified LIVE-mode check via RunContext (single authority).
    Preserves operator override: IBKR_LIVE=1.
    """
    import os
    if os.getenv("IBKR_LIVE", "0") == "1":
        return True
    c = ctx or load_run_context_from_env()
    return bool(c.is_live)
