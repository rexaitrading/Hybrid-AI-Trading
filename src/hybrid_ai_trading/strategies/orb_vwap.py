from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ORBVWAPConfig:
    open_range_minutes: int = 5  # minutes after session open to form the ORB
    vwap_confirm: bool = True  # require price above/below VWAP for signal
    tick_size: float = 0.01  # for stops/targets rounding
    rr_target: float = 1.5  # risk:reward target multiple


class ORBVWAPStrategy:
    """
    Deterministic micro-scalper: Long when price breaks ORH with VWAP confirm; Short on ORL break with VWAP confirm.
    No external IO. Expects a DataFrame with:
      index: pd.DatetimeIndex (intraday, tz-aware or naive but consistent)
      columns: ["open","high","low","close","vwap"]
    """

    def __init__(self, cfg: ORBVWAPConfig | None = None):
        self.cfg = cfg or ORBVWAPConfig()

    def generate_signals(
        self, df: pd.DataFrame, session_open: pd.Timestamp
    ) -> pd.DataFrame:
        df = df.copy()
        cfg = self.cfg

        # Build the opening range high/low
        end = session_open + pd.Timedelta(minutes=cfg.open_range_minutes)
        mask_or = (df.index >= session_open) & (df.index < end)
        orh = df.loc[mask_or, "high"].max()
        orl = df.loc[mask_or, "low"].min()

        df["signal"] = 0
        post_or = df.index >= end

        # Breakout with optional VWAP confirm
        if cfg.vwap_confirm:
            long_mask = post_or & (df["high"] >= orh) & (df["close"] >= df["vwap"])
            short_mask = post_or & (df["low"] <= orl) & (df["close"] <= df["vwap"])
        else:
            long_mask = post_or & (df["high"] >= orh)
            short_mask = post_or & (df["low"] <= orl)

        # First breakout only (simple micro entry)
        if long_mask.any() and (~short_mask).any():
            first_long_idx = long_mask[long_mask].index[0]
            df.loc[first_long_idx, "signal"] = 1
        if short_mask.any() and (~long_mask).any():
            first_short_idx = short_mask[short_mask].index[0]
            # respect whichever comes first in time
            if df["signal"].eq(1).any():
                if first_short_idx < df.index[df["signal"] == 1][0]:
                    df.loc[df["signal"] == 1, "signal"] = 0
                    df.loc[first_short_idx, "signal"] = -1
            else:
                df.loc[first_short_idx, "signal"] = -1

        df.attrs["orb_high"] = float(orh)
        df.attrs["orb_low"] = float(orl)
        return df
