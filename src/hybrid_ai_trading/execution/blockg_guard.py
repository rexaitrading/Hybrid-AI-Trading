from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from typing import Any, Dict


class BlockGNotReadyError(RuntimeError):
    """Raised when Block-G contract says live trading is not allowed."""


def _repo_root() -> Path:
    # src/hybrid_ai_trading/execution/blockg_guard.py -> repo root = ../../..
    return Path(__file__).resolve().parents[3]


def _contract_path() -> Path:
    env = os.getenv("HAT_BLOCKG_CONTRACT_PATH", "").strip()
    if env:
        return Path(env)
    return _repo_root() / "logs" / "blockg_status_stub.json"


def _today_str() -> str:
    return date.today().isoformat()


def _load_contract() -> Dict[str, Any]:
    p = _contract_path()
    if not p.exists():
        raise BlockGNotReadyError(f"Block-G contract missing: {p}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        raise BlockGNotReadyError(f"Block-G contract unreadable: {p} ({e})")


def require_blockg_ready(symbol: str) -> None:
    """
    Fail-closed Block-G guard (pure Python).

    Enforces contract semantics:
      - contract exists and parses
      - as_of_date == today
      - <symbol>_blockg_ready == True
    """
    s = str(symbol).upper().strip()
    if not s:
        raise BlockGNotReadyError("Block-G: empty symbol")

    c = _load_contract()

    as_of = str(c.get("as_of_date", "")).strip()[:10]
    today = _today_str()
    if as_of != today:
        raise BlockGNotReadyError(f"Block-G contract stale: as_of_date={as_of!r} today={today!r}")

    key = f"{s.lower()}_blockg_ready"
    if bool(c.get(key)) is not True:
        raise BlockGNotReadyError(f"Block-G: {s} not live-ready (contract {key}=False)")
