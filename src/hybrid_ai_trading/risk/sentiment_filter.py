from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Optional deps Ã¢â‚¬â€ tests may monkeypatch these names to None
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
    Contract:
    - kwargs-robust init (enabled, model, threshold, neutral_zone, future keys ok)
    - disabled or empty text => score==0.5 (legacy)
    - neutral_zone gate: if abs(raw)<neutral_zone => 0.0
    - unknown model while enabled => ValueError raised in __init__
    - allow_trade(text, side): BUY >= gate, SELL <= -gate; fail-open if disabled/analyzer missing
    """

    _ALLOWED_MODELS = {"vader", "hf", "transformers", "bert", "distilbert"}

    def __init__(self, **cfg: Any) -> None:
        # parse knobs
        self.enabled: bool = bool(cfg.pop("enabled", True))
        self.model: str = str(cfg.pop("model", "vader"))
        self.threshold: float = float(cfg.pop("threshold", 0.0))
        self.neutral_zone: float = float(cfg.pop("neutral_zone", 0.0))
        self._extra_cfg: Dict[str, Any] = dict(cfg)

        # upfront validation so tests see ValueError immediately
        m = (self.model or "vader").lower()
        if self.enabled and m not in self._ALLOWED_MODELS:
            raise ValueError(f"Unknown sentiment model={m}")

        self.analyzer: Optional[Any] = None
        self._init_analyzer()

    def _init_analyzer(self) -> None:
        """Initialize analyzer for supported models; warn+neutral if deps unavailable."""
        if not self.enabled:
            self.analyzer = None
            return

        m = (self.model or "vader").lower()

        if m == "vader":
            if SentimentIntensityAnalyzer is not None:
                try:
                    self.analyzer = SentimentIntensityAnalyzer()
                    return
                except Exception:
                    self.analyzer = None
            logger.warning(
                "Analyzer unavailable for model=vader; fallback to neutral scoring (analyzer=None)."
            )
            self.analyzer = None
            return

        # hf family
        if m in ("hf", "transformers", "bert", "distilbert"):
            if pipeline is not None:
                try:
                    self.analyzer = pipeline("sentiment-analysis")
                    return
                except Exception:
                    self.analyzer = None
            logger.warning(
                "Analyzer unavailable for model=hf; fallback to neutral scoring (analyzer=None)."
            )
            self.analyzer = None
            return

    def score(self, text: str) -> float:
        """
        [-1,1] score.
        - disabled or empty => 0.5 (legacy)
        - no analyzer => 0.0
        - VADER: compound
        - HF: POSITIVE=+score, NEGATIVE=-score
        - neutral_zone gate applied after raw score
        """
        if not self.enabled or not text:
            return 0.5
        if self.analyzer is None:
            return 0.0

        raw: float = 0.0
        if hasattr(self.analyzer, "polarity_scores"):
            try:
                raw = float(self.analyzer.polarity_scores(text).get("compound", 0.0))
            except Exception:
                logger.exception("VADER scoring failed; fallback to neutral (0.0).")
                return 0.0
        else:
            try:
                out = self.analyzer(text)
                if not out:
                    return 0.0
                r0: Dict[str, Any] = out[0]
                label = str(r0.get("label", "")).upper()
                val = float(r0.get("score", 0.0))
                if "POS" in label:
                    raw = +val
                elif "NEG" in label:
                    raw = -val
                else:
                    raw = 0.0
            except Exception:
                logger.exception("HF scoring failed; fallback to neutral (0.0).")
                return 0.0

        if self.neutral_zone > 0.0 and abs(raw) < self.neutral_zone:
            return 0.0
        return raw

    def allow_trade(self, text: str, side: str | None = None) -> bool:
        """
        Disabled => allow; analyzer missing => allow.
        Gate = max(threshold, neutral_zone).
        BUY: score>=gate; SELL: score<=-gate; other sides => allow.
        """
        if not self.enabled:
            return True
        if self.analyzer is None:
            return True
        s = self.score(text)
        gate = max(float(self.threshold or 0.0), float(self.neutral_zone or 0.0))
        if not side:
            return True
        side_u = str(side).upper()
        if side_u == "BUY":
            return s >= gate
        if side_u == "SELL":
            return s <= -gate
        return True
