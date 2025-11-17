from __future__ import annotations

import math
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple

import pandas as pd

from hybrid_ai_trading.tools.replay_logger_hook import log_closed_trade
from hybrid_ai_trading.replay_gatescore import compute_session_gatescore


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
    gatescore: Optional[Dict[str, float]] = None

def load_bars(csv_path: str):
    """
    Simple bar loader for replay / backtest helpers.

    Expects a CSV file path and returns a pandas DataFrame that run_replay can consume.
    """
    import pandas as pd  # type: ignore[import]
    return pd.read_csv(csv_path)

from hybrid_ai_trading.gatescore_bar import BarGateInput, compute_bar_gatescore


def compute_bar_gatescore_for_row(
    df,
    idx: int,
    symbol: str,
    side: str,
    orb_trigger: bool,
    expected_edge: float,
    qty: float,
    spread: float,
    vwap_col: str = "vwap",
    price_col: str = "close",
    volume_col: str = "volume",
    window: int = 5,
    risk_ok: bool = True,
    qos_ok: bool = True,
):
    """
    Convenience helper to compute GateScore for a single replay bar.

    This is the conceptual hook for your ORB/VWAP strategy:

        - df           : pandas DataFrame with at least price_col, volume_col (and optionally vwap_col)
        - idx          : integer row index of the decision bar
        - symbol       : trading symbol, e.g. "AAPL"
        - side         : "BUY" or "SELL"
        - orb_trigger  : True if your ORB condition is met on this bar
        - expected_edge: expected PnL (currency units) for this trade idea
        - qty          : trade size
        - spread       : full bid-ask spread (price units)
        - vwap_col     : name of VWAP column in df (if present)
        - price_col    : name of close/price column
        - volume_col   : name of volume column
        - window       : number of bars (including idx) in microstructure window
        - risk_ok      : result of your risk checks
        - qos_ok       : result of your provider QoS checks

    Returns BarGateOutput from gatescore_bar.compute_bar_gatescore.
    """
    # Build microstructure window
    start = max(0, int(idx) - int(window) + 1)
    closes_window = [float(x) for x in df[price_col].iloc[start : idx + 1]]
    volumes_window = [float(x) for x in df[volume_col].iloc[start : idx + 1]]

    if not closes_window:
        raise ValueError("compute_bar_gatescore_for_row: closes_window is empty; check idx/window/data range")

    price = float(df[price_col].iloc[idx])

    # VWAP distance
    vwap_value = 0.0
    if vwap_col in df.columns:
        try:
            vwap_value = float(df[vwap_col].iloc[idx])
        except Exception:
            vwap_value = 0.0

    vwap_distance = 0.0
    if vwap_value:
        vwap_distance = (price - vwap_value) / vwap_value

    bi = BarGateInput(
        symbol=symbol,
        side=side,
        orb_trigger=orb_trigger,
        vwap_distance=vwap_distance,
        closes_window=closes_window,
        volumes_window=volumes_window,
        expected_edge=expected_edge,
        qty=qty,
        spread=spread,
        risk_ok=risk_ok,
        qos_ok=qos_ok,
    )

    return compute_bar_gatescore(bi)
