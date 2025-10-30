from datetime import datetime, timedelta

import pandas as pd

from hybrid_ai_trading.tools.bar_replay import run_replay

t0 = datetime(2025, 10, 24, 9, 30)
rows = []
# ORB (2 bars)
rows += [
    {
        "timestamp": t0,
        "open": 100,
        "high": 101,
        "low": 99,
        "close": 100.5,
        "volume": 1000,
    },
    {
        "timestamp": t0 + timedelta(minutes=1),
        "open": 100.5,
        "high": 102,
        "low": 100,
        "close": 101.8,
        "volume": 1200,
    },
]
# Breakout (enter)
rows += [
    {
        "timestamp": t0 + timedelta(minutes=2),
        "open": 101.8,
        "high": 103,
        "low": 101.6,
        "close": 102.5,
        "volume": 1500,
    }
]
# Drop below ORB low (exit)
rows += [
    {
        "timestamp": t0 + timedelta(minutes=3),
        "open": 102.5,
        "high": 102.6,
        "low": 98.5,
        "close": 99.4,
        "volume": 1800,
    }
]

df = pd.DataFrame(rows)
res = run_replay(
    df=df,
    symbol="TEST",
    mode="auto",
    speed=100.0,
    fees_per_share=0.0,
    orb_minutes=2,
    risk_cents=20.0,
    max_qty=50,
    force_exit=False,
)
print("SANITY:", res)
