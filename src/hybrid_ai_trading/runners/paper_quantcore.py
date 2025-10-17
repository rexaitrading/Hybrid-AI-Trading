# -*- coding: utf-8 -*-
"""
Quant-core shim for simulation and testing only.
Connects RiskManager, KellySizer, RegimeDetector, SentimentFilter, etc.
Safe-imports with fallbacks if modules are not present yet.
"""
from __future__ import annotations
import time
from typing import Dict, List, Any

try:
    from hybrid_ai_trading.risk.risk_manager import RiskManager
except Exception:
    class RiskManager:
        def __init__(self, *a, **k): pass
        def approve_trade(self, market_data): return {"approved": True, "reason": "stub"}

try:
    from hybrid_ai_trading.sizing.kelly_sizer import KellySizer
except Exception:
    class KellySizer:
        def __init__(self, *a, **k): pass
        def size(self, market_data): return {"f": 0.05, "qty": 1, "reason": "stub"}

try:
    from hybrid_ai_trading.regime.regime_detector import RegimeDetector
except Exception:
    class RegimeDetector:
        def __init__(self, *a, **k): pass
        def detect(self, market_data): return {"regime": "neutral", "confidence": 0.5, "reason": "stub"}

try:
    from hybrid_ai_trading.sentiment.sentiment_filter import SentimentFilter
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
    import inspect
    regime = self.regime.detect(market_data)
    sentiment = self.sentiment.score(market_data)
    sizing = self.sizer.size(market_data)
    # derive qty & notional robustly
    try:
        qty = float((sizing or {}).get("qty") or market_data.get("qty") or 0.0)
    except Exception:
        qty = 0.0
    try:
        price = float(market_data.get("price") or market_data.get("last") or market_data.get("close") or market_data.get("vwap") or 0.0)
    except Exception:
        price = 0.0
    notional = qty * price

    approval = {"approved": True, "reason": "stub"}
    ap = getattr(self.risk, "approve_trade", None)
    if callable(ap):
        try:
            sig = inspect.signature(ap)
            params = [p.name for p in sig.parameters.values()][1:]  # drop self
            # prefer side/qty/notional if available
            if {"side","qty","notional"}.issubset(set(params)) or len(params) >= 3:
                approval = ap("BUY", qty, notional)
            else:
                approval = ap(market_data)
        except TypeError:
            # alternate call if the first style didn't match
            try:
                approval = ap(market_data)
            except Exception as e2:
                approval = {"approved": False, "reason": f"risk_call_failed: {e2}"}
        except Exception as e:
            approval = {"approved": False, "reason": f"risk_call_failed: {e}"}
    else:
        approval = {"approved": False, "reason": "risk_method_missing"}

    return {
        "regime": regime,
        "sentiment": sentiment,
        "kelly_size": sizing,
        "risk_approved": approval,
    }def run_once(cfg: dict, logger, snapshots: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    """
    Evaluate one pass on provided market snapshots.
    snapshots: list of {symbol, price, bid, ask, last, close, vwap, volume, ts}
    If None, we fall back to a single dummy sample.
    """
    qc = QuantCore(cfg)
    decisions: List[Dict[str, Any]] = []
    data = snapshots or [{"symbol": "AAPL", "price": 246.9, "vol": 0.03}]
    for md in data:
        md2 = dict(md)
        if "price" not in md2 or md2.get("price") is None:
            md2["price"] = md2.get("last") or md2.get("close") or md2.get("vwap")
        d = qc.evaluate(md2)
        logger.info("quantcore_eval", symbol=md2.get("symbol"), decision=d)
        decisions.append({"symbol": md2.get("symbol"), **d})
    return {"decisions": decisions}