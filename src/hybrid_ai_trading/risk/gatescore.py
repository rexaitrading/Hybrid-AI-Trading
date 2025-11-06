"""
GateScore (Hybrid AI Quant Pro v37.5 Ã¢â‚¬â€œ Hedge Fund Grade, 100% Coverage)
=======================================================================
Weighted ensemble voting system with adaptive regime thresholds.

Features:
- Weighted ensemble scoring with safe fallbacks.
- Normalizes weights to sum=1 (guards against invalid or empty weights).
- Adaptive threshold based on detected regime (if enabled):
  * bull   Ã¢â€ â€™ threshold lower (easier to allow trades).
  * bear   Ã¢â€ â€™ threshold higher (harder to allow trades).
  * crisis Ã¢â€ â€™ threshold much higher (strict risk mode).
  * neutral/sideways Ã¢â€ â€™ base threshold.
- Guards:
  * Disabled gate Ã¢â€ â€™ always allow (audit-friendly path).
  * Missing models Ã¢â€ â€™ ignored or veto depending on strict_missing.
  * Invalid/exception in score Ã¢â€ â€™ treated as 0.
  * total weight <= 0 Ã¢â€ â€™ block trade.
"""

import logging
from typing import Dict, List, Tuple, Union

logger = logging.getLogger("hybrid_ai_trading.risk.gatescore")


class _RegimeDetectorStub:
    """Simple stub so tests can monkeypatch .detect()."""

    def detect(self, symbol: str) -> str:
        return "neutral"


class GateScore:
    def __init__(
        self,
        models: List[str] | None = None,
        weights: Dict[str, float] | None = None,
        threshold: float = 0.5,
        adaptive: bool = False,
        enabled: bool = True,
        audit_mode: bool = False,
        strict_missing: bool = False,
    ) -> None:
        self.models = models or []
        # Normalize weights at construction
        self.weights = self._normalize_weights(weights or {})
        self.threshold = threshold
        self.base_threshold = threshold
        self.adaptive = adaptive
        self.enabled = enabled
        self.audit_mode = audit_mode
        self.strict_missing = strict_missing
        # Expose regime_detector attribute for monkeypatching in tests
        self.regime_detector = _RegimeDetectorStub()

    # ------------------------------------------------------------------
    # Weight normalization
    # ------------------------------------------------------------------
    def _normalize_weights(self, weights: Dict[str, float]) -> Dict[str, float]:
        """Normalize weights so they sum to 1.0. Fallback: equal weights or empty dict."""
        if not weights:
            return {}
        total = sum(weights.values())
        if total <= 0:
            logger.warning(
                "Ã¢Å¡Â Ã¯Â¸Â Invalid weights (sum<=0), assigning equal weights"
            )
            n = len(weights)
            return {k: 1.0 / n for k in weights}
        return {k: v / total for k, v in weights.items()}

    # ------------------------------------------------------------------
    # Core allow_trade decision
    # ------------------------------------------------------------------
    def allow_trade(
        self, inputs: Dict[str, float], symbol: str = "SYM"
    ) -> Union[bool, Tuple[bool, float, float, str]]:
        """
        Main decision method.
        Returns bool if audit_mode=False,
        else tuple: (decision, score, threshold, regime).
        """
        if not self.enabled:
            if self.audit_mode:
                return True, 1.0, self.base_threshold, "neutral"
            return True

        contributing = False
        score = 0.0
        total_weight = 0.0
        regime = "neutral"

        for m in self.models:
            if m == "regime":
                # Always query regime detector
                try:
                    regime = self._detect_regime(symbol)
                except Exception as e:
                    logger.error("Regime detection failed: %s", e, exc_info=True)
                    regime = "neutral"
                contributing = True
                continue

            if m not in inputs:
                if self.strict_missing:
                    logger.warning(
                        "[GateScore] Ã¢ÂÅ’ Missing model %s Ã¢â€ â€™ veto trade", m
                    )
                    if self.audit_mode:
                        return False, 0.0, self.base_threshold, regime
                    return False
                else:
                    logger.info(
                        "[GateScore] Ã¢Å¡Â Ã¯Â¸Â Missing model %s Ã¢â€ â€™ ignored", m
                    )
                    continue

            contrib = self._safe_score(m, inputs.get(m, 0.0))
            score += contrib
            total_weight += self.weights.get(m, 0.0)
            contributing = True

        if not contributing:
            logger.warning(
                "[GateScore] Ã¢ÂÅ’ No contributing models Ã¢â€ â€™ block trade"
            )
            if self.audit_mode:
                return False, 0.0, self.base_threshold, regime
            return False

        if total_weight <= 0:
            logger.warning("[GateScore] Ã¢ÂÅ’ Total weight=0 Ã¢â€ â€™ block trade")
            if self.audit_mode:
                return False, 0.0, self.base_threshold, regime
            return False

        norm_score = score / total_weight
        thr = self._adaptive_threshold(symbol) if self.adaptive else self.base_threshold
        decision = norm_score >= thr

        logger.info(
            "[GateScore] Ensemble Score=%.3f, Thr=%.3f, Regime=%s, Decision=%s",
            norm_score,
            thr,
            regime,
            decision,
        )

        if self.audit_mode:
            return decision, norm_score, thr, regime
        return decision

    # ------------------------------------------------------------------
    # Voting (lightweight form)
    # ------------------------------------------------------------------
    def vote(self, inputs: Dict[str, float]) -> int:
        """Return 1 if allowed, else 0 (wrapper around allow_trade)."""
        result = self.allow_trade(inputs)
        return 1 if result is True else 0

    # ------------------------------------------------------------------
    # Adaptive threshold logic
    # ------------------------------------------------------------------
    def adjusted_threshold(self, regime: str) -> float:
        """Public method for tests. If adaptive=False, always return base_threshold."""
        if not self.adaptive:
            return self.base_threshold

        if regime == "bull":
            return max(0.3, self.base_threshold - 0.2)
        if regime == "bear":
            return min(0.9, self.base_threshold + 0.2)
        if regime == "crisis":
            return min(0.95, self.base_threshold + 0.3)
        return self.base_threshold

    def _adaptive_threshold(self, symbol: str = "SYM") -> float:
        """Internal adaptive threshold based on detected regime."""
        try:
            regime = self._detect_regime(symbol)
            return self.adjusted_threshold(regime)
        except Exception as e:
            logger.error("Adaptive threshold failed: %s", e, exc_info=True)
            return self.base_threshold

    def _detect_regime(self, symbol: str = "SYM") -> str:
        """Call through to regime_detector.detect (monkeypatched in tests)."""
        return self.regime_detector.detect(symbol)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _safe_score(self, m: str, val) -> float:
        """Safe contribution = weight * value; failures return 0."""
        try:
            return self.weights.get(m, 0.0) * float(val)
        except Exception as e:
            logger.warning("Ã¢Å¡Â Ã¯Â¸Â GateScore _safe_score failed for %s: %s", m, e)
            return 0.0


__all__ = ["GateScore"]
