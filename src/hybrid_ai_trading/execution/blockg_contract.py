from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict


class BlockGNotReady(RuntimeError):
    pass


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def is_paper() -> bool:
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
        return json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return {"nvda_blockg_ready": False, "reasons_not_ready": ["blockg_status_unreadable"]}


def assert_nvda_live_ready() -> None:
    if is_paper():
        return
    st = read_blockg_status()
    if not bool(st.get("nvda_blockg_ready", False)):
        reasons = st.get("reasons_not_ready", [])
        raise BlockGNotReady(f"BLOCK-G DENY (live): nvda_blockg_ready!=True reasons={reasons}")
