import pandas as pd

from hybrid_ai_trading.tools.bar_replay import load_bars, run_replay

df = load_bars("data/SPY_1m_sample.csv")
res = run_replay(
    df,
    symbol="SPY",
    mode="auto",
    speed=1000,
    force_exit=True,
    orb_minutes=5,
    risk_cents=20,
    max_qty=50,
)
print("RESULT:", res)
