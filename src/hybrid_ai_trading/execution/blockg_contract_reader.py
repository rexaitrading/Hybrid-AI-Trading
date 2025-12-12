from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


# Repo root: .../src/hybrid_ai_trading/execution/blockg_contract_reader.py
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONTRACT_PATH = Path(
    os.environ.get("BLOCKG_CONTRACT_PATH", str(REPO_ROOT / "logs" / "blockg_status_stub.json"))
)


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
    """
    Load Block-G contract JSON.

    - BOM tolerant: decode with utf-8-sig (strips EF BB BF automatically)
    - Conservative: any read/parse failure returns None
    """
    try:
        if not path.exists():
            return None

        raw = path.read_bytes()
        if not raw:
            return None

        txt = raw.decode("utf-8-sig", errors="replace").strip()
        if not txt:
            return None

        obj = json.loads(txt)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def is_symbol_ready(symbol: str, contract_path: Path = DEFAULT_CONTRACT_PATH) -> BlockGDecision:
    sym = (symbol or "").strip().upper()
    obj = _load_contract(contract_path)

    if obj is None:
        return BlockGDecision(
            symbol=sym,
            ready=False,
            reason="BLOCKG_CONTRACT_MISSING_OR_UNREADABLE",
            contract_path=str(contract_path),
        )

    key = f"{sym.lower()}_blockg_ready"
    v = obj.get(key)

    if isinstance(v, bool):
        return BlockGDecision(
            symbol=sym,
            ready=v,
            reason=("BLOCKG_READY" if v else "BLOCKG_NOT_READY"),
            contract_path=str(contract_path),
        )

    return BlockGDecision(
        symbol=sym,
        ready=False,
        reason=f"BLOCKG_FIELD_MISSING:{key}",
        contract_path=str(contract_path),
    )


def assert_symbol_ready(symbol: str, contract_path: Path = DEFAULT_CONTRACT_PATH) -> None:
    d = is_symbol_ready(symbol, contract_path=contract_path)
    if not d.ready:
        raise RuntimeError(f"[BLOCK-G] {d.symbol} NOT READY: {d.reason} (contract={d.contract_path})")