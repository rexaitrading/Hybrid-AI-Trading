from __future__ import annotations

from hybrid_ai_trading.execution.blockg_enforce import BlockGNotReady
import json
import os
from pathlib import Path
from typing import Any, Dict
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
    status_path: str | None = None,
    status: dict | None = None,
    ctx: any | None = None,
) -> None:
    """
    Single semantics owner for Block-G gating.

    - ctx overrides env if provided (paper wins when ctx.is_paper True)
    - If paper and allow_paper=True: no-op
    - If live: fail-closed unless per-symbol readiness is True
    - status_path optional for tests; status optional for tests
    """
    # ctx precedence (paper-safe)
    try:
        if ctx is not None:
            ip = getattr(ctx, "is_paper", None)
            if ip is True:
                if allow_paper:
                    return
                raise BlockGNotReady("BLOCK-G DENY: allow_paper=False but ctx says paper")
            if ip is False:
                is_paper = False
    except Exception:
        pass

    # env/default
    if is_paper is None:
        is_paper = (os.environ.get("HAT_IS_PAPER", "").strip() == "1")

    if is_paper:
        if allow_paper:
            return
        raise BlockGNotReady("BLOCK-G DENY: allow_paper=False but running in paper mode")

    # Load status
    st = None
    if isinstance(status, dict):
        st = status
    else:
        p = (status_path or os.environ.get("HAT_BLOCKG_STATUS_PATH", "") or "").strip()
        if not p:
            raise BlockGNotReady("BLOCK-G DENY: missing HAT_BLOCKG_STATUS_PATH")
        try:
            with open(p, "r", encoding="utf-8") as f:
                st = json.load(f)
        except Exception as e:
            raise BlockGNotReady(f"BLOCK-G DENY: failed to read status: {e!r}")

    sym = (symbol or "").strip().upper()
    key_map = {"NVDA":"nvda_blockg_ready","SPY":"spy_blockg_ready","QQQ":"qqq_blockg_ready"}
    k = key_map.get(sym)
    if not k:
        raise BlockGNotReady(f"BLOCK-G DENY (live): unknown symbol={sym}")

    ok = bool(st.get(k, False))
    if not ok:
        reasons = st.get("reasons_not_ready", [])
        raise BlockGNotReady(f"{k}=false reasons={reasons}")

def assert_nvda_live_ready() -> None:
    # Back-compat wrapper used by order path patches
    ensure_symbol_blockg_ready("NVDA", allow_paper=True, is_paper=None, ctx=None)

# --- Backward-compatible aliases (used by smoke tests / older callers) ---
def require_symbol_ready(symbol: str) -> None:
    """Alias: require Block-G readiness for symbol (fail-closed)."""
    # Prefer the canonical helper if present in this module.
    try:
        ensure_symbol_blockg_ready(str(symbol), allow_paper=True, is_paper=False, ctx=None)  # type: ignore[name-defined]
        return
    except NameError:
        pass
    # Fallback: if module exposes assert_* helpers, use NVDA-specific when applicable.
    sym = str(symbol).upper().strip()
    if sym == "NVDA":
        try:
            assert_nvda_live_ready()  # type: ignore[name-defined]
            return
        except NameError:
            pass
    raise RuntimeError(f"BLOCKG_DENY: {sym}_not_ready")

def require_symbol_not_paper(symbol: str) -> None:
    """Alias: explicit live requirement for symbol readiness."""
    require_symbol_ready(symbol)
