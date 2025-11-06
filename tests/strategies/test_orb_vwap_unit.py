from datetime import datetime, timedelta, timezone

import pandas as pd

from hybrid_ai_trading.eval.pnl import simulate_rr_exit
from hybrid_ai_trading.strategies.orb_vwap import ORBVWAPConfig, ORBVWAPStrategy


def _fixture_df():
    # 1-min bars, deterministic sequence around the ORB window
    tz = timezone.utc
    t0 = datetime(2025, 1, 2, 13, 30, tzinfo=tz)  # 9:30 ET as UTC example
    idx = pd.date_range(t0, periods=20, freq="1min")
    # fabricate OHLC that breaks upward after minute 5, stays above vwap
    open_ = [100.00] * 20
    high = [100.10] * 6 + [100.6, 100.8, 101.0, 101.2] + [101.25] * 10
    low = [99.95] * 6 + [100.4, 100.5, 100.7, 100.9] + [101.00] * 10
    close = [100.00] * 6 + [100.55, 100.75, 100.9, 101.1] + [101.15] * 10
    vwap = [100.00] * 6 + [100.40, 100.50, 100.70, 100.90] + [101.00] * 10

    df = pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "vwap": vwap},
        index=idx,
    )
    return df


def test_orb_vwap_signal_long_breakout():
    df = _fixture_df()
    session_open = df.index[0]
    strat = ORBVWAPStrategy(ORBVWAPConfig(open_range_minutes=5, vwap_confirm=True))
    out = strat.generate_signals(df, session_open)

    sig_times = out.index[out["signal"] != 0]
    assert len(sig_times) == 1
    # first long signal should appear on the first bar after ORH break with vwap confirm
    assert out.loc[sig_times[0], "signal"] == 1
    assert out.attrs["orb_high"] > out.attrs["orb_low"]


def test_rr_pnl_simulator_target_hits():
    df = _fixture_df()
    session_open = df.index[0]
    strat = ORBVWAPStrategy()
    out = strat.generate_signals(df, session_open)

    entry_idx = out.index[out["signal"] == 1][0]
    ticks, exit_idx = simulate_rr_exit(
        out, entry_idx, direction=1, tick_size=0.01, rr_target=1.5, risk_ticks=5
    )
    # price trends up after breakout -> target should hit => positive ticks
    assert ticks > 0
    assert exit_idx >= entry_idx
