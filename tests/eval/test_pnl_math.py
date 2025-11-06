from datetime import datetime, timedelta, timezone

import pandas as pd

from hybrid_ai_trading.eval.pnl import simulate_rr_exit


def _df_flat():
    tz = timezone.utc
    t0 = datetime(2025, 1, 2, 13, 30, tzinfo=tz)
    idx = pd.date_range(t0, periods=10, freq="1min")
    close = [100.00] * 10
    return pd.DataFrame(
        {"open": close, "high": close, "low": close, "close": close, "vwap": close},
        index=idx,
    )


def test_rr_exit_no_hit_exits_at_end():
    df = _df_flat()
    entry_idx = df.index[1]
    ticks, exit_idx = simulate_rr_exit(
        df, entry_idx, direction=1, tick_size=0.01, rr_target=2.0, risk_ticks=5
    )
    # flat tape -> no stop/target -> zero PnL, exit at last bar
    assert ticks == 0
    assert exit_idx == df.index[-1]
