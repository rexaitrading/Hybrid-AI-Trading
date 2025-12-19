from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass(frozen=True)
class BlockGContract:
    as_of_date: str
    nvda_blockg_ready: bool
    gatescore_ok_today: bool
    phase4_ok_today: bool
    phase23_health_ok_today: bool
    ev_hard_daily_ok_today: bool


def _fail_closed() -> BlockGContract:
    return BlockGContract(
        as_of_date="",
        nvda_blockg_ready=False,
        gatescore_ok_today=False,
        phase4_ok_today=False,
        phase23_health_ok_today=False,
        ev_hard_daily_ok_today=False,
    )


def load_blockg_contract(path: Path) -> BlockGContract:
    if not path.exists():
        return _fail_closed()

    try:
        raw = path.read_text(encoding="utf-8")
        data: Dict[str, Any] = json.loads(raw)
    except Exception:
        return _fail_closed()

    def b(key: str) -> bool:
        return bool(data.get(key, False))

    return BlockGContract(
        as_of_date=str(data.get("as_of_date", "")),
        nvda_blockg_ready=b("nvda_blockg_ready"),
        gatescore_ok_today=b("gatescore_ok_today"),
        phase4_ok_today=b("phase4_ok_today"),
        phase23_health_ok_today=b("phase23_health_ok_today"),
        ev_hard_daily_ok_today=b("ev_hard_daily_ok_today"),
    )


def require_nvda_blockg_ready(repo_root: Path) -> BlockGContract:
    """
    Fail-closed enforcement: raises if NVDA is not Block-G ready.
    """
    contract_path = repo_root / "logs" / "blockg_status_stub.json"
    c = load_blockg_contract(contract_path)
    if not c.nvda_blockg_ready:
        raise RuntimeError(
            "BLOCK-G FAIL-CLOSED: NVDA not ready. "
            f"as_of_date={c.as_of_date} "
            f"phase4={c.phase4_ok_today} phase23={c.phase23_health_ok_today} "
            f"ev_hard={c.ev_hard_daily_ok_today} gatescore={c.gatescore_ok_today}"
        )
    return c