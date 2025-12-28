from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict
class BlockGNotReady(RuntimeError):
    pass

def _repo_root() -> Path:
    # src/hybrid_ai_trading/execution/blockg_contract.py -> repo root
    return Path(__file__).resolve().parents[3]

def is_paper_env() -> bool:
    return os.getenv("HAT_IS_PAPER", "1").strip() == "1"

def blockg_status_path() -> Path:
    p = os.getenv("HAT_BLOCKG_STATUS_PATH", "").strip()
    if p:
        return Path(p)
    return _repo_root() / "logs" / "blockg_status_stub.json"

def read_blockg_status() -> Dict[str, Any]:
    fp = blockg_status_path()
    if not fp.exists():
        return {"nvda_blockg_ready": False, "reasons_not_ready": ["blockg_status_missing"]}
    try:
        return json.loads(fp.read_bytes().decode("utf-8-sig"))  # tolerate UTF-8 BOM
    except Exception:
        return {"nvda_blockg_ready": False, "reasons_not_ready": ["blockg_status_unreadable"]}

def ensure_symbol_blockg_ready(
    symbol: str,
    allow_paper: bool = True,
    is_paper: bool | None = None,
    ctx: Any | None = None,
) -> None:
    """
    Single semantics owner for Block-G gating (signature matches blockg_enforce.py).

    - If paper and allow_paper=True: no-op
    - If live: fail-closed unless per-symbol readiness is True

    ctx is accepted for API compatibility (RunContext), but not required.
    """
    if is_paper is None:
        is_paper = is_paper_env()

    if is_paper:
        if allow_paper:
            return
        raise BlockGNotReady("BLOCK-G DENY: allow_paper=False but running in paper mode")

    st = read_blockg_status()
    sym = (symbol or "").strip().upper()

    key_map = {
        "NVDA": "nvda_blockg_ready",
        "SPY":  "spy_blockg_ready",
        "QQQ":  "qqq_blockg_ready",
    }
    k = key_map.get(sym)
    if not k:
        raise BlockGNotReady(f"BLOCK-G DENY (live): unknown symbol={sym}")

    ok = bool(st.get(k, False))
    if not ok:
        reasons = st.get("reasons_not_ready", [])
        raise BlockGNotReady(f"BLOCK-G DENY (live): {k}!=True reasons={reasons}")

def assert_nvda_live_ready() -> None:
    # Back-compat wrapper used by order path patches
    ensure_symbol_blockg_ready("NVDA", allow_paper=True, is_paper=None, ctx=None)
