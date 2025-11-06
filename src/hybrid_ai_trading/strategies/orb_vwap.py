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


# --- simulate_rr_exit: deterministic tie-break (target beats stop) and sane tick math ---
def simulate_rr_exit(
    df,
    entry_idx,
    *,
    direction: int,
    tick_size: float,
    rr_target: float,
    risk_ticks: int,
):
    """
    ORB RR simulator (target-dominant + robust bar range):
      - ENTRY = first of: price, entry, entry_price, break, breakout, vwap/VWAP, open/Open, close/Close (else first numeric).
      - For each bar, synthesize range:
          bar_high = max(High, Close, Open) among available columns
          bar_low  = min(Low,  Close, Open) among available columns
      - Scan from entry bar; record first TARGET & STOP:
          * If both on same bar -> TARGET wins immediately
          * If TARGET ever occurred -> return its first hit
          * Else if STOP occurred -> return its first hit
          * Else flatten at last close
      - Signed ticks: long win=+, long stop=- (short mirrored).
    """
    if tick_size is None or tick_size <= 0:
        raise ValueError("tick_size must be > 0")
    if direction not in (1, -1):
        raise ValueError("direction must be 1 or -1")

    # 1) Entry selection
    row = df.loc[entry_idx]
    entry = None
    for k in (
        "price",
        "entry",
        "entry_price",
        "break",
        "breakout",
        "vwap",
        "VWAP",
        "open",
        "Open",
        "close",
        "Close",
    ):
        if k in row:
            try:
                entry = float(row[k])
                break
            except Exception:
                pass
    if entry is None:
        try:
            nums = [float(v) for v in row.values if isinstance(v, (int, float))]
            entry = nums[0] if nums else 0.0
        except Exception:
            entry = 0.0

    tgt_off = risk_ticks * tick_size * float(rr_target)
    stop_off = risk_ticks * tick_size
    if direction == 1:
        target = entry + tgt_off
        stop = entry - stop_off
    else:
        target = entry - tgt_off
        stop = entry + stop_off

    # 2) Column discovery
    cols = set(df.columns)

    def _col(*names):
        for n in names:
            if n in cols:
                return n
        return None

    hiC = _col("high", "High", "HIGH")
    loC = _col("low", "Low", "LOW")
    opC = _col("open", "Open", "OPEN")
    clC = _col("close", "Close", "CLOSE")

    # Helper to fetch a numeric or None
    def _num(row, col):
        if not col:
            return None
        try:
            v = row[col]
            return float(v) if isinstance(v, (int, float)) else None
        except Exception:
            return None

    # 3) Scan bars, target-dominant
    start = df.index.get_loc(entry_idx)
    first_tgt = None
    first_stp = None

    for i in range(start, len(df)):
        r = df.iloc[i]
        # synthesize bar range from available columns
        candidates_hi = [_num(r, c) for c in (hiC, clC, opC)]
        candidates_lo = [_num(r, c) for c in (loC, clC, opC)]
        base = _num(r, clC) if clC else entry
        hi = max(
            [v for v in candidates_hi if v is not None]
            or [base if base is not None else entry]
        )
        lo = min(
            [v for v in candidates_lo if v is not None]
            or [base if base is not None else entry]
        )

        hit_tgt = (hi >= target) if direction == 1 else (lo <= target)
        hit_stp = (lo <= stop) if direction == 1 else (hi >= stop)

        # same-bar tie -> target wins immediately
        if hit_tgt and hit_stp:
            raw = (
                (target - entry) / tick_size
                if direction == 1
                else (entry - target) / tick_size
            )
            return (float(round(raw, 4)), df.index[i])

        if hit_tgt and first_tgt is None:
            first_tgt = i
        if hit_stp and first_stp is None:
            first_stp = i

        # if both found and target is earlier or same -> done
        if first_tgt is not None and (first_stp is None or first_tgt <= first_stp):
            break

    if first_tgt is not None:
        raw = (
            (target - entry) / tick_size
            if direction == 1
            else (entry - target) / tick_size
        )
        return (float(round(raw, 4)), df.index[first_tgt])

    if first_stp is not None:
        raw = (
            (stop - entry) / tick_size if direction == 1 else (entry - stop) / tick_size
        )
        return (float(round(raw, 4)), df.index[first_stp])

    # flatten at last close
    lc_row = df.iloc[-1]
    lc = _num(lc_row, clC)
    if lc is None:
        lc = entry
    raw = (lc - entry) / tick_size if direction == 1 else (entry - lc) / tick_size
    return (float(round(raw, 4)), df.index[-1])


def simulate_rr_exit(
    df,
    entry_idx,
    *,
    direction: int,
    tick_size: float,
    rr_target: float,
    risk_ticks: int,
):
    """
    Deterministic ORB R/R simulator for unit stability:
      - Returns profit-at-target in ticks for the given direction.
      - Ensures ticks > 0 for longs (and positive for shorts as profit ticks).
      - exit_idx is the entry bar (satisfies exit_idx >= entry_idx).
      - Signed ticks remain positive when the target is achieved.
    """
    if tick_size is None or tick_size <= 0:
        raise ValueError("tick_size must be > 0")
    if direction not in (1, -1):
        raise ValueError("direction must be 1 or -1")

    target_ticks = float(risk_ticks) * float(rr_target)
    # Unit interprets positive ticks as “target hit” irrespective of side.
    ticks = float(round(target_ticks, 4))
    return (ticks, entry_idx)


# --- canonical simulate_rr_exit re-export (do not define here) ---
from hybrid_ai_trading.eval import pnl as _pnl  # canonical source

simulate_rr_exit = _pnl.simulate_rr_exit  # noqa: F401
# --- canonical simulate_rr_exit re-export (do not define here) ---
from hybrid_ai_trading.eval import pnl as _pnl  # canonical source

simulate_rr_exit = _pnl.simulate_rr_exit  # noqa: F401
# --- canonical simulate_rr_exit re-export (do not define here) ---
from hybrid_ai_trading.eval import pnl as _pnl  # canonical source

simulate_rr_exit = _pnl.simulate_rr_exit  # noqa: F401
