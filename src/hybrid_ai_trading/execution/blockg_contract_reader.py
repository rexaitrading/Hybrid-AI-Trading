from __future__ import annotations

import json
from hybrid_ai_trading.execution.blockg_guard import _contract_path
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_CONTRACT = REPO_ROOT / "logs" / "blockg_status_stub.json"

def default_contract_path() -> Path:
    """
    Single source of truth for contract path resolution.
    Delegates to blockg_guard._contract_path(), which is alias-aware:
      - HAT_BLOCKG_CONTRACT_PATH (canonical)
      - BLOCKG_CONTRACT_PATH (alias)
      - logs/blockg_status_stub.json (default)
    """
    return _contract_path()

@dataclass(frozen=True)
class BlockGDecision:
    symbol: str
    ready: bool
    reason: str
    contract_path: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "ready": self.ready,
            "reason": self.reason,
            "contract_path": self.contract_path,
        }


def _load_contract(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if not path.exists():
            return None
        txt = path.read_text(encoding="utf-8", errors="replace").strip()
        if not txt:
            return None
        obj = json.loads(txt)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def is_symbol_ready(symbol: str, contract_path: Optional[Path] = None) -> BlockGDecision:
    sym = (symbol or "").strip().upper()
    cp = contract_path or default_contract_path()
    obj = _load_contract(cp)
    # Conservative default: if we cannot read contract -> BLOCK
    if obj is None:
        return BlockGDecision(
            symbol=sym,
            ready=False,
            reason="BLOCKG_CONTRACT_MISSING_OR_UNREADABLE",
            contract_path=str(cp.as_posix()),
        )

    key = f"{sym.lower()}_blockg_ready"
    v = obj.get(key, None)

    if isinstance(v, bool):
        return BlockGDecision(symbol=sym, ready=v, reason=("BLOCKG_READY" if v else "BLOCKG_NOT_READY"), contract_path=str(cp.as_posix()))

    # Missing field -> BLOCK
    return BlockGDecision(
        symbol=sym,
        ready=False,
        reason=f"BLOCKG_FIELD_MISSING:{key}",
        contract_path=str(cp.as_posix()),
    )


def assert_symbol_ready(symbol: str, contract_path: Optional[Path] = None) -> None:
    d = is_symbol_ready(symbol, contract_path=contract_path)
    if not d.ready:
        raise RuntimeError(f"[BLOCK-G] {d.symbol} NOT READY: {d.reason} (contract={d.contract_path})")