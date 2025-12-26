from __future__ import annotations

import re
from pathlib import Path

# Baseline regression guard:
# The ONLY files allowed to contain direct `ib.placeOrder(` are:
#   - broker/ib_safe.py (the chokepoint)
#   - execution/paper_order.py (paper simulation)
ALLOWED_FILES = {
    "src/hybrid_ai_trading/broker/ib_safe.py",
    "src/hybrid_ai_trading/execution/paper_order.py",
}


def _strip_docstrings_and_comments(txt: str) -> str:
    # Remove triple-quoted blocks (best-effort) and line comments
    txt = re.sub(r"(?s)'''(.*?)'''", "", txt)
    txt = re.sub(r'(?s)\"\"\"(.*?)\"\"\"', "", txt)
    txt = re.sub(r"(?m)#.*$", "", txt)
    return txt


def test_no_new_direct_ib_placeorder_call_sites():
    root = Path("src/hybrid_ai_trading")
    offenders: list[str] = []

    for p in root.rglob("*.py"):
        txt = p.read_text(encoding="utf-8-sig")
        txt = _strip_docstrings_and_comments(txt)

        if "ib.placeOrder(" not in txt:
            continue

        rel = str(p).replace("\\", "/")
        if rel not in ALLOWED_FILES:
            offenders.append(rel)

    assert not offenders, (
        "New direct ib.placeOrder call sites detected (must route via IB chokepoint): "
        + ", ".join(sorted(offenders))
    )
