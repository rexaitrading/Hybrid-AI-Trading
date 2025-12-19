from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional


class BlockGNotReady(RuntimeError):
    pass


def _today_str() -> str:
    return date.today().isoformat()


def _repo_root_from_here() -> Path:
    # .../src/hybrid_ai_trading/execution/blockg_enforce.py -> repo root
    return Path(__file__).resolve().parents[4]


def _default_status_paths() -> list[Path]:
    root = _repo_root_from_here()
    return [
        root / "logs" / "blockg_status_stub.json",
        root / ".intel" / "blockg_status_stub.json",
    ]


def load_blockg_status(path: Optional[str] = None) -> Dict[str, Any]:
    if path:
        p = Path(path)
        raw = p.read_text(encoding="utf-8")
        return json.loads(raw)

    for p in _default_status_paths():
        if p.exists():
            raw = p.read_text(encoding="utf-8")
            return json.loads(raw)

    raise FileNotFoundError("Block-G status JSON not found in logs/ or .intel/.")


def _sym_ready_key(symbol: str) -> str:
    s = symbol.upper()
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
    Hard fail-closed for LIVE orders only.
    Caller decides paper vs live; this function is ONLY for live.
    """
    st = status if status is not None else load_blockg_status()

    as_of = str(st.get("as_of_date", ""))[:10]
    if as_of != _today_str():
        raise BlockGNotReady(f"BLOCK-G: date mismatch as_of_date={as_of} today={_today_str()}")

    key = _sym_ready_key(symbol)
    if not key:
        raise BlockGNotReady(f"BLOCK-G: unknown symbol '{symbol}' (fail-closed)")

    if not bool(st.get(key, False)):
        reasons = st.get("reasons_not_ready", [])
        raise BlockGNotReady(f"BLOCK-G: {key}=false for {symbol}. reasons={reasons}")