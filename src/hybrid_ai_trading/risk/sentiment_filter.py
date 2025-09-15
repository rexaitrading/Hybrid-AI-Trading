"""
Sentiment Filter (Hybrid AI Quant Pro v14.6 – Final Stable, AAA Grade)
----------------------------------------------------------------------
- Supports VADER (default) and FinBERT sentiment scoring
- Threshold priority: threshold → neutral zone → bias
- Rolling smoothing (history-based averaging)
- Defensive guards for missing/malformed analyzers
- Safe fallbacks when vader/transformers not installed
"""

import logging

logger = logging.getLogger(__name__)

# Safe optional imports
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except ImportError:
    SentimentIntensityAnalyzer = None
    logger.warning("⚠️ vaderSentiment not installed → VADER unavailable")

try:
    from transformers import pipeline
except ImportError:
    pipeline = None
    logger.warning("⚠️ transformers not installed → FinBERT unavailable")


class SentimentFilter:
    def __init__(
        self,
        enabled: bool = True,
        threshold: float = 0.8,
        neutral_zone: float = 0.2,
        bias: str = "none",
        model: str = "vader",
        smoothing: int = 1,
    ):
        self.enabled = enabled
        self.threshold = threshold
        self.neutral_zone = neutral_zone
        self.bias = bias
        self.model = model
        self.smoothing = max(1, smoothing)
        self.history = []

        if not enabled:
            self.analyzer = None
            return

        # --- Safe model selection ---
        if model == "vader" and SentimentIntensityAnalyzer:
            self.analyzer = SentimentIntensityAnalyzer()
        elif model == "finbert" and pipeline:
            try:
                self.analyzer = pipeline("sentiment-analysis", model="ProsusAI/finbert")
            except Exception as e:
                self.analyzer = None
                logger.warning(f"⚠️ SentimentFilter fallback: FinBERT unavailable → {e}")
        elif model not in ("vader", "finbert"):
            raise ValueError(f"Unknown model: {model}")
        else:
            self.analyzer = None
            logger.warning(f"⚠️ SentimentFilter fallback: model={model} unavailable")

        logger.info(
            f"✅ SentimentFilter initialized | model={self.model} | "
            f"threshold={self.threshold} | neutral_zone={self.neutral_zone} | "
            f"bias={self.bias} | smoothing={self.smoothing}"
        )

    # ------------------------------------------------------------------
    def score(self, text: str) -> float:
        """Return sentiment score ∈ [0,1]."""
        if not self.enabled:
            return 0.5
        if self.analyzer is None:
            logger.debug("ℹ️ Analyzer=None → default neutral 0.5")
            return 0.5

        try:
            if self.model == "vader":
                if not hasattr(self.analyzer, "polarity_scores"):
                    logger.error("❌ VADER analyzer missing polarity_scores → 0.0")
                    return 0.0
                result = self.analyzer.polarity_scores(text)
                if not isinstance(result, dict) or "compound" not in result:
                    logger.error("❌ Invalid VADER output → 0.0")
                    return 0.0
                compound = result["compound"]
                normalized = (compound + 1) / 2
            elif self.model == "finbert":
                if not callable(self.analyzer):
                    logger.error("❌ FinBERT analyzer not callable → 0.0")
                    return 0.0
                result = self.analyzer(text)
                if not isinstance(result, list) or not result:
                    logger.error("❌ FinBERT output not list → 0.0")
                    return 0.0
                res = result[0]
                if not isinstance(res, dict) or "label" not in res or "score" not in res:
                    logger.error("❌ Malformed FinBERT dict → 0.0")
                    return 0.0
                label, sc = res["label"].lower(), res["score"]
                if label == "positive":
                    normalized = sc
                elif label == "negative":
                    normalized = 1 - sc
                else:
                    normalized = 0.5
            else:
                return 0.5
        except Exception as e:
            logger.error(f"❌ Sentiment scoring failed: {e}")
            return 0.0

        # --- Smoothing ---
        if self.smoothing > 1:
            self.history.append(normalized)
            if len(self.history) > self.smoothing:
                self.history.pop(0)
            return sum(self.history) / len(self.history)

        return normalized

    # ------------------------------------------------------------------
    def allow_trade(self, headline: str, side: str = "BUY") -> bool:
        """Return True if trade is allowed under sentiment rules."""
        if not self.enabled:
            return True
        if self.analyzer is None:
            logger.debug("ℹ️ Analyzer=None → allow all trades")
            return True

        score = self.score(headline)
        side = side.upper()

        # HOLD always allowed
        if side == "HOLD":
            return True

        # Unknown side allowed
        if side not in {"BUY", "SELL", "HOLD"}:
            logger.debug("ℹ️ Unknown side → allowed")
            return True

        # --- Threshold veto ---
        if score < self.threshold:
            logger.warning(
                f"⚠️ Emotional Filter blocked {side} | score={score:.2f} | threshold={self.threshold}"
            )
            return False

        # --- Neutral zone → allow ---
        if abs(score) <= self.neutral_zone:
            logger.debug(f"ℹ️ Score={score:.2f} inside neutral zone → allowed")
            return True

        # --- Bias overrides ---
        if self.bias == "bullish" and side == "SELL":
            logger.warning(f"⚠️ Bullish bias blocks SELL | score={score:.2f}")
            return False
        if self.bias == "bearish" and side == "BUY":
            logger.warning(f"⚠️ Bearish bias blocks BUY | score={score:.2f}")
            return False

        return True
