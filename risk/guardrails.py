from __future__ import annotations

from datetime import datetime, time
from typing import Any, Dict, Tuple

import pytz

PT = pytz.timezone("America/Vancouver")


def _now_pt() -> datetime:
    return datetime.now(PT)


def in_trading_window(start_hm=("06", "00"), end_hm=("11", "00")) -> bool:
    now = _now_pt().timetz()
    sh, sm = map(int, start_hm)
    eh, em = map(int, end_hm)
    return time(sh, sm) <= now <= time(eh, em)


def margin_usage_ok(
    preview: Dict[str, Any], max_frac: float = 0.20
) -> Tuple[bool, str]:
    ewl = preview.get("equityWithLoan")
    init_total = preview.get("initMargin_total")
    if ewl is None:
        return False, "No equityWithLoan in preview"
    if init_total is None:
        # attempt per-unit * qty reconstruction
        pu = preview.get("initMargin_perUnit")
        qty = preview.get("qty", 1)
        if pu is not None:
            init_total = pu * max(qty, 1)
    if init_total is None or init_total <= 0:
        return False, "No usable initMargin in preview"
    frac = init_total / float(ewl)
    return (frac <= max_frac, f"margin_usage={frac:.3%} (limit {max_frac:.0%})")


def qty_ok(qty: int, max_qty: int = 1000) -> Tuple[bool, str]:
    return (0 < qty <= max_qty, f"qty={qty} (max {max_qty})")


def guardrails(
    preview: Dict[str, Any],
    max_margin_frac: float = 0.20,
    max_qty: int = 1000,
    start=("06", "00"),
    end=("11", "00"),
) -> Tuple[bool, str]:
    ok_qty, m_qty = qty_ok(preview.get("qty", 1), max_qty)
    if not ok_qty:
        return False, m_qty
    ok_mu, m_mu = margin_usage_ok(preview, max_margin_frac)
    if not ok_mu:
        return False, m_mu
    if not in_trading_window(start, end):
        return (
            False,
            f"outside trading window PT {start[0]}:{start[1]}â€“{end[0]}:{end[1]}",
        )
    return True, "guardrails: PASS"
