# === orb_vwap_replay.py ===

from hybrid_ai_trading.models.orb_model import ORBModel
from hybrid_ai_trading.models.vwap_model import VWAPModel
from hybrid_ai_trading.models.hybrid_gate import HybridGate

class ORBVWAPReplay:
    def __init__(self):
        self.orb = ORBModel(orb_minutes=5)
        self.vwap = VWAPModel()
        self.gate = HybridGate()

    def replay_bar(self, ts, price, volume, minute_index):
        if minute_index < 5:
            self.orb.update_bar(ts, price, price)
            if minute_index == 4:
                self.orb.finalize()
            return None

        vwap_result = self.vwap.update(price, volume)
        orb_result = self.orb.evaluate(price)

        decision = self.gate.decide(
            orb=orb_result,
            vwap=vwap_result,
            kelly_f=0.05,
            sentiment_score=0.0,
            regime_conf=0.5,
            risk_approved=True,
        )

        return {
            "ts": ts,
            "price": price,
            "orb": orb_result,
            "vwap": vwap_result,
            "decision": decision,
        }