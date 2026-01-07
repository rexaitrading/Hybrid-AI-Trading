from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from hybrid_ai_trading.execution.blockg_errors import BlockGNotReady


@dataclass(frozen=True)
class LiveArmToken:
    symbol: str
    as_of_date: str
    expires_utc: str


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _token_path(symbol: str) -> Path:
    """Resolve live-arm token path. Tests can override via HAT_LIVE_READY_STAMP_PATH."""
    envp = os.getenv("HAT_LIVE_READY_STAMP_PATH", "").strip()
    if envp:
        return Path(envp)
    # default per-symbol token file
    sym = (symbol or "").upper().strip()
    return Path("logs") / f"{sym.lower()}_live_ready_stamp.json"

def require_live_arm(symbol: str) -> None:
    sym = (symbol or "").upper().strip()
    p = _token_path(sym)
    if not p.exists():
        raise BlockGNotReady(f"LIVE ARM FAIL-CLOSED: missing {p.as_posix()}")

    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        raise BlockGNotReady(f"LIVE ARM FAIL-CLOSED: invalid_json path={p.as_posix()} err={e}")

    as_of = str(obj.get("as_of_date", "")).strip()
    exp   = str(obj.get("expires_utc", "")).strip()
    # Legacy compatibility: allow blank expires_utc (fail-closed still enforced via as_of_date==today)
    if not exp:
        # Default to end-of-day UTC for today
        exp = f"{as_of}T23:59:59Z"
    sym2  = str(obj.get("symbol", "")).strip().upper()

    if sym2 and (sym2 != sym):
        raise BlockGNotReady(f"LIVE ARM FAIL-CLOSED: symbol_mismatch token={sym2} expected={sym}")

    today = datetime.now().strftime("%Y-%m-%d")
    if as_of != today:
        raise BlockGNotReady(f"LIVE ARM FAIL-CLOSED: as_of_date={as_of} expected={today}")

    try:
        exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=timezone.utc)
    except Exception:
        raise BlockGNotReady(f"LIVE ARM FAIL-CLOSED: expires_utc invalid: {exp}")

    now = datetime.now(timezone.utc)
    if now >= exp_dt:
        raise BlockGNotReady(f"LIVE ARM FAIL-CLOSED: expired expires_utc={exp} now_utc={now.isoformat()}")