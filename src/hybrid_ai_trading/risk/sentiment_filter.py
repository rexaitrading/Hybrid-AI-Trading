from __future__ import annotations

import logging
from typing import Optional, Any, Dict

logger = logging.getLogger(__name__)

# Optional deps — tests may monkeypatch these names to None
try:
    from nltk.sentiment import SentimentIntensityAnalyzer  # type: ignore
except Exception:  # pragma: no cover
    SentimentIntensityAnalyzer = None  # type: ignore

try:
    from transformers import pipeline  # type: ignore
except Exception:  # pragma: no cover
    pipeline = None  # type: ignore


class SentimentFilter:
    """
    Config-robust sentiment filter:
    - Accepts arbitrary kwargs from config (enabled, model, threshold, neutral_zone, etc.)
    - Ignores unknown keys safely so future config additions won't crash
    - Falls back to neutral scoring (0.0) when analyzer is unavailable
    """

    def __init__(self, **cfg: Any) -> None:
        # Known knobs (with sensible defaults)
        self.enabled: bool = bool(cfg.pop("enabled", True))
        self.model: str = str(cfg.pop("model", "vader"))
        self.threshold: float = float(cfg.pop("threshold", 0.0))
        self.neutral_zone: float = float(cfg.pop("neutral_zone", 0.0))

        # Anything else is accepted and ignored to maintain forward compatibility
        # (kept for potential debugging/inspection)
        self._extra_cfg: Dict[str, Any] = dict(cfg)

        self.analyzer: Optional[Any] = None
        self._init_analyzer()

    def _init_analyzer(self) -> None:
        """Initialize analyzer based on model; if unavailable, fall back to neutral."""
        m = (self.model or "vader").lower()

        if not self.enabled:
            self.analyzer = None
            return

        if m == "vader":
            if SentimentIntensityAnalyzer is not None:
                try:
                    self.analyzer = SentimentIntensityAnalyzer()
                    return
                except Exception:  # pragma: no cover
                    self.analyzer = None
            logger.warning(
                "Analyzer unavailable for model=vader; fallback to neutral scoring (analyzer=None)."
            )
            self.analyzer = None
            return

        if m in ("hf", "transformers", "bert", "distilbert"):
            if pipeline is not None:
                try:
                    self.analyzer = pipeline("sentiment-analysis")
                    return
                except Exception:  # pragma: no cover
                    self.analyzer = None
            logger.warning(
                "Analyzer unavailable for model=hf; fallback to neutral scoring (analyzer=None)."
            )
            self.analyzer = None
            return

        # Unknown model → neutral fallback with explicit wording
        logger.warning(
            "Unknown sentiment model=%s; fallback to neutral scoring (analyzer=None).", m
        )
        self.analyzer = None

    def score(self, text: str) -> float:
        """
        Return sentiment score in [-1, 1].
        - Disabled or missing analyzer → 0.0 (neutral fallback)
        - VADER: compound score
        - HF pipeline: map POSITIVE to +score, NEGATIVE to -score (else 0)
        NOTE: `threshold` / `neutral_zone` are accepted for config compatibility; this returns raw score.
        """
        if not self.enabled or not text:
            return 0.0
        if self.analyzer is None:
            return 0.0

        # VADER path
        if hasattr(self.analyzer, "polarity_scores"):
            try:
                return float(self.analyzer.polarity_scores(text).get("compound", 0.0))
            except Exception:
                logger.exception("VADER scoring failed; fallback to neutral (0.0).")
                return 0.0

        # HF pipeline path
        try:
            out = self.analyzer(text)
            if not out:
                return 0.0
            r0: Dict[str, Any] = out[0]
            label = str(r0.get("label", "")).upper()
            val = float(r0.get("score", 0.0))
            if "POS" in label:
                return +val
            if "NEG" in label:
                return -val
            return 0.0
        except Exception:
            logger.exception("HF scoring failed; fallback to neutral (0.0).")
            return 0.0