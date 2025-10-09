from __future__ import annotations
import json, csv, os, logging
from logging.handlers import RotatingFileHandler
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any
from hybrid_ai_trading.utils.time_utils import utc_now

@dataclass
class TradeEvent:
    ts: str
    strategy: str
    broker: str
    symbol: str
    side: str
    qty: float
    px: float
    order_type: str
    order_id: Optional[str] = None
    status: str = "submitted"  # submitted/filled/partial/closed/canceled/rejected
    pnl: Optional[float] = None
    meta: Optional[Dict[str, Any]] = None
    risk: Optional[Dict[str, Any]] = None

class TradeLogger:
    def __init__(self, jsonl_path: str = "logs/trades.jsonl",
                 csv_path: Optional[str] = "logs/trades.csv",
                 text_log_path: str = "logs/trades.log",
                 max_bytes: int = 2_000_000, backup_count: int = 5) -> None:
        os.makedirs(os.path.dirname(jsonl_path), exist_ok=True)
        self.jsonl_path = jsonl_path
        self.csv_path = csv_path
        self._logger = logging.getLogger("hybrid_ai_trading.trade_logger")
        self._logger.setLevel(logging.INFO)
        if not self._logger.handlers:
            rh = RotatingFileHandler(text_log_path, maxBytes=max_bytes, backupCount=backup_count)
            fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
            rh.setFormatter(fmt)
            self._logger.addHandler(rh)
        if self.csv_path and not os.path.exists(self.csv_path):
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["ts","strategy","broker","symbol","side","qty","px","order_type","order_id","status","pnl","meta","risk"])

    @staticmethod
    def _now_iso() -> str:
        return utc_now().replace(microsecond=0).isoformat() + "Z"

    def log(self, event: TradeEvent) -> None:
        with open(self.jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event), separators=(",", ":")) + "\n")
        if self.csv_path:
            with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow([
                    event.ts,event.strategy,event.broker,event.symbol,event.side,
                    event.qty,event.px,event.order_type,event.order_id,event.status,
                    event.pnl,json.dumps(event.meta or {}),json.dumps(event.risk or {})
                ])
        self._logger.info(
            "trade | %s | %s | %s | %s %.6f @ %.6f | %s | id=%s | status=%s",
            event.strategy,event.broker,event.symbol,event.side,event.qty,event.px,event.order_type,event.order_id,event.status
        )

    def submit_event(self, strategy: str, broker: str, symbol: str, side: str, qty: float, px: float,
                     order_type: str, meta: Optional[Dict[str, Any]]=None, risk: Optional[Dict[str, Any]]=None) -> TradeEvent:
        ev = TradeEvent(ts=self._now_iso(), strategy=strategy, broker=broker, symbol=symbol,
                        side=side, qty=qty, px=px, order_type=order_type, status="submitted", meta=meta, risk=risk)
        self.log(ev); return ev

    def fill_event(self, prev: TradeEvent, px_fill: float, order_id: Optional[str], meta: Optional[Dict[str, Any]]=None) -> TradeEvent:
        ev = TradeEvent(ts=self._now_iso(), strategy=prev.strategy, broker=prev.broker, symbol=prev.symbol,
                        side=prev.side, qty=prev.qty, px=px_fill, order_type=prev.order_type,
                        order_id=order_id, status="filled", meta=meta, risk=prev.risk)
        self.log(ev); return ev

    def status_event(self, prev: TradeEvent, status: str, meta: Optional[Dict[str, Any]]=None, pnl: Optional[float]=None) -> TradeEvent:
        ev = TradeEvent(ts=self._now_iso(), strategy=prev.strategy, broker=prev.broker, symbol=prev.symbol,
                        side=prev.side, qty=prev.qty, px=prev.px, order_type=prev.order_type,
                        order_id=prev.order_id, status=status, pnl=pnl, meta=meta, risk=prev.risk)
        self.log(ev); return ev

    def close_event(self, prev: TradeEvent, realized_pnl: float, meta: Optional[Dict[str, Any]]=None) -> TradeEvent:
        return self.status_event(prev, status="closed", meta=meta, pnl=realized_pnl)