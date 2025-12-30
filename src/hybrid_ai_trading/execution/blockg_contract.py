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
    # Explicit kw flags
    for k in ("is_live", "live", "enforce_live"):
        if k in kwargs:
            return bool(kwargs[k])

    # ctx kw (RunContext-like) is authoritative
    ctx = kwargs.get("ctx", None)
    if ctx is not None:
        m = getattr(ctx, "mode", None)
        if isinstance(m, str) and m.strip().lower() == "live":
            return True
        ip = getattr(ctx, "is_paper", None)
        if ip is False:
            return True

    # is_paper kw passed explicitly (False => live intent)
    if "is_paper" in kwargs and bool(kwargs["is_paper"]) is False:
        return True

    # mode/run_mode kw
    mode = kwargs.get("mode") or kwargs.get("run_mode")
    if isinstance(mode, str) and mode.strip().lower() == "live":
        return True

    # Scan positional args for RunContext-like objects
    for a in args:
        m = getattr(a, "mode", None)
        if isinstance(m, str) and m.strip().lower() == "live":
            return True
        ip = getattr(a, "is_paper", None)
        if ip is False:
            return True

    # Env: paper flag (tests set HAT_IS_PAPER=0)
    if os.environ.get("HAT_IS_PAPER", "").strip() == "0":
        return True

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
    ensure_symbol_blockg_ready("NVDA", *args, **kwargs)
