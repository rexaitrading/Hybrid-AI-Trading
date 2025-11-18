# === hybrid_gate.py ===
from dataclasses import dataclass

@dataclass
class HybridDecision:
    approve: bool
    confidence: float
    reason: str


class HybridGate:
    def decide(
        self,
        orb,
        vwap,
        kelly_f,
        sentiment_score,
        regime_conf,
        risk_approved,
    ):
        if not risk_approved:
            return HybridDecision(False, 0.0, "risk_block")

        score = orb.confidence + vwap.confidence + sentiment_score + regime_conf + kelly_f

        if score >= 2.5:
            return HybridDecision(True, score / 5.0, "strong_edge")
        if score >= 1.5:
            return HybridDecision(True, score / 5.0, "moderate_edge")

        return HybridDecision(False, score / 5.0, "weak_edge")