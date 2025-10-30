from __future__ import annotations

import json
import os
import time
from typing import Any, Dict

STATE = os.path.join("logs", "session_state.json")


def _read_state() -> Dict[str, Any]:
    if os.path.exists(STATE):
        try:
            with open(STATE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _write_state(d: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(d, f)


def init_baseline(equity_with_loan: float, loss_cap_frac: float) -> Dict[str, Any]:
    st = _read_state()
    if "baseline_ewl" not in st:
        st["baseline_ewl"] = float(equity_with_loan)
        st["loss_cap_frac"] = float(loss_cap_frac)
        st["t0"] = int(time.time())
        _write_state(st)
    return st


def should_halt(current_ewl: float, loss_cap_frac: float | None = None) -> bool:
    st = _read_state()
    base = st.get("baseline_ewl")
    cap = float(
        loss_cap_frac if loss_cap_frac is not None else st.get("loss_cap_frac", 0.01)
    )
    if base is None:
        init_baseline(current_ewl, cap)
        return False
    return float(current_ewl) <= float(base) * (1.0 - cap)
