from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


def _default_contract_path() -> Path:
    # Single source of truth: PowerShell builder writes into repo logs/
    repo_root = Path(__file__).resolve().parents[3]
    envp = os.environ.get("HAT_BLOCKG_CONTRACT_PATH", "").strip()
    if envp:
        return Path(envp)
    return repo_root / "logs" / "blockg_status_stub.json"


def read_contract(path: Optional[Path] = None) -> Dict[str, Any]:
    p = path or _default_contract_path()
    try:
        txt = p.read_text(encoding="utf-8")
        obj = json.loads(txt)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def symbol_ready(contract: Dict[str, Any], symbol: str) -> bool:
    # contract keys are expected like: nvda_blockg_ready / spy_blockg_ready / qqq_blockg_ready
    key = f"{str(symbol).strip().lower()}_blockg_ready"
    v = contract.get(key, False)
    return bool(v)

def require_blockg_ready_for_live_symbol(symbol: str) -> None:
    """
    Back-compat shim for execution_engine_phase5_guard.py.
    Fail-closed: if contract missing/unreadable or symbol not ready, raise RuntimeError.
    """
    c = read_contract()
    if not symbol_ready(c, symbol):
        raise RuntimeError(f"BLOCK-G DENY (live): {str(symbol).upper()}_blockg_ready!=True")
