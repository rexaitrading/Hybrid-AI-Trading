from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass
class Decision:
    symbol: str
    setup: str  # e.g., "ORB_Break", "OD_VWAP_Reclaim", "Pullback_1R"
    side: str  # "long" | "short"
    entry_px: float
    stop_px: float
    target_px: float
    qty: int
    kelly_f: float  # raw kelly before caps
    regime: str
    regime_conf: float
    sentiment: float
    sent_conf: float
    price: Optional[float] = None  # microstructure enrich
    bid: Optional[float] = None
    ask: Optional[float] = None
    bidSize: Optional[float] = None
    askSize: Optional[float] = None
    volume: Optional[float] = None
    risk_approved: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None  # freeform reason code

    def to_item(self) -> Dict[str, Any]:
        d = asdict(self)
        # pack into the runner item shape: {"symbol": ..., "decision": {...}}
        sym = d.pop("symbol")
        return {"symbol": sym, "decision": d}
