# -*- coding: utf-8 -*-
"""
Quant-core shim for simulation and testing only.
Connects RiskManager, KellySizer, RegimeDetector, SentimentFilter, etc.
Safe-imports with fallbacks if modules are not present yet.
"""
from __future__ import annotations
import time

# --- Safe imports with stubs -------------------------------------------------
try:
    from hybrid_ai_trading.risk_manager import RiskManager
except Exception:
    class RiskManager:
        def __init__(self, *a, **k): pass
        def approve_trade(self, market_data): return {"approved": True, "reason": "stub"}

try:
    from hybrid_ai_trading.kelly_sizer import KellySizer
except Exception:
    class KellySizer:
        def __init__(self, *a, **k): pass
        def size(self, market_data): return {"f": 0.05, "qty": 1, "reason": "stub"}

try:
    from hybrid_ai_trading.regime_detector import RegimeDetector
except Exception:
    class RegimeDetector:
        def __init__(self, *a, **k): pass
        def detect(self, market_data): return {"regime": "neutral", "confidence": 0.5, "reason": "stub"}

try:
    from hybrid_ai_trading.sentiment_filter import SentimentFilter
except Exception:
    class SentimentFilter:
        def __init__(self, *a, **k): pass
        def score(self, market_data): return {"sentiment": 0.0, "confidence": 0.5, "reason": "stub"}

class QuantCore:
    """Lightweight orchestrator for research / paper-mode."""
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.risk = RiskManager(cfg.get("risk", {}))
        self.sizer = KellySizer(cfg.get("kelly", {}))
        self.regime = RegimeDetector(cfg.get("regime", {}))
        self.sentiment = SentimentFilter(cfg.get("sentiment", {}))

    def evaluate(self, market_data: dict) -> dict:
        regime = self.regime.detect(market_data)
        sentiment = self.sentiment.score(market_data)
        sizing = self.sizer.size(market_data)
        approval = self.risk.approve_trade(market_data)
        return {
            "regime": regime,
            "sentiment": sentiment,
            "kelly_size": sizing,
            "risk_approved": approval,
        }

def run_once(cfg: dict, logger, snapshots=None):\n    \"\"\"Evaluate one pass on provided market snapshots.\n    snapshots: list of {symbol, price, bid, ask, last, close, vwap, volume, ts}\n    If None, we fall back to a single dummy sample.\n    \"\"\"\n    qc = QuantCore(cfg)\n    decisions = []\n    data = snapshots or [{\"symbol\": \"AAPL\", \"price\": 246.9, \"vol\": 0.03}]\n    for md in data:\n        md2 = {**md}\n        if \"price\" not in md2:\n            # pick best available price field\n            md2[\"price\"] = md2.get(\"last\") or md2.get(\"close\") or md2.get(\"vwap\")\n        d = qc.evaluate(md2)\n        logger.info(\"quantcore_eval\", symbol=md2.get(\"symbol\"), decision=d)\n        decisions.append({\"symbol\": md2.get(\"symbol\"), **d})\n    return {\"decisions\": decisions}
