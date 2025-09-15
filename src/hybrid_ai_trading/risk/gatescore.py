"""
GateScore Ensemble Voting (Hybrid AI Quant Pro v14.5 - Final, Polished & 100% Coverage)
--------------------------------------------------------------------------------------
- Aggregates multiple AI model confidences
- Blocks trades unless ensemble ≥ threshold
- Explainability: logs per-model contributions
- Adaptive thresholding based on detected regime (optional)
- Config-driven initialization from config.yaml
- Audit-friendly: deterministic outputs
- Full branch coverage (neutral fallback, regime errors, no models, strict_missing, etc.)
"""

import logging
from typing import Dict, List, Optional, Tuple, Union

from hybrid_ai_trading.config.settings import CONFIG
from hybrid_ai_trading.risk.regime_detector import RegimeDetector

logger = logging.getLogger(__name__)


class GateScore:
    def __init__(
        self,
        enabled: Optional[bool] = None,
        threshold: Optional[float] = None,
        models: Optional[List[str]] = None,
        weights: Optional[Dict[str, float]] = None,
        adaptive: Optional[bool] = None,
        strict_missing: Optional[bool] = None,
        audit_mode: bool = False,
    ) -> None:
        cfg = CONFIG.get("gatescore", {})

        # Config-driven fallback
        self.enabled = enabled if enabled is not None else cfg.get("enabled", True)
        self.base_threshold = threshold if threshold is not None else cfg.get("threshold", 0.85)
        self.models = models or cfg.get("models", [])
        self.weights = self._normalize_weights(weights or cfg.get("weights", {}))
        self.adaptive = adaptive if adaptive is not None else cfg.get("adaptive", True)
        self.strict_missing = strict_missing if strict_missing is not None else False
        self.audit_mode = audit_mode

        self.regime_detector = RegimeDetector()

        logger.info(
            "✅ GateScore initialized | enabled=%s | base_threshold=%.2f | adaptive=%s | models=%s | weights=%s | strict_missing=%s",
            self.enabled,
            self.base_threshold,
            self.adaptive,
            self.models,
            self.weights,
            self.strict_missing,
        )

    # --------------------------------------------------
    def _normalize_weights(self, weights: Dict[str, float]) -> Dict[str, float]:
        """Ensure weights sum to 1.0, fallback to equal if invalid."""
        if not weights and self.models:
            weights = {m: 1 / len(self.models) for m in self.models}

        total = sum(weights.values())
        if total <= 0:
            logger.warning("⚠️ Invalid or empty weights, falling back to equal split.")
            return {m: 1 / len(weights) for m in weights} if weights else {}

        return {m: w / total for m, w in weights.items()}

    def adjusted_threshold(self, regime: str) -> float:
        """Adjust threshold based on market regime (if adaptive enabled)."""
        if not self.adaptive:
            return self.base_threshold

        if regime == "crisis":
            return min(0.95, self.base_threshold + 0.10)
        elif regime == "bear":
            return self.base_threshold + 0.05
        elif regime == "bull":
            return max(0.70, self.base_threshold - 0.05)
        return self.base_threshold

    # --------------------------------------------------
    def allow_trade(
        self,
        ai_inputs: Dict[str, float],
        symbol: Optional[str] = None,
        **kwargs,  # ✅ Accept extra params like regime
    ) -> Union[bool, Tuple[bool, float, float, str]]:
        """
        Evaluate ensemble score against threshold.

        Args:
            ai_inputs: dict of model_name → confidence
            symbol: optional symbol for regime detection
            kwargs: may include regime="bull"/"bear"/"crisis"/etc.

        Returns:
            bool or (decision, score, threshold, regime) if audit_mode
        """
        if not self.enabled:
            logger.info("ℹ️ GateScore disabled → always allow")
            regime = kwargs.get("regime", "neutral")
            return (True, 1.0, self.base_threshold, regime) if self.audit_mode else True

        # Detect regime (external override has priority)
        regime = kwargs.get("regime", "neutral")
        if regime == "neutral" and self.regime_detector:
            try:
                regime = self.regime_detector.detect(symbol) or "neutral"
            except Exception as e:
                logger.error("❌ Regime detection failed: %s", e)
                regime = "neutral"

        logger.info("🔎 GateScore evaluation (symbol=%s, regime=%s)", symbol, regime)

        used_models = []
        weighted_sum, total_weight = 0.0, 0.0

        for m in self.models:
            conf = ai_inputs.get(m)

            # Special mapping: regime → confidence
            if m == "regime":
                mapping = {"bull": 1.0, "bear": 0.0, "sideways": 0.5, "crisis": 0.2}
                conf = mapping.get(regime, 0.5)

            if conf is None:
                if self.strict_missing:
                    logger.warning("⚠️ Model %s missing confidence → veto trade", m)
                    return (False, 0.0, self.base_threshold, regime) if self.audit_mode else False
                else:
                    logger.info("ℹ️ Model %s missing → ignored", m)
                    continue

            w = self.weights.get(m, 1.0 / max(len(self.models), 1))
            weighted_sum += conf * w
            total_weight += w
            used_models.append((m, conf, w))

        if total_weight == 0:
            logger.warning("⚠️ No contributing models → default HOLD/blocked")
            return (False, 0.0, self.base_threshold, regime) if self.audit_mode else False

        ensemble_score = weighted_sum / total_weight
        threshold = self.adjusted_threshold(regime)

        # Log contributions
        for m, conf, w in used_models:
            logger.info("   🔹 %-10s | conf=%.2f | weight=%.2f", m, conf, w)
        logger.info("   ➡️ Ensemble Score=%.2f | Threshold=%.2f", ensemble_score, threshold)

        decision = ensemble_score >= threshold
        if decision:
            logger.info("✅ GateScore passed")
        else:
            logger.warning("❌ GateScore blocked trade")

        return (decision, ensemble_score, threshold, regime) if self.audit_mode else decision
