from __future__ import annotations

import json
import os
from hybrid_ai_trading.execution.blockg_errors import BlockGNotReady
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple


DEFAULT_STATUS_PATH = Path("logs") / "blockg_status_stub.json"


@dataclass(frozen=True)
class BlockGDecision:
    ready: bool
    reasons: List[str]
    path: str



def _load_status(path: Path) -> Dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
        return json.loads(raw)
    except Exception:
        return {}


def _status_path() -> Path:
    p = (os.environ.get("HAT_BLOCKG_STATUS_PATH") or "").strip()
    return Path(p) if p else DEFAULT_STATUS_PATH


def check_symbol_ready(symbol: str) -> BlockGDecision:
    sym = (symbol or "").upper().strip()
    path = _status_path()
    st = _load_status(path)

    # Fail-closed on missing/invalid JSON
    if not st:
        return BlockGDecision(False, [f"missing_or_invalid_contract:{path.as_posix()}"], str(path))

    key = f"{sym.lower()}_blockg_ready"
    ready = bool(st.get(key, False))
    reasons = list(st.get("reasons_not_ready") or [])

    # If the symbol is not ready but reasons list is empty, add deterministic reason
    if not ready and not reasons:
        reasons = [f"{key}=false"]

    return BlockGDecision(ready, reasons, str(path))


def require_blockg_ready(symbol: str, *, is_live: bool) -> None:
    """
    Enforce Block-G contract for live order path.
    Fail-closed: if live and contract says not ready -> raise RuntimeError.
    """
    if not is_live:
        return

    sym = (symbol or "").upper().strip()
    if sym not in {"NVDA", "SPY", "QQQ"}:
        return

    d = check_symbol_ready(sym)
    if not d.ready:
        msg = f"BLOCKG_NOT_READY sym={sym} path={d.path} reasons={';'.join(d.reasons)[:500]}"
        raise BlockGNotReady(msg)
def require_blockg_ready_for_live(symbol: str, *, status: dict | None = None) -> None:
    """
    Test + broker wrapper.

    - Live is determined by HAT_IS_PAPER=0.
    - If status is provided, use it (tests).
    - Fail-closed for unknown symbols.
    - Raises BlockGNotReady on failure.
    """
    sym = (symbol or "").upper().strip()
    if sym not in {"NVDA", "SPY", "QQQ"}:
        raise BlockGNotReady(f"Block-G not ready: unsupported_symbol={sym}")
    # If status is provided, always enforce it (tests + deterministic auditing), regardless of env.
    if status is not None:
        key = f"{sym.lower()}_blockg_ready"
        if bool(status.get(key, False)) is not True:
            reasons = status.get("reasons_not_ready") or [f"{key}=false"]
            # tests expect explicit key=false substring
            if all(str(x).lower() != f"{key}=false" for x in reasons):
                reasons = list(reasons) + [f"{key}=false"]
            raise BlockGNotReady(";".join([str(x) for x in reasons])[:500])
        return

    # Runtime path: only enforce when live
    is_live = str(os.environ.get("HAT_IS_PAPER", "")).strip() == "0"
    if not is_live:
        return

    require_blockg_ready(sym, is_live=True)