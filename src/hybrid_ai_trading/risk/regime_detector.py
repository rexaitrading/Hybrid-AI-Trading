from __future__ import annotations

import logging
from datetime import timedelta
from typing import Dict, List, Optional, Union

import pandas as pd

from hybrid_ai_trading.utils.time_utils import utc_now

try:
    from hybrid_ai_trading.config.settings import CONFIG  # type: ignore
except Exception:
    CONFIG = {}
try:
    from hybrid_ai_trading.data.store.database import (  # type: ignore
        Price,
        SessionLocal,
    )
except Exception:
    Price = None
    SessionLocal = None

logger = logging.getLogger("hybrid_ai_trading.risk.regime_detector")


class RegimeDetector:
    def __init__(
        self,
        enabled: Optional[bool] = None,
        method: Optional[str] = None,
        lookback_days: Optional[int] = None,
        bull_threshold: Optional[float] = None,
        bear_threshold: Optional[float] = None,
        crisis_volatility: Optional[float] = None,
        min_samples: Optional[int] = None,
        neutral_tolerance: float = 1e-4,
    ) -> None:
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
        self.history: Dict[str, List[str]] = {}
        logger.info(
            " RegimeDetector | enabled=%s method=%s lookback=%dd bull>%s bear<%s crisis_vol=%s min_samples=%s",
            self.enabled,
            self.method,
            self.lookback_days,
            f"{self.bull_threshold:.2%}",
            f"{self.bear_threshold:.2%}",
            f"{self.crisis_volatility:.2%}",
            self.min_samples,
        )

    def _get_prices(self, symbol: str, prices: Optional[List[float]] = None) -> pd.Series:
        if prices is not None:
            try:
                return pd.Series([float(p) for p in prices], dtype="float64").dropna()
            except Exception as e:
                logger.error("Bad price data for %s: %s", symbol, e)
                return pd.Series(dtype="float64")
        if SessionLocal is None or Price is None:
            return pd.Series(dtype="float64")
        since = utc_now() - timedelta(days=self.lookback_days)
        session = SessionLocal()
        try:
            rows = (
                session.query(Price)
                .filter(Price.symbol == symbol, Price.timestamp >= since)
                .order_by(Price.timestamp.asc())
                .all()
            )
            closes = [float(r.close) for r in rows if getattr(r, "close", None) is not None]
            return pd.Series(closes, dtype="float64").dropna()
        except Exception as e:
            logger.error("DB fetch failed for %s: %s", symbol, e)
            return pd.Series(dtype="float64")
        finally:
            try:
                session.close()
            except Exception:
                pass

    def detect(self, symbol: str, prices: Optional[List[float]] = None) -> str:
        if not self.enabled:
            return "neutral"
        closes = self._get_prices(symbol, prices)
        if closes.empty:
            logger.warning("No data for %s  returning neutral", symbol)
            return "neutral"
        if len(closes) < self.min_samples:
            logger.warning(
                "Insufficient data for %s: have %d, need  %d  returning neutral",
                symbol,
                len(closes),
                self.min_samples,
            )
            return "neutral"
        rets = closes.pct_change().dropna()
        if rets.empty:
            logger.warning("Empty returns for %s  returning sideways", symbol)
            return "sideways"
        try:
            avg_return = float(rets.mean())
            vol = float(rets.std())
        except Exception as e:
            logger.error("Return stats failed for %s: %s  returning neutral", symbol, e)
            return "neutral"
        if rets.abs().sum() < self.neutral_tolerance:
            regime = "sideways"
        elif vol >= self.crisis_volatility:
            regime = "crisis"
        elif avg_return >= self.bull_threshold:
            regime = "bull"
        elif avg_return <= self.bear_threshold:
            regime = "bear"
        else:
            regime = "transition"
        self.history.setdefault(symbol, []).append(regime)
        logger.info(
            " Regime %s | regime=%s avg=%.4f vol=%.4f n=%d",
            symbol,
            regime,
            avg_return,
            vol,
            len(rets),
        )
        return regime

    def detect_with_metrics(
        self, symbol: str, prices: Optional[List[float]] = None
    ) -> Dict[str, Union[str, float, int]]:
        closes = self._get_prices(symbol, prices)
        if closes.empty:
            return {"symbol": symbol, "regime": "neutral", "reason": "no_data"}
        rets = closes.pct_change().dropna()
        if rets.empty:
            return {"symbol": symbol, "regime": "sideways", "reason": "flat"}
        try:
            avg_return = float(rets.mean())
            vol = float(rets.std())
        except Exception:
            return {"symbol": symbol, "regime": "neutral", "reason": "bad_data"}
        regime = self.detect(symbol, prices)
        return {
            "symbol": symbol,
            "regime": regime,
            "avg_return": avg_return,
            "volatility": vol,
            "n_samples": int(len(rets)),
        }

    def confidence(self, symbol: str, prices: Optional[List[float]] = None) -> float:
        if not self.enabled:
            return 0.0
        mapping = {"bull": 0.9, "bear": 0.1, "crisis": 0.3, "transition": 0.5, "sideways": 0.5}
        return mapping.get(self.detect(symbol, prices), 0.5)

    def reset(self) -> None:
        logger.info(" Resetting regime history")
        self.history.clear()
