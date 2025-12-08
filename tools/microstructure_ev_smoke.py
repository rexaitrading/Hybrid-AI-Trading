"""
Microstructure + EV/GateScore smoke.

- Ensures hybrid_ai_trading.microstructure and gatescore modules import.
- Prints basic information only. No trading, no config changes.
"""

from __future__ import annotations

import importlib
import sys

modules = [
    "hybrid_ai_trading.microstructure",
    "hybrid_ai_trading.gatescore",
    "hybrid_ai_trading.gatescore_bar",
]

print("[MICROSTRUCTURE] Microstructure + EV/GateScore smoke start")

for name in modules:
    try:
        mod = importlib.import_module(name)
        print(f"[MICROSTRUCTURE] Imported {name!r} OK (module = {mod})")
    except Exception as exc:
        print(f"[MICROSTRUCTURE] WARNING: failed to import {name!r}: {exc!r}")

print("[MICROSTRUCTURE] Microstructure smoke complete")