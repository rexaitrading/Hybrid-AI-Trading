"""
Test Harness for TradeEngine v7.2 (Hybrid AI Quant Pro)
-------------------------------------------------------
- Simulates trades under:
  • Sentiment scores
  • GateScore ensemble confidence
  • Market regimes (bull / bear / crisis)
- Prints GateScore ensemble score + threshold (audit mode)
"""

import os, yaml
from hybrid_ai_trading.trade_engine import TradeEngine
from hybrid_ai_trading.execution.portfolio_tracker import PortfolioTracker

# --- Load config ---
with open("config/config.yaml", "r", encoding="utf-8-sig") as f:
    cfg = yaml.safe_load(f)

# Inject AI signals + test headline
cfg["price_ai_confidence"] = 0.9
cfg["macro_ai_confidence"] = 0.8
cfg["last_headline"] = "BREAKING: Market crash panic spreads after unexpected Fed move"
c
# --- Force audit mode for GateScore ---
if "gatescore" in cfg:
    cfg["gatescore"]["audit_mode"] = True   # ✅ activate audit mode

# --- Initialize engine ---
engine = TradeEngine(cfg, portfolio=PortfolioTracker(100000))

def run_case(title, fn):
    print(f"\n=== {title} ===")
    result = fn()
    if isinstance(result, tuple):  # audit mode (decision, score, threshold)
        decision, score, threshold = result
        print(f"GateScore decision={decision} | score={score:.2f} | threshold={threshold:.2f}")
    else:
        print(result)

# --- Normal Bullish Trade ---
run_case("Normal Bullish Trade", lambda: engine.process_signal("AAPL", "BUY", size=1, price=150))

# --- Bear Regime Adjustment ---
engine.regime_detector.detect = lambda s: "bear"
run_case("Bear Regime Adjustment", lambda: engine.process_signal("AAPL", "BUY", size=1, price=150))

# --- Bull Regime Adjustment ---
engine.regime_detector.detect = lambda s: "bull"
run_case("Bull Regime Adjustment", lambda: engine.process_signal("AAPL", "SELL", size=1, price=150))

# --- Crisis Regime Halt ---
engine.regime_detector.detect = lambda s: "crisis"
run_case("Crisis Regime Halt", lambda: engine.process_signal("AAPL", "BUY", size=1, price=150))

# --- Emotional Headline ---
cfg["last_headline"] = "🚀 TSLA surges 50% overnight — insane rally continues"
run_case("Emotional Filter Block", lambda: engine.process_signal("TSLA", "BUY", size=1, price=900))

# --- Weak GateScore Ensemble ---
engine.gatescore.allow_trade = lambda inputs, regime=None: (False, 0.40, 0.85)  # simulate low score
run_case("Weak GateScore Block", lambda: engine.process_signal("ETH/USDT", "BUY", size=1, price=2000))

print("\n=== Portfolio Report ===")
print(engine.portfolio.report())
