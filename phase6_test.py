from hybrid_ai_trading.models.orb_model import ORBModel
from hybrid_ai_trading.models.vwap_model import VWAPModel
from hybrid_ai_trading.models.hybrid_gate import HybridGate
from hybrid_ai_trading.runners.orb_vwap_replay import ORBVWAPReplay
from hybrid_ai_trading.models.orb_model import ORBResult
from hybrid_ai_trading.models.vwap_model import VWAPResult

print("=== IMPORTS OK ===")

# ORB TEST
orb = ORBModel(orb_minutes=5)
orb.update_bar(1, 100, 99)
orb.update_bar(2, 101, 99)
orb.update_bar(3, 102, 100)
orb.update_bar(4, 103, 101)
orb.update_bar(5, 104, 103)
orb.finalize()

print("ORB HIGH/LOW:", orb.orb_high, orb.orb_low)
print("ORB EVAL UP:", orb.evaluate(106))
print("ORB EVAL INSIDE:", orb.evaluate(102))
print("ORB EVAL DOWN:", orb.evaluate(98))

# VWAP TEST
v = VWAPModel()
print("VWAP 1:", v.update(100,10))
print("VWAP 2:", v.update(101,20))
print("VWAP 3:", v.update(102,15))

# HYBRID GATE TEST
gate = HybridGate()
orb_res  = ORBResult(104, 99, "up",   0.7, "breakout_up")
vwap_res = VWAPResult(101, 5,  1.0,  "trend_up", 0.7)

decision = gate.decide(
    orb = orb_res,
    vwap = vwap_res,
    kelly_f = 0.05,
    sentiment_score = 0.1,
    regime_conf = 0.5,
    risk_approved = True,
)
print("HYBRID DECISION:", decision)

# REPLAY ENGINE TEST
print("\n=== REPLAY ENGINE ===")
replay = ORBVWAPReplay()
for i in range(10):
    out = replay.replay_bar(
        ts=i,
        price=100+i,
        volume=10*(i+1),
        minute_index=i
    )
    if out:
        print(out)
