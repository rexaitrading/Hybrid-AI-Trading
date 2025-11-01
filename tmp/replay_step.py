import pandas as pd

from hybrid_ai_trading.tools.bar_replay import load_bars, run_replay

df = load_bars("data/SPY_1m_sample.csv")
run_replay(
    df,
    symbol="SPY",
    mode="step",
    speed=2.0,
    orb_minutes=5,
    risk_cents=20,
    max_qty=50,
    force_exit=False,
)
