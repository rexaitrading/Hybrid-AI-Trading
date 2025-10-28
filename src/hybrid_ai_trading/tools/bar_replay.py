from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple
import math, time
import pandas as pd
from hybrid_ai_trading.tools.replay_logger_hook import log_closed_trade

@dataclass
class Position:
    side: Optional[str] = None
    entry_px: Optional[float] = None
    qty: int = 0

@dataclass
class ReplayResult:
    bars: int
    trades: int
    pnl: float
    entry_px: Optional[float]
    exit_px: Optional[float]
    final_pos: Position

def _to_datetime_col(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce", utc=False)

def orb_strategy_step(idx: int, row: pd.Series, pos: Position,
                      orb_high: float, orb_low: float,
                      risk_cents: float, max_qty: int) -> Tuple[Position, Optional[str]]:
    act = None
    close = float(row["close"])
    if pos.side is None:
        if close > orb_high:
            denom = max(0.01, (orb_high - orb_low))
            qty = max(1, min(max_qty, int(max(1, math.floor((risk_cents/100.0) / denom)))))
            pos = Position(side="long", entry_px=close, qty=qty)
            act = f"enter_long qty={qty} px={close:.4f}"
    else:
        if close < orb_low:
            act = f"exit_long qty={pos.qty} px={close:.4f}"
    return pos, act

def run_replay(df: pd.DataFrame, symbol: str, mode: str = "step", speed: float = 5.0,
               fees_per_share: float = 0.003, orb_minutes: int = 5,
               risk_cents: float = 20.0, max_qty: int = 200,
               force_exit: bool = False) -> ReplayResult:
    assert mode in ("step","auto")
    if "timestamp" in df.columns:
        df["timestamp"] = _to_datetime_col(df["timestamp"])
        df = df.set_index("timestamp")
    df = df.sort_index()
    need = {"open","high","low","close","volume"}
    if not need.issubset(df.columns):
        raise ValueError("Data must have columns: open, high, low, close, volume (+ timestamp or dt index)")
    if len(df) < (orb_minutes + 2):
        raise ValueError(f"Not enough bars for ORB; need >= {orb_minutes+2}, have {len(df)}")

    orb_df = df.iloc[:orb_minutes]
    orb_high = float(orb_df["high"].max())
    orb_low  = float(orb_df["low"].min())

    pos = Position(); trades = 0
    entry_px = None; exit_px = None; entry_dt: Optional[datetime] = None
    pnl = 0.0

    for i, (ts, row) in enumerate(df.iloc[orb_minutes:].iterrows(), start=orb_minutes):
        prev_qty = pos.qty
        pos, action = orb_strategy_step(i, row, pos, orb_high, orb_low, risk_cents, max_qty)
        close_px = float(row["close"])

        if action and action.startswith("enter_long"):
            trades += 1
            entry_px = close_px
            entry_dt = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts

        elif action and action.startswith("exit_long"):
            trades += 1
            exit_px = close_px
            q_used = prev_qty if isinstance(prev_qty, int) and prev_qty > 0 else (pos.qty if pos.qty else 1)
            if entry_px is not None:
                pnl += (exit_px - entry_px) * q_used
                pnl -= (fees_per_share * q_used) * 2

            try:
                et = entry_dt or (ts.to_pydatetime() if hasattr(ts,"to_pydatetime") else ts)
                log_closed_trade(
                    symbol=symbol, setup="ORB", context_tags=[],
                    entry_time=et, exit_time=(ts.to_pydatetime() if hasattr(ts,"to_pydatetime") else ts),
                    entry=(entry_px if entry_px is not None else close_px), exit=exit_px,
                    qty=int(q_used), fees=float((fees_per_share * q_used) * 2),
                    slippage=0.0, r_multiple=0.0, notes="auto-logged exit",
                    replay_id=f"{symbol}-{str(ts)[:10]}-orb-auto"
                )
            except Exception as _e:
                print(f"[hook] log_closed_trade failed: {_e}")

            pos = Position(); entry_px = None; entry_dt = None

        try:
            if mode == "step":
                input(f"[{ts}] {symbol} close={row['close']:.4f} (Enter=next, Ctrl+C=stop)")
            else:
                time.sleep(max(0.0, 1.0/float(speed if speed>0 else 1.0)))
        except KeyboardInterrupt:
            print(f"[replay] aborted at {ts}")
            break

    last_ts = df.index[-1]; last_close = float(df.iloc[-1]["close"])
    if pos.side == "long" and entry_px is not None:
        q_used = pos.qty if pos.qty else max_qty
        if force_exit:
            pnl += (last_close - entry_px) * q_used
            pnl -= (fees_per_share * q_used)
            try:
                lt = last_ts.to_pydatetime() if hasattr(last_ts,"to_pydatetime") else last_ts
                et = entry_dt or lt
                log_closed_trade(
                    symbol=symbol, setup="ORB", context_tags=[],
                    entry_time=et, exit_time=lt, entry=entry_px, exit=last_close,
                    qty=int(q_used), fees=float(fees_per_share * q_used),
                    slippage=0.0, r_multiple=0.0, notes="force-exit at end",
                    replay_id=f"{symbol}-{str(last_ts)[:10]}-orb-auto"
                )
            except Exception as _e:
                print(f"[hook] final log_closed_trade failed: {_e}")
            pos = Position(); entry_px = None

    return ReplayResult(bars=len(df), trades=trades, pnl=float(round(pnl,2)),
                        entry_px=entry_px, exit_px=exit_px, final_pos=pos)

def load_bars(path: str) -> pd.DataFrame:
    ext = str(path).lower()
    if ext.endswith((".parquet",".pq",".pqt")):
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    return df