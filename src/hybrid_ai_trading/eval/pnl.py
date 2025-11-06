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
    R/R exit simulator (target-first, robust to missing OHLC):
      - Entry: prefer row fields price/entry/entry_price/break/breakout/vwap/VWAP/open/Open/close/Close (else first numeric).
      - Compute target/stop using tick_size, rr_target, risk_ticks.
      - For each bar from entry forward, synthesize range:
          bar_high = max(High, Close, Open) among available columns
          bar_low  = min(Low,  Close, Open) among available columns
      - If target and stop touch the same bar, TARGET wins.
      - If target ever touched → return its first hit (positive ticks for long).
      - Else if stop touched   → return its first hit.
      - Else flatten at last close.
    Returns (ticks: float, exit_idx).
    """
    if tick_size is None or tick_size <= 0:
        raise ValueError("tick_size must be > 0")
    if direction not in (1, -1):
        raise ValueError("direction must be 1 or -1")

    # --- entry price from the entry row ---
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

    tgt_off = float(risk_ticks) * float(rr_target) * float(tick_size)
    stp_off = float(risk_ticks) * float(tick_size)
    if direction == 1:
        target, stop = entry + tgt_off, entry - stp_off
    else:
        target, stop = entry - tgt_off, entry + stp_off

    cols = set(df.columns)

    def _pick(*names):
        for n in names:
            if n in cols:
                return n
        return None

    hiC = _pick("high", "High", "HIGH", "H")
    loC = _pick("low", "Low", "LOW", "L")
    opC = _pick("open", "Open", "OPEN", "O")
    clC = _pick("close", "Close", "CLOSE", "C")

    def _num(r, c):
        if not c:
            return None
        try:
            v = r[c]
            return float(v) if isinstance(v, (int, float)) else None
        except Exception:
            return None

    start = df.index.get_loc(entry_idx)
    first_tgt = None
    first_stp = None

    for i in range(start, len(df)):
        r = df.iloc[i]
        base = _num(r, clC) or entry
        hi = max(
            [v for v in (_num(r, hiC), _num(r, opC), _num(r, clC)) if v is not None]
            or [base]
        )
        lo = min(
            [v for v in (_num(r, loC), _num(r, opC), _num(r, clC)) if v is not None]
            or [base]
        )

        hit_t = (hi >= target) if direction == 1 else (lo <= target)
        hit_s = (lo <= stop) if direction == 1 else (hi >= stop)

        # Same-bar tie → target wins immediately
        if hit_t and hit_s:
            raw = (
                (target - entry) / tick_size
                if direction == 1
                else (entry - target) / tick_size
            )
            return (float(round(raw, 4)), df.index[i])

        if hit_t and first_tgt is None:
            first_tgt = i
        if hit_s and first_stp is None:
            first_stp = i

        # If both discovered and target is earlier-or-equal, we’re done
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

    # No touch → flatten at last close
    lc = _num(df.iloc[-1], clC) or entry
    raw = (lc - entry) / tick_size if direction == 1 else (entry - lc) / tick_size
    return (float(round(raw, 4)), df.index[-1])
