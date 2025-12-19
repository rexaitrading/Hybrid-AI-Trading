from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional


class BlockGNotReadyError(RuntimeError):
    """Raised when Block-G contract says live trading is not allowed."""


def _repo_root() -> Path:
    # src/hybrid_ai_trading/blockg_status.py -> repo root = ../../
    return Path(__file__).resolve().parents[2]


def _contract_path() -> Path:
    # Allow override for tests/CI
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
    except Exception as e:
        raise BlockGNotReadyError(f"Block-G contract unreadable: {p} ({e})")


def ensure_symbol_live_allowed(symbol: str) -> None:
    """
    Fail-closed live gate: raises BlockGNotReadyError unless:
      - contract exists and is parseable
      - contract as_of_date == today
      - <symbol>_blockg_ready == true
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


def ensure_nvda_live_allowed() -> None:
    ensure_symbol_live_allowed("NVDA")