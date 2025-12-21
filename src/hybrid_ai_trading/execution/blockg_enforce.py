from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional

import json

import os

class BlockGNotReady(RuntimeError):
    pass


def _today_str() -> str:
    return date.today().isoformat()


def _repo_root() -> Path:
    # .../src/hybrid_ai_trading/execution/blockg_enforce.py -> repo root
    return Path(__file__).resolve().parents[4]


def _default_paths() -> list[Path]:
    root = _repo_root()
    return [
        root / "logs" / "blockg_status_stub.json",
        root / ".intel" / "blockg_status_stub.json",
    ]


def load_blockg_status(path: Optional[str] = None) -> Dict[str, Any]:
    if path:
        p = Path(path)
        raw = p.read_text(encoding="utf-8-sig")
        return json.loads(raw)

    # Env override (deterministic): HAT_BLOCKG_STATUS_PATH points to contract JSON
    p_env = os.environ.get("HAT_BLOCKG_STATUS_PATH", "").strip()
    if p_env:
        pe = Path(p_env)
        if pe.exists():
            raw = pe.read_text(encoding="utf-8-sig")
            return json.loads(raw)
    for p in _default_paths():
        if p.exists():
            raw = p.read_text(encoding="utf-8-sig")
            return json.loads(raw)

    raise BlockGNotReady("BLOCK-G: status file missing (fail-closed)")


def _sym_ready_key(symbol: str) -> str:
    s = (symbol or "").upper().strip()
    if s == "NVDA":
        return "nvda_blockg_ready"
    if s == "SPY":
        return "spy_blockg_ready"
    if s == "QQQ":
        return "qqq_blockg_ready"
    # Conservative default: unknown symbols are not allowed for live
    return ""


def require_blockg_ready_for_live(symbol: str, status: Optional[Dict[str, Any]] = None) -> None:
    """
    Fail-closed readiness gate.

    Test contract:
    - Unknown symbol => raise BlockGNotReady (fail-closed)
    - If provided status has nvda_blockg_ready=False => raise and message contains 'nvda_blockg_ready=false'
    - If status is None => load from default contract JSON
    """
    st = status if status is not None else load_blockg_status()

    key = _sym_ready_key(symbol)
    if not key:
        raise BlockGNotReady(f"BLOCK-G: unknown symbol '{symbol}' (fail-closed)")

    if not bool(st.get(key, False)):
        reasons = st.get("reasons_not_ready", [])
        raise BlockGNotReady(f"BLOCK-G: {key}=false for {symbol}. reasons={reasons}")
