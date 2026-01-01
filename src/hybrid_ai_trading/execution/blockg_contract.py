from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

# Canonical exception type expected by tests/chokepoints
from hybrid_ai_trading.execution.blockg_enforce import BlockGNotReady


@dataclass(frozen=True)
class BlockGDecision:
    ok: bool
    reason: str
    status_path: str


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _status_path(repo_root: Optional[Path] = None) -> Path:
    env_p = os.environ.get("HAT_BLOCKG_STATUS_PATH", "").strip()
    if env_p:
        return Path(env_p)
    root = repo_root or _default_repo_root()
    return root / "logs" / "blockg_status_stub.json"


def read_blockg_status(repo_root: Optional[Path] = None) -> Dict[str, Any]:
    p = _status_path(repo_root)
    if not p.exists():
        raise FileNotFoundError(f"Block-G status missing: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def is_symbol_ready(symbol: str, st: Dict[str, Any], repo_root: Optional[Path] = None) -> BlockGDecision:
    sym = (symbol or "").upper().strip()
    sp = str(_status_path(repo_root))

    if sym == "NVDA":
        ok = bool(st.get("nvda_blockg_ready", False))
        return BlockGDecision(ok=ok, reason="nvda_blockg_ready=false" if not ok else "ok", status_path=sp)

    key = f"{sym.lower()}_blockg_ready"
    ok = bool(st.get(key, False))
    return BlockGDecision(ok=ok, reason=f"{key}=false" if not ok else "ok", status_path=sp)


def _infer_is_live(*args: Any, **kwargs: Any) -> bool:
    """
    Determine if call is LIVE.
    Policy: ctx wins over env/meta. If ctx says paper => not live (paper-safe bypass).
    Supports RunContext and SimpleNamespace-style ctx objects used in tests.
    """
    ctx = kwargs.get("ctx", None)
    try:
        if ctx is not None:
            m = str(getattr(ctx, "mode", "") or "").strip().lower()
            ip = getattr(ctx, "is_paper", None)
            # paper wins (fail-closed toward paper when explicit)
            if m == "paper" or ip is True:
                return False
            if m == "live" or ip is False:
                return True
    except Exception:
        pass

    # Existing behavior fallback (env/meta)  keep semantics stable
    try:
        is_paper = kwargs.get("is_paper", None)
        if is_paper is True:
            return False
        if is_paper is False:
            return True
    except Exception:
        pass

    # env fallback: HAT_IS_PAPER=0 means live
    try:
        import os
        return str(os.environ.get("HAT_IS_PAPER", "1")).strip() == "0"
    except Exception:
        return False

def ensure_symbol_blockg_ready(symbol: str, *args: Any, **kwargs: Any) -> None:
    if not _infer_is_live(*args, **kwargs):
        return

    repo_root = kwargs.get("repo_root", None)
    st = kwargs.get("status", None)
    if st is None:
        st = read_blockg_status(repo_root=repo_root)

    decision = is_symbol_ready(symbol, st, repo_root=repo_root)
    if not decision.ok:
        raise BlockGNotReady(f"BLOCK-G DENY: {symbol} {decision.reason} ({decision.status_path})")


def assert_nvda_live_ready(*args: Any, **kwargs: Any) -> None:
    """
    Fail-closed NVDA live arming gate.
    This is a STRICT guard: it does NOT infer live/paper. Callers use it right before any NVDA live order.
    Requires BOTH BlockG contract ready AND NVDA live stamp today.
    """
    st = read_blockg_status(repo_root=kwargs.get("repo_root", None))
    if not bool(st.get("nvda_blockg_ready", False)):
        sp = str(_status_path(kwargs.get("repo_root", None)))
        raise BlockGNotReady(f"BLOCK-G DENY: NVDA nvda_blockg_ready=false ({sp})")
    # Require NVDA live stamp (separate human arming consent gate)
    from hybrid_ai_trading.broker.ib_safe import require_nvda_live_stamp  # local import
    require_nvda_live_stamp("NVDA")
