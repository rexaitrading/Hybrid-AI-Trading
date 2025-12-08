"""
Phase-2 microstructure feature probe.

Goal:
- Discover candidate functions / classes in:
    - hybrid_ai_trading.microstructure
    - hybrid_ai_trading.gatescore_bar

We are specifically looking for:
- range / volatility style metrics (ms_range_pct)
- trend / momentum style flags (ms_trend_flag)

NO trading, NO config writes. Print-only diagnostics.
"""

from __future__ import annotations

import importlib
import inspect
import sys
from types import ModuleType
from typing import Iterable, Tuple


MODULES = [
    "hybrid_ai_trading.microstructure",
    "hybrid_ai_trading.gatescore_bar",
]


KEYWORDS_RANGE = ["range", "atr", "vol", "volatility"]
KEYWORDS_TREND = ["trend", "momentum", "slope", "dir", "direction"]
KEYWORDS_ALL = KEYWORDS_RANGE + KEYWORDS_TREND


def iter_callables(mod: ModuleType) -> Iterable[Tuple[str, object]]:
    for name, obj in vars(mod).items():
        if not callable(obj):
            continue
        if name.startswith("_"):
            continue
        yield name, obj


def first_line_doc(obj: object) -> str:
    try:
        doc = inspect.getdoc(obj) or ""
    except Exception:
        return ""
    if not doc:
        return ""
    return doc.splitlines()[0].strip()


def classify_name(name: str) -> str:
    lname = name.lower()
    hits_range = any(k in lname for k in KEYWORDS_RANGE)
    hits_trend = any(k in lname for k in KEYWORDS_TREND)
    if hits_range and hits_trend:
        return "range+trend"
    if hits_range:
        return "range"
    if hits_trend:
        return "trend"
    return ""


def probe_module(mod_name: str) -> None:
    print(f"\n[PROBE] Module: {mod_name}")
    try:
        mod = importlib.import_module(mod_name)
    except Exception as exc:
        print(f"[PROBE] WARNING: failed to import {mod_name!r}: {exc!r}")
        return

    range_candidates = []
    trend_candidates = []
    other_candidates = []

    for name, obj in iter_callables(mod):
        cls = classify_name(name)
        if not cls:
            # Optionally surface a few short names that might be interesting
            if any(k in name.lower() for k in ["ev", "bar", "feature", "snap"]):
                cls = "other"
            else:
                continue

        try:
            sig = str(inspect.signature(obj))
        except Exception:
            sig = "(...)"

        doc = first_line_doc(obj)

        record = (name, sig, cls, doc)

        if cls == "range":
            range_candidates.append(record)
        elif cls == "trend":
            trend_candidates.append(record)
        elif cls == "range+trend":
            range_candidates.append(record)
            trend_candidates.append(record)
        else:
            other_candidates.append(record)

    if not (range_candidates or trend_candidates or other_candidates):
        print("[PROBE] No matching callables found with current heuristics.")
        return

    def dump(title: str, items: Iterable[Tuple[str, str, str, str]]) -> None:
        items = list(items)
        if not items:
            return
        print(f"\n[PROBE] {title} (count={len(items)})")
        for name, sig, cls, doc in items:
            summary = f"{name}{sig}"
            if doc:
                summary += f"  # {doc}"
            print("   ", summary)

    dump("Range / volatility candidates", range_candidates)
    dump("Trend / momentum candidates", trend_candidates)
    dump("Other EV/microstructure candidates", other_candidates)


def main() -> None:
    print("[MICROSTRUCTURE-PROBE] Microstructure + EV/GateScore feature probe start")
    for mod_name in MODULES:
        probe_module(mod_name)
    print("\n[MICROSTRUCTURE-PROBE] Feature probe complete")


if __name__ == "__main__":
    main()