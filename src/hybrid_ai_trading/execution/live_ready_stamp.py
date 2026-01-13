from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from hybrid_ai_trading.runtime.run_context import RunContext
from pathlib import Path
from typing import Any, Dict, Optional


class LiveStampNotReady(RuntimeError):
    pass


_DEFAULT_STAMP_PATH = Path("logs") / "nvda_live_ready_stamp.json"
_ENV_KEY = "HAT_LIVE_READY_STAMP_PATH"


def _today_utc_yyyy_mm_dd() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _today_from_runcontext(symbol: str) -> str:
    """
    A3 single-truth: for LIVE gating, prefer RunContext as_of_date (market-aware).
    Fail-open is NOT allowed; if RunContext is unavailable, fall back to UTC today.
    """
    try:
        s = (symbol or "NVDA").upper().strip() or "NVDA"
        mkt = str(os.environ.get("HAT_MARKET", "US")).strip().upper() or "US"
        ctx = RunContext.from_env_and_args(symbol=s, regime="unknown", market=mkt)
        d = str(getattr(ctx, "as_of_date", "") or "")[:10]
        if d:
            return d
    except Exception:
        pass
    return _today_utc_yyyy_mm_dd()



def _is_live() -> bool:
    return str(os.environ.get("HAT_IS_PAPER", "1")).strip() == "0"


def load_live_ready_stamp(path: Optional[str] = None) -> Dict[str, Any]:
    p = Path(path or os.environ.get(_ENV_KEY) or _DEFAULT_STAMP_PATH)
    try:
        # utf-8-sig to tolerate BOM on Windows
        raw = p.read_text(encoding="utf-8-sig")
        return json.loads(raw)
    except FileNotFoundError:
        raise LiveStampNotReady(f"Live-ready stamp missing at: {p}")
    except Exception as e:
        raise LiveStampNotReady(f"Live-ready stamp invalid at: {p}: {type(e).__name__}: {e}")


def require_nvda_live_stamp(symbol: str) -> None:
    """
    Human arming consent gate (separate from BlockG).
    Fail-closed: if live mode and symbol is NVDA, require today's stamp nvda_live_ready=true.
    """
    s = (symbol or "").upper().strip()
    if not _is_live():
        return
    if s != "NVDA":
        return

    d = load_live_ready_stamp()
    as_of = str(d.get("as_of_date") or "")[:10]
    ok = bool(d.get("nvda_live_ready", False))
    today = _today_from_runcontext(s)
    if as_of != today:
        raise LiveStampNotReady(f"NVDA live stamp not for today: as_of_date={as_of} today={today}")
    if not ok:
        raise LiveStampNotReady("NVDA live stamp nvda_live_ready=false")
