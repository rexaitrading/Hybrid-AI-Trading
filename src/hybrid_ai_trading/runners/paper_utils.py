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
