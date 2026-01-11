from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List


def local_day() -> str:
    return datetime.now().strftime("%Y%m%d")


@dataclass
class Position:
    qty: float = 0.0
    avg_px: float = 0.0


@dataclass
class CryptoSimState:
    day: str
    cash_usd: float = 10000.0
    equity_usd: float = 10000.0

    # PnL breakdown
    realized_pnl_usd: float = 0.0
    unrealized_pnl_usd: float = 0.0
    fees_paid_usd: float = 0.0  # slippage/fees tracked explicitly

    # Per-symbol realized PnL for daily caps
    realized_by_symbol: Dict[str, float] = None
    fees_by_symbol: Dict[str, float] = None

    # Prices / positions
    last_price: Dict[str, float] = None
    pos: Dict[str, Position] = None

    # Strategy history + trade timestamps for throttling
    hist: Dict[str, list] = None
    trades_ts_by_symbol: Dict[str, List[float]] = None

    last_trade_ts: float = 0.0

    def __post_init__(self):
        if self.last_price is None:
            self.last_price = {}
        if self.pos is None:
            self.pos = {}
        if self.hist is None:
            self.hist = {}
        if self.realized_by_symbol is None:
            self.realized_by_symbol = {}
        if self.fees_by_symbol is None:
            self.fees_by_symbol = {}
        if self.trades_ts_by_symbol is None:
            self.trades_ts_by_symbol = {}


def _pos_to_dict(pos: Dict[str, Position]) -> Dict[str, dict]:
    return {k: asdict(v) for k, v in pos.items()}


def _pos_from_dict(d: Dict[str, dict]) -> Dict[str, Position]:
    out: Dict[str, Position] = {}
    for k, v in (d or {}).items():
        out[k] = Position(qty=float(v.get("qty", 0.0)), avg_px=float(v.get("avg_px", 0.0)))
    return out


def load_state(path: Path) -> CryptoSimState:
    if not path.exists():
        return CryptoSimState(day=local_day())

    obj = json.loads(path.read_text(encoding="utf-8"))
    st = CryptoSimState(
        day=str(obj.get("day", local_day())),
        cash_usd=float(obj.get("cash_usd", 10000.0)),
        equity_usd=float(obj.get("equity_usd", 10000.0)),
        realized_pnl_usd=float(obj.get("realized_pnl_usd", 0.0)),
        unrealized_pnl_usd=float(obj.get("unrealized_pnl_usd", 0.0)),
        fees_paid_usd=float(obj.get("fees_paid_usd", 0.0)),
        last_trade_ts=float(obj.get("last_trade_ts", 0.0)),
    )
    st.last_price = dict(obj.get("last_price", {}) or {})
    st.pos = _pos_from_dict(obj.get("pos", {}) or {})
    st.hist = dict(obj.get("hist", {}) or {})
    st.realized_by_symbol = dict(obj.get("realized_by_symbol", {}) or {})
    st.fees_by_symbol = dict(obj.get("fees_by_symbol", {}) or {})
    st.trades_ts_by_symbol = dict(obj.get("trades_ts_by_symbol", {}) or {})
    return st


def save_state(path: Path, st: CryptoSimState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    obj = asdict(st)
    obj["pos"] = _pos_to_dict(st.pos)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

