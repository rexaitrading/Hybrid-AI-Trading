from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple


@dataclass
class RiskConfig:
    # knobs for halts/caps
    day_loss_cap_pct: float | None = None
    per_trade_notional_cap: float | None = None
    max_trades_per_day: int | None = None
    max_consecutive_losers: int | None = None
    cooldown_bars: int | None = None
    max_drawdown_pct: float | None = None
    state_path: str | None = None
    fail_closed: bool = False
    base_equity_fallback: float | None = None
    # legacy/minimal
    max_daily_loss: float | None = None
    max_portfolio_exposure: float | None = None
    max_leverage: float | None = None
    equity: float | None = None


class RiskManager:
    def __init__(
        self,
        daily_loss_limit: Optional[float] = None,
        max_portfolio_exposure: Optional[float] = None,
        max_leverage: Optional[float] = None,
        equity: Optional[float] = None,
        portfolio: Any = None,
        **kwargs: Any,
    ) -> None:
        self.daily_loss_limit = daily_loss_limit
        self.max_portfolio_exposure = max_portfolio_exposure
        self.max_leverage = max_leverage
        self.equity = equity
        self.portfolio = portfolio

        self.config: Optional[RiskConfig] = kwargs.get("config", None)
        for name in (
            "per_trade_notional_cap",
            "day_loss_cap_pct",
            "max_trades_per_day",
            "max_consecutive_losers",
            "cooldown_bars",
            "max_drawdown_pct",
            "state_path",
            "fail_closed",
            "base_equity_fallback",
        ):
            if getattr(self, name, None) is None and self.config is not None:
                try:
                    setattr(self, name, getattr(self.config, name))
                except Exception:
                    pass

        if getattr(self, "per_trade_notional_cap", None) is None:
            self.per_trade_notional_cap = kwargs.get("per_trade_notional_cap", None)

        # starting equity
        _eq: Optional[float] = None
        try:
            if self.equity is not None:
                _eq = float(self.equity)
        except Exception:
            _eq = None
        if _eq is None and self.portfolio is not None:
            try:
                val = getattr(self.portfolio, "equity", None)
                if val is not None:
                    _eq = float(val)
            except Exception:
                _eq = None
        if _eq is None:
            try:
                _eq = float(getattr(self, "base_equity_fallback", None))
            except Exception:
                _eq = None
        if _eq is not None:
            self.starting_equity = _eq
            if self.equity is None:
                self.equity = _eq

        # intraday state
        self._trades_today: int = 0
        self._loser_streak: int = 0
        self._cooldown_until_ms: int | None = None
        self._last_bar_ts_ms: int | None = None
        self._pnl_today: float = 0.0

        if not hasattr(self, "starting_equity"):
            eq0 = self._resolve_equity()
            if eq0 is not None:
                self.starting_equity = float(eq0)

    # -------- core gate --------
    def approve_trade(
        self, symbol: str, side: str, qty: float, notional: float
    ) -> Tuple[bool, str]:
        # disable knob
        try:
            if (
                self.daily_loss_limit is not None
                and float(self.daily_loss_limit) <= 0.0
            ):
                return False, "daily_loss_limit<=0 disables trading"
        except Exception:
            return False, "invalid_daily_loss_limit"

        eq = self._resolve_equity()

        # per-trade notional cap
        try:
            cap = getattr(self, "per_trade_notional_cap", None)
            if cap is None and self.config is not None:
                cap = getattr(self.config, "per_trade_notional_cap", None)
            if cap is not None and float(notional) > max(0.0, float(cap)):
                return False, "exceeds_per_trade_notional_cap"
        except Exception:
            pass

        # max trades per day
        try:
            mtpd = getattr(self, "max_trades_per_day", None)
            if mtpd is None and self.config is not None:
                mtpd = getattr(self.config, "max_trades_per_day", None)
            if mtpd is not None and self._trades_today >= int(mtpd):
                return False, "max_trades_per_day"
        except Exception:
            pass

        # cooldown
        try:
            if self._cooldown_until_ms is not None:
                now_ms = self._last_bar_ts_ms
                if now_ms is None or int(now_ms) < int(self._cooldown_until_ms):
                    return False, "cooldown_active"
        except Exception:
            pass

        # day loss cap (% of base equity)
        try:
            dl_pct = getattr(self, "day_loss_cap_pct", None)
            if dl_pct is None and self.config is not None:
                dl_pct = getattr(self.config, "day_loss_cap_pct", None)
            if dl_pct is not None:
                base = getattr(self, "starting_equity", None) or (eq or 0.0)
                if base and float(self._pnl_today) <= -abs(float(dl_pct)) * float(base):
                    return False, "day_loss_cap_pct"
        except Exception:
            pass

        # exposure cap
        try:
            mpe = self.max_portfolio_exposure
            if eq is not None and mpe is not None:
                if float(notional) > float(eq) * max(0.0, float(mpe)):
                    return False, "exceeds_max_portfolio_exposure"
        except Exception:
            pass

        # leverage cap
        try:
            ml = self.max_leverage
            if eq not in (None, 0) and ml is not None:
                if (float(notional) / float(eq)) > max(0.0, float(ml)):
                    return False, "exceeds_max_leverage"
        except Exception:
            pass

        # max drawdown
        try:
            dd_pct = getattr(self, "max_drawdown_pct", None)
            if dd_pct is None and self.config is not None:
                dd_pct = getattr(self.config, "max_drawdown_pct", None)
            if dd_pct is not None and hasattr(self, "starting_equity"):
                se = float(self.starting_equity)
                cur = float(eq) if eq is not None else se + float(self._pnl_today)
                if se > 0:
                    dd = max(0.0, (se - cur) / se)
                    if dd >= max(0.0, float(dd_pct)):
                        return False, "max_drawdown_pct"
        except Exception:
            pass

        return True, ""

    def _resolve_equity(self) -> Optional[float]:
        if self.equity is not None:
            try:
                return float(self.equity)
            except Exception:
                return None
        pt = getattr(self, "portfolio", None)
        if pt is not None:
            try:
                val = getattr(pt, "equity", None)
                return float(val) if val is not None else None
            except Exception:
                return None
        try:
            return float(getattr(self, "base_equity_fallback", None))
        except Exception:
            return None

    # -------- events --------
    def on_fill(
        self,
        side: str,
        qty: float,
        px: float,
        bar_ts: int | None = None,
        pnl: float | None = None,
    ) -> None:
        self._trades_today += 1

    def record_close_pnl(self, pnl: float, bar_ts_ms: int | None = None) -> None:
        self._last_bar_ts_ms = bar_ts_ms
        try:
            if pnl is not None:
                self._pnl_today += float(pnl)
        except Exception:
            pass
        try:
            if pnl is not None and float(pnl) < 0.0:
                self._loser_streak += 1
            else:
                self._loser_streak = 0
        except Exception:
            self._loser_streak = 0
        try:
            thr = getattr(self, "max_consecutive_losers", None)
            if thr is None and self.config is not None:
                thr = getattr(self.config, "max_consecutive_losers", None)
            if thr is not None and self._loser_streak >= int(thr):
                bars = getattr(self, "cooldown_bars", None)
                if bars is None and self.config is not None:
                    bars = getattr(self.config, "cooldown_bars", None)
                if bar_ts_ms is not None and bars is not None:
                    self._cooldown_until_ms = int(bar_ts_ms) + int(bars) * 60_000
                else:
                    self._cooldown_until_ms = (bar_ts_ms or 0) + 1
                self._loser_streak = 0
        except Exception:
            pass

    def allow_trade(
        self, notional: float, side: str = "BUY", bar_ts: int | None = None
    ) -> Tuple[bool, str]:
        try:
            if (
                getattr(self, "_cooldown_until_ms", None) is not None
                and bar_ts is not None
            ):
                if int(bar_ts) < int(self._cooldown_until_ms):
                    return False, "COOLDOWN"
        except Exception:
            pass

        try:
            mtd = getattr(self, "max_trades_per_day", None)
            if mtd is None and self.config is not None:
                mtd = getattr(self.config, "max_trades_per_day", None)
            if mtd is None:
                for _k, _v in vars(self).items():
                    if hasattr(_v, "max_trades_per_day"):
                        _mt = getattr(_v, "max_trades_per_day")
                        if _mt is not None:
                            mtd = _mt
                            break
            if mtd is not None and self._trades_today >= int(mtd):
                return False, "TRADES_PER_DAY"
        except Exception:
            if getattr(getattr(self, "config", None), "fail_closed", False):
                return False, "TRADES_PER_DAY"

        try:
            dl = getattr(self, "daily_loss_limit", None)
            if dl is not None and float(dl) <= 0.0:
                return False, "daily_loss_limit<=0 disables trading"
        except Exception:
            pass

        cap = None
        try:
            cfg = getattr(self, "config", None)
            if cfg is not None and hasattr(cfg, "per_trade_notional_cap"):
                cap = cfg.per_trade_notional_cap
        except Exception:
            cap = None
        if cap is None:
            cap = getattr(self, "per_trade_notional_cap", None)
        if cap is None:
            try:
                for _k, _v in vars(self).items():
                    if hasattr(_v, "per_trade_notional_cap"):
                        _val = getattr(_v, "per_trade_notional_cap")
                        if _val is not None:
                            cap = _val
                            break
            except Exception:
                pass
        try:
            if (
                cap is not None
                and notional is not None
                and float(notional) > float(cap)
            ):
                return False, "NOTIONAL_CAP"
        except Exception:
            if getattr(getattr(self, "config", None), "fail_closed", False):
                return False, "invalid_notional_or_cap"

        return True, ""

    # legacy shim
    def check_trade(
        self,
        pnl: float = 0.0,
        trade_notional: float | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> bool:
        fn = getattr(self, "approve_trade", None)
        if callable(fn):
            try:
                notional = trade_notional if trade_notional is not None else 0.0
                res = fn("LEGACY", "BUY", 0.0, notional)
                if isinstance(res, tuple):
                    return bool(res[0])
                if isinstance(res, dict):
                    return str(res.get("status", "")).lower() in (
                        "ok",
                        "allow",
                        "approved",
                        "true",
                        "pass",
                        "filled",
                    )
                return bool(res)
            except Exception:
                return True
        return True

    def reset_day(self) -> dict[str, str]:
        self._trades_today = 0
        self._loser_streak = 0
        self._cooldown_until_ms = None
        self._last_bar_ts_ms = None
        self._pnl_today = 0.0
        return {"status": "ok"}
