# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional

from ib_insync import IB


def apply_mdt(ib: IB, mdt: Optional[int]):
    """Set IB market data type safely (1 live, 2 frozen, 3 delayed, 4 delayed-frozen)."""
    try:
        if mdt:
            ib.reqMarketDataType(int(mdt))
    except Exception:
        pass

def safe_float(val, default=0.0):
    """
    Safely convert val to float.

    Accepts strings, numbers, or None.
    Returns default (0.0 by default) on any exception.
    """
    try:
        return float(val)
    except Exception:
        return float(default)
