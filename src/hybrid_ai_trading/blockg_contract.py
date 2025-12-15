from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class BlockGDecision:
    as_of_date: str
    symbol: str
    ready: bool
    reason: str


def _safe_bool(x: Any) -> bool:
    return bool(x) is True


def load_blockg_status(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def require_blockg_ready(
    symbol: str,
    status_path: Optional[str] = None,
) -> BlockGDecision:
    """
    Fail-closed readiness check.

    - Reads logs/blockg_status_stub.json (or provided path)
    - Requires per-symbol readiness flag (nvda_blockg_ready, spy_blockg_ready, qqq_blockg_ready)
    """
    sym = (symbol or "").strip().upper()
    if not sym:
        return BlockGDecision(as_of_date="", symbol="", ready=False, reason="symbol_empty")

    default_path = Path("logs") / "blockg_status_stub.json"
    p = Path(status_path) if status_path else default_path

    j = load_blockg_status(p)
    as_of = str(j.get("as_of_date", ""))

    key = f"{sym.lower()}_blockg_ready"
    ready_val = _safe_bool(j.get(key, False))

    if not ready_val:
        return BlockGDecision(as_of_date=as_of, symbol=sym, ready=False, reason=f"blockg_not_ready:{key}")

    return BlockGDecision(as_of_date=as_of, symbol=sym, ready=True, reason="ok")
