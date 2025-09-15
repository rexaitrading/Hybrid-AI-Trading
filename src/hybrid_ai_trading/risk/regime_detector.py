"""
Regime Detector (Hybrid AI Quant Pro v10.1 – Polished & Testable)
-----------------------------------------------------------------
- Detects regimes via DB (production) or price series (tests)
- Tracks per-symbol history
- Supports reset() for clearing state
- Confidence scores aligned with GateScore + tests
- Polished logging, explicit all-equal handling, and safer DB branch
"""

import logging
import pandas as pd
from datetime import datetime, timedelta

from hybrid_ai_trading.data.store.database import SessionLocal, Price
from hybrid_ai_trading.config.settings import CONFIG

logger = logging.getLogger(__name__)


class RegimeDetector:
    def __init__(
        self,
        enabled: bool = None,
        method: str = None,
        lookback_days: int = None,
        bull_threshold: float = None,
        bear_threshold: float = None,
        crisis_volatility: float = None,
        min_samples: int = None,
        neutral_tolerance: float = 1e-4,
    ):
        cfg = CONFIG.get("regime", {})

        self.enabled = enabled if enabled is not None else cfg.get("enabled", True)
        self.method = method or cfg.get("method", "hybrid")
        self.lookback_days = lookback_days or cfg.get("lookback_days", 90)
        self.bull_threshold = bull_threshold or cfg.get("bull_threshold", 0.02)
        self.bear_threshold = bear_threshold or cfg.get("bear_threshold", -0.02)
        self.crisis_volatility = crisis_volatility or cfg.get("crisis_volatility", 0.03)
        self.min_samples = (
            min_samples
            if min_samples is not None
            else cfg.get("min_samples", int(self.lookback_days * 0.7))
        )
        self.neutral_tolerance = neutral_tolerance
        self.history: dict[str, list[str]] = {}

        logger.info(
            "✅ RegimeDetector initialized | enabled=%s | method=%s | lookback=%dd | "
            "bull>%s | bear<%s | crisis_vol>%s | min_samples=%s",
            self.enabled,
            self.method,
            self.lookback_days,
            f"{self.bull_threshold:.2%}",
            f"{self.bear_threshold:.2%}",
            f"{self.crisis_volatility:.2%}",
            self.min_samples,
        )

    # ------------------------------------------------------------------
    def detect(self, symbol: str, prices=None) -> str:
        """Detect market regime from DB or provided price list."""
        if not self.enabled:
            logger.debug("Regime detection disabled → neutral")
            return "neutral"

        # --- Use provided prices (tests) ---
        if prices is not None:
            closes = pd.Series(prices, dtype="float64").dropna()
        else:
            # --- Production DB fetch ---
            since = datetime.utcnow() - timedelta(days=self.lookback_days)
            session = SessionLocal()
            try:
                rows = (
                    session.query(Price)
                    .filter(Price.symbol == symbol, Price.timestamp >= since)
                    .order_by(Price.timestamp.asc())
                    .all()
                )
            except Exception as e:
                logger.error("❌ RegimeDetector DB error for %s: %s", symbol, e)
                return "neutral"
            finally:
                session.close()
            closes = pd.Series([r.close for r in rows], dtype="float64")

        # --- Data sufficiency check ---
        if len(closes) < self.min_samples:
            logger.warning(
                "⚠️ Insufficient data for %s: have %d, need ≥ %d",
                symbol, len(closes), self.min_samples
            )
            return "sideways"

        rets = closes.pct_change().dropna()
        if rets.empty:
            logger.info("ℹ️ No returns data for %s → sideways", symbol)
            return "sideways"

        avg_return = rets.mean()
        vol = rets.std()

        logger.debug(
            "📊 Regime calc for %s | avg_return=%.4f, vol=%.4f, n=%d",
            symbol, avg_return, vol, len(rets)
        )

        # --- All equal fallback ---
        if rets.abs().sum() < self.neutral_tolerance:
            logger.info("ℹ️ All-equal or flat prices for %s → sideways", symbol)
            regime = "sideways"
        # --- Crisis regime ---
        elif vol >= self.crisis_volatility:
            logger.warning("🚨 Crisis regime for %s | vol=%.3f", symbol, vol)
            regime = "crisis"
        elif avg_return >= self.bull_threshold:
            regime = "bull"
        elif avg_return <= self.bear_threshold:
            regime = "bear"
        else:
            regime = "sideways"

        # --- Track history ---
        self.history.setdefault(symbol, []).append(regime)
        return regime

    # ------------------------------------------------------------------
    def confidence(self, symbol: str, prices=None) -> float:
        """Return confidence score aligned with test expectations."""
        if not self.enabled:
            return 0.0
        regime = self.detect(symbol, prices=prices)
        if regime == "bull":
            return 0.9
        if regime == "bear":
            return 0.1
        if regime == "crisis":
            return 0.5
        return 0.5

    # ------------------------------------------------------------------
    def reset(self):
        """Clear internal history."""
        logger.info("🔄 Resetting regime history")
        self.history.clear()
