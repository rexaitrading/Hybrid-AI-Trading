from __future__ import annotations

from pathlib import Path

import pytest


def test_no_direct_ib_placeorder_outside_ib_safe():
    root = Path(__file__).resolve().parents[1] / "src" / "hybrid_ai_trading"
    offenders = []

    for p in root.rglob("*.py"):
        txt = p.read_text(encoding="utf-8", errors="replace")
        if ".placeOrder(" in txt:
            # Only allowed inside the chokepoint module
            if p.as_posix().endswith("/broker/ib_safe.py"):
                continue
            offenders.append(str(p))

    assert offenders == [], "Direct IB placeOrder bypass found:\n" + "\n".join(offenders)
