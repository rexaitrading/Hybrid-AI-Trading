from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from hybrid_ai_trading.execution.alerts import Alerts
from hybrid_ai_trading.execution.brokers import (
    BinanceClient,
    BrokerClient,
    BrokerError,
    IBKRClient,
    KrakenClient,
)
from hybrid_ai_trading.execution.trade_logger import TradeEvent, TradeLogger
from hybrid_ai_trading.risk.black_swan_guard import BlackSwanGuard
from hybrid_ai_trading.risk.kelly_sizer import KellySizer
from hybrid_ai_trading.risk.risk_manager import RiskManager
from hybrid_ai_trading.signals.eth1h_alpha import eth1h_signal

try:
    import ccxt
except ImportError:
    ccxt = None  # type: ignore


@dataclass
class RunnerConfig:
    exchange: str = "binance"  # "binance" or "kraken"
    symbol: str = "ETH/USDT"  # Kraken prefers "ETH/USD"
    tf: str = "1h"
    limit: int = 1000
    base_capital: float = 10000.0
    kelly_fraction: float = 0.5
    broker: str = "binance"  # "binance" | "kraken" | "ibkr"
    ibkr_asset_class: str = "CRYPTO"
    paper: bool = True
    virtual_fills: bool = True
    allow_shorts: bool = True
    fee_bps: float = 10.0  # total both-sides bps
    slip_bps: float = 5.0  # bps
    cooldown_bars: int = 1
    trailing_k_atr: float = 2.0
    time_stop_bars: int = 24


class ETH1HRunner:
    def __init__(
        self,
        cfg: RunnerConfig,
        risk: RiskManager,
        kelly: KellySizer,
        bsg: BlackSwanGuard,
        logger: TradeLogger,
    ):
        self.cfg = cfg
        self.risk = risk
        self.kelly = kelly
        self.bsg = bsg
        self.logger = logger
        self.alerts = Alerts()
        key = f"eth1h_{self.cfg.exchange}_{self._norm_symbol(self.cfg.symbol).replace('/', '-')}"
        self.state_path = os.path.join("logs", f"{key}_state.json")
        self.pos_path = os.path.join("logs", f"{key}_pos.json")
        self.broker: Optional[BrokerClient] = None
        if not self.cfg.virtual_fills:
            self.broker = self._make_broker()

    def _norm_symbol(self, sym: str) -> str:
        if self.cfg.exchange == "kraken" and sym.endswith("USDT"):
            sym = sym.replace("USDT", "USD")
        return sym

    def _make_broker(self) -> BrokerClient:
        if self.cfg.broker == "binance":
            return BinanceClient()
        if self.cfg.broker == "kraken":
            return KrakenClient()
        if self.cfg.broker == "ibkr":
            return IBKRClient(asset_class=self.cfg.ibkr_asset_class)
        raise BrokerError(f"Unsupported broker={self.cfg.broker}")

    def _fetch_ohlcv(self) -> List[List[float]]:
        if ccxt is None:
            raise RuntimeError("ccxt not installed")
        ex = ccxt.kraken() if self.cfg.exchange == "kraken" else ccxt.binance()
        ex.load_markets()
        symbol = self._norm_symbol(self.cfg.symbol)
        return ex.fetch_ohlcv(symbol, timeframe=self.cfg.tf, limit=self.cfg.limit)

    def _signal_from_bars(self, bars: List[List[float]]) -> Optional[str]:
        try:
            return eth1h_signal(bars)
        except Exception:
            return None

    def _position_size(self, side: str, px: float) -> float:
        total_bps = max(0.0, self.cfg.fee_bps + self.cfg.slip_bps)
        bps = total_bps / 10_000.0
        eff_px = px * (1.0 + bps) if side == "BUY" else px * (1.0 - bps)
        k = max(0.0, min(self.cfg.kelly_fraction, 1.0))
        notional = self.cfg.base_capital * k
        qty = max(0.0, math.floor((notional / eff_px) * 1000) / 1000)
        return qty

    def _load_state(self) -> Dict[str, Any]:
        try:
            if os.path.exists(self.state_path):
                with open(self.state_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_state(self, last_ts: int) -> None:
        os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
        try:
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump({"last_ts": last_ts}, f)
        except Exception:
            pass

    def _pos_load(self) -> Optional[Dict[str, Any]]:
        try:
            if os.path.exists(self.pos_path):
                with open(self.pos_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return None

    def _pos_save(self, pos: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self.pos_path), exist_ok=True)
        try:
            with open(self.pos_path, "w", encoding="utf-8") as f:
                json.dump(pos, f)
        except Exception:
            pass

    def _pos_clear(self) -> None:
        try:
            if os.path.exists(self.pos_path):
                os.remove(self.pos_path)
        except Exception:
            pass

    @staticmethod
    def _atr_last(
        highs: List[float], lows: List[float], closes: List[float], period: int = 14
    ) -> Optional[float]:
        n = len(closes)
        if n < period + 1:
            return None
        trs = []
        for i in range(n - period, n):
            prev_close = closes[i - 1]
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - prev_close),
                abs(lows[i] - prev_close),
            )
            trs.append(tr)
        return sum(trs) / float(period)

    def _realized_pnl(
        self, side: str, qty: float, entry_px: float, exit_px: float
    ) -> float:
        raw = (
            (exit_px - entry_px) * qty if side == "BUY" else (entry_px - exit_px) * qty
        )
        fee_rate = max(0.0, self.cfg.fee_bps) / 10_000.0
        avg_px = 0.5 * (entry_px + exit_px)
        fees = fee_rate * qty * avg_px
        return raw - fees

    def _alert_ctx(self) -> Dict[str, Any]:
        return {
            "strategy": "ETH1H",
            "exchange": self.cfg.exchange,
            "broker": (
                "virtual"
                if self.cfg.virtual_fills
                else (self.broker.name if self.broker else "unknown")
            ),
            "symbol": self._norm_symbol(self.cfg.symbol),
        }

    def step(self):
        bars = self._fetch_ohlcv()
        if not bars:
            return None

        last_ts = int(bars[-1][0])
        state = self._load_state()
        if state.get("last_ts") == last_ts:
            return None  # already traded this bar

        closes = [float(b[4]) for b in bars if b[4] is not None]
        highs = [float(b[2]) for b in bars if b[2] is not None]
        lows = [float(b[3]) for b in bars if b[3] is not None]
        last_px = float(closes[-1])

        force = os.getenv("FORCE_TRADE", "").upper()
        force_close = os.getenv("FORCE_CLOSE", "")
        pos = self._pos_load()

        atr14 = self._atr_last(highs, lows, closes, 14)
        exit_reason = None
        if pos:
            if pos["side"] == "BUY":
                pos["peak"] = float(max(pos.get("peak", last_px), last_px))
                if atr14 is not None and last_px < (
                    pos["peak"] - self.cfg.trailing_k_atr * atr14
                ):
                    exit_reason = "TRAIL"
            else:
                pos["trough"] = float(min(pos.get("trough", last_px), last_px))
                if atr14 is not None and last_px > (
                    pos["trough"] + self.cfg.trailing_k_atr * atr14
                ):
                    exit_reason = "TRAIL"
            if exit_reason is None and isinstance(pos.get("opened_bar_ts"), int):
                if (
                    last_ts - int(pos["opened_bar_ts"])
                    >= self.cfg.time_stop_bars * 3600_000
                ):
                    exit_reason = "TIME"

        side = force if force in ("BUY", "SELL") else self._signal_from_bars(bars)
        if pos and exit_reason is None and side and side != pos["side"]:
            exit_reason = "OPPOSITE"
        if pos and not exit_reason and force_close:
            exit_reason = "FORCE_CLOSE"

        if pos and exit_reason:
            realized = self._realized_pnl(
                pos["side"], float(pos["qty"]), float(pos["avg_px"]), last_px
            )
            prev = TradeEvent(
                ts=self.logger._now_iso(),
                strategy="ETH1H",
                broker=(
                    "virtual"
                    if self.cfg.virtual_fills
                    else (self.broker.name if self.broker else "unknown")
                ),
                symbol=self._norm_symbol(self.cfg.symbol),
                side=pos["side"],
                qty=float(pos["qty"]),
                px=last_px,
                order_type="MARKET",
                order_id=pos.get("order_id"),
                status="filled",
                pnl=None,
                meta={
                    "reason": exit_reason,
                    "fee_bps": self.cfg.fee_bps,
                    "slip_bps": self.cfg.slip_bps,
                    "bar_ts": last_ts,
                },
                risk=self.risk.snapshot(),
            )
            closed = self.logger.close_event(
                prev, realized_pnl=realized, meta=prev.meta
            )
            self.risk.record_close_pnl(realized, bar_ts_ms=last_ts)
            self.alerts.notify(
                "closed",
                {
                    **self._alert_ctx(),
                    "side": pos["side"],
                    "qty": float(pos["qty"]),
                    "px": last_px,
                    "pnl": round(realized, 6),
                    "reason": exit_reason,
                    "status": "closed",
                    "bar_ts": last_ts,
                },
            )
            self._pos_clear()
            self._save_state(last_ts)
            return closed

        if not side:
            return None
        if side == "SELL" and not getattr(self.cfg, "allow_shorts", True):
            return None
        if pos:
            return None

        px = last_px
        qty = self._position_size(side, px)
        if qty <= 0:
            return None

        notional = float(qty) * float(px)
        ok, reason = self.risk.allow_trade(notional=notional, side=side, bar_ts=last_ts)
        if not ok:
            self.alerts.notify(
                "risk_halt",
                {
                    **self._alert_ctx(),
                    "reason": reason,
                    "status": "blocked",
                    "bar_ts": last_ts,
                },
            )
            return None

        meta_extra = {
            "fee_bps": self.cfg.fee_bps,
            "slip_bps": self.cfg.slip_bps,
            "bar_ts": last_ts,
        }

        sub = self.logger.submit_event(
            strategy="ETH1H",
            broker=(
                "virtual"
                if self.cfg.virtual_fills
                else (self.broker.name if self.broker else "unknown")
            ),
            symbol=self._norm_symbol(self.cfg.symbol),
            side=side,
            qty=qty,
            px=px,
            order_type="MARKET",
            risk=self.risk.snapshot(),
            meta=meta_extra,
        )
        self.alerts.notify(
            "submitted",
            {
                **self._alert_ctx(),
                "side": side,
                "qty": qty,
                "px": px,
                "status": "submitted",
                "bar_ts": last_ts,
            },
        )

        if self.cfg.virtual_fills:
            oid, meta = (
                "virtual",
                {
                    "status": "filled",
                    "fills": [{"px": px, "qty": qty}],
                    **meta_extra,
                },
            )
            filled_px = px
        else:
            oid, meta = self.broker.submit_order(
                self._norm_symbol(self.cfg.symbol), side, qty, "MARKET", meta=meta_extra
            )
            filled_px = (
                meta.get("fills", [{}])[-1].get("px", px)
                if isinstance(meta, dict)
                else px
            )

        fill = self.logger.fill_event(sub, px_fill=filled_px, order_id=oid, meta=meta)
        self.risk.on_fill(side=side, qty=qty, px=filled_px, bar_ts=last_ts)
        self.alerts.notify(
            "filled",
            {
                **self._alert_ctx(),
                "side": side,
                "qty": qty,
                "px": filled_px,
                "status": "filled",
                "bar_ts": last_ts,
            },
        )

        pos_new = {
            "side": side,
            "qty": float(qty),
            "avg_px": float(filled_px),
            "opened_bar_ts": last_ts,
        }
        if side == "BUY":
            pos_new["peak"] = float(filled_px)
        else:
            pos_new["trough"] = float(filled_px)
        self._pos_save(pos_new)

        self._save_state(last_ts)
        return fill
