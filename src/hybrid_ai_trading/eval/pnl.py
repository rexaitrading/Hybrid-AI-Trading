from __future__ import annotations

import pandas as pd


def simulate_rr_exit(
    df: pd.DataFrame,
    entry_idx,
    direction: int,
    tick_size: float,
    rr_target: float,
    risk_ticks: int = 5,
):
    """
    Simple R-multiple simulator: stop = entry -/+ risk_ticks*tick_size; target = entry +/ rr_target*risk.
    direction: +1 long, -1 short
    Returns: pnl in ticks (float), exit_index (pd.Timestamp)
    """
    assert direction in (1, -1)
    entry = float(df.loc[entry_idx, "close"])
    risk = risk_ticks * tick_size
    if direction == 1:
        stop = entry - risk
        target = entry + rr_target * risk
        for ts, row in df.loc[df.index >= entry_idx].iterrows():
            if row["low"] <= stop:
                return -risk / tick_size, ts
            if row["high"] >= target:
                return rr_target * risk / tick_size, ts
        return (df.iloc[-1]["close"] - entry) / tick_size, df.index[-1]
    else:
        stop = entry + risk
        target = entry - rr_target * risk
        for ts, row in df.loc[df.index >= entry_idx].iterrows():
            if row["high"] >= stop:
                return -risk / tick_size, ts
            if row["low"] <= target:
                return rr_target * risk / tick_size, ts
        return (entry - df.iloc[-1]["close"]) / tick_size, df.index[-1]
