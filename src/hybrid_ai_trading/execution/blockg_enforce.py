# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from hybrid_ai_trading.execution.blockg_errors import BlockGNotReady

def _repo_root() -> Path:
    # src/hybrid_ai_trading/execution/blockg_enforce.py -> repo root is 4 parents up
    return Path(__file__).resolve().parents[3]

def _default_status_path() -> Path:
    return _repo_root() / "logs" / "blockg_status_stub.json"

def load_blockg_status() -> Dict[str, Any]:
    """
    Load Block-G status JSON (fail-closed).

    Resolution order (tighten-only; never loosens):
      1) env HAT_BLOCKG_STATUS_PATH if set
      2) repo-root/logs/blockg_status_stub.json
    """
    path_s = (os.environ.get("HAT_BLOCKG_STATUS_PATH", "") or "").strip()
    p = Path(path_s) if path_s else _default_status_path()

    try:
        raw = p.read_text(encoding="utf-8")
        st = json.loads(raw)
        if not isinstance(st, dict):
            raise BlockGNotReady("BLOCK-G DENY: status not a dict")
        return st
    except FileNotFoundError:
        raise BlockGNotReady(f"BLOCK-G DENY: missing status file: {p}")
    except BlockGNotReady:
        raise
    except Exception as e:
        raise BlockGNotReady(f"BLOCK-G DENY: failed to read status: {e!r}")

def _load_blockg_status() -> Dict[str, Any]:
    # Backward-compatible alias used by callers/tests
    return load_blockg_status()

def require_blockg_ready_for_live(symbol: str, *, status: Optional[Dict[str, Any]] = None) -> None:
    """
    Fail-closed per-symbol readiness.
    - Unknown symbol => deny
    - Missing/invalid status => deny (BlockGNotReady)
    - <symbol>_blockg_ready != True => deny
    """
    sym = str(symbol or "").upper().strip()
    key_map = {"NVDA": "nvda_blockg_ready", "SPY": "spy_blockg_ready", "QQQ": "qqq_blockg_ready"}

    if sym not in key_map:
        raise BlockGNotReady(f"BLOCK-G DENY (live): unknown symbol={sym}")

    st = status if isinstance(status, dict) else _load_blockg_status()
    k = key_map[sym]
    ok = bool(st.get(k, False))
    if not ok:
        reasons = st.get("reasons_not_ready", [])
        raise BlockGNotReady(f"{k}=false reasons={reasons}")
