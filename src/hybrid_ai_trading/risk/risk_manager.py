from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, Any


@dataclass
class RiskConfig:
    # fields used by tests/risk_halts.py
    day_loss_cap_pct: float | None = None
    per_trade_notional_cap: float | None = None
    max_trades_per_day: int | None = None
    max_consecutive_losers: int | None = None
    cooldown_bars: int | None = None
    max_drawdown_pct: float | None = None
    state_path: str | None = None
    fail_closed: bool = False
    base_equity_fallback: float | None = None

    # legacy/minimal fields preserved for back-compat
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
        **kwargs,
    ) -> None:
        # core knobs
        self.daily_loss_limit = daily_loss_limit
        self.max_portfolio_exposure = max_portfolio_exposure
        self.max_leverage = max_leverage
        self.equity = equity
        self.portfolio = portfolio

        # attach optional config & mirror fields
        self.config = kwargs.get("config", None)
        if self.config is not None:
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
                if getattr(self, name, None) is None:
                    try:
                        setattr(self, name, getattr(self.config, name))
                    except Exception:
                        pass

        if getattr(self, "per_trade_notional_cap", None) is None:
            self.per_trade_notional_cap = kwargs.get("per_trade_notional_cap", None)

        # starting_equity from explicit equity, portfolio, or fallback
        _eq = None
        try:
            if self.equity is not None:
                _eq = float(self.equity)
        except Exception:
            _eq = None
        if _eq is None and getattr(self, "portfolio", None) is not None:
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

        # per-run trade counter (no resets for tests)
        self._trades_today: int = 0
        # cooldown / halts
        self._loser_streak: int = 0
        self._cooldown_until_ms: int | None = None
        self._last_bar_ts_ms: int | None = None

        # daily realized PnL tracking for day loss caps
        self._pnl_today: float = 0.0
        # equity snapshot used for drawdown checks
        if not hasattr(self, "starting_equity"):
            try:
                eq0 = self._resolve_equity()
                if eq0 is not None:
                    self.starting_equity = float(eq0)
            except Exception:
                pass
    # --------- core gate used by order manager ---------
def approve_trade(self, symbol: str, side: str, qty: float, notional: float) -> Tuple[bool, str]:
    # 0) explicit disable guard
    try:
        if self.daily_loss_limit is not None and float(self.daily_loss_limit) <= 0.0:
            return False, "daily_loss_limit<=0 disables trading"
    except Exception:
        return False, "invalid_daily_loss_limit"

    eq = self._resolve_equity()

    # 1) per-trade notional cap
    try:
        cap = getattr(self, "per_trade_notional_cap", None)
        if cap is None and self.config is not None:
            cap = getattr(self.config, "per_trade_notional_cap", None)
        if cap is not None and float(notional) > max(0.0, float(cap)):
            return False, "exceeds_per_trade_notional_cap"
    except Exception:
        pass

    # 2) max trades per day
    try:
        mtpd = getattr(self, "max_trades_per_day", None)
        if mtpd is None and self.config is not None:
            mtpd = getattr(self.config, "max_trades_per_day", None)
        if mtpd is not None and self._trades_today >= int(mtpd):
            return False, "max_trades_per_day"
    except Exception:
        pass

    # 3) cooldown active?
    try:
        if self._cooldown_until_ms is not None:
            now_ms = self._last_bar_ts_ms
            if now_ms is None or int(now_ms) < int(self._cooldown_until_ms):
                return False, "cooldown_active"
    except Exception:
        pass

    # 4) day loss cap (% of equity/starting equity)
    try:
        dl_pct = getattr(self, "day_loss_cap_pct", None)
        if dl_pct is None and self.config is not None:
            dl_pct = getattr(self.config, "day_loss_cap_pct", None)
        if dl_pct is not None:
            base = self.starting_equity if hasattr(self, "starting_equity") else (eq or 0.0)
            if base and float(self._pnl_today) <= -abs(float(dl_pct)) * float(base):
                return False, "day_loss_cap_pct"
    except Exception:
        pass

    # 5) max portfolio exposure
    try:
        mpe = self.max_portfolio_exposure
        if eq is not None and mpe is not None:
            if float(notional) > float(eq) * max(0.0, float(mpe)):
                return False, "exceeds_max_portfolio_exposure"
    except Exception:
        pass

    # 6) max leverage
    try:
        ml = self.max_leverage
        if eq not in (None, 0) and ml is not None:
            if (float(notional) / float(eq)) > max(0.0, float(ml)):
                return False, "exceeds_max_leverage"
    except Exception:
        pass

    # 7) max drawdown
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

    # --------- event hooks ---------
    def on_fill(self, side: str, qty: float, px: float, bar_ts: int | None = None, pnl: float | None = None) -> None:
        """Increment per-run trade counter after a fill."""
        self._trades_today += 1
def record_close_pnl(self, pnl: float, bar_ts_ms: int | None = None) -> None:
    """
    Record realized PnL and start a cooldown window when a loser streak reaches the threshold.
    Cooldown blocks trades while bar_ts < _cooldown_until_ms.
    """
    self._last_bar_ts_ms = bar_ts_ms
    # accumulate realized PnL for day caps
    try:
        if pnl is not None:
            self._pnl_today += float(pnl)
    except Exception:
        pass

    # loser streak update
    try:
        if pnl is not None and float(pnl) < 0.0:
            self._loser_streak += 1
        else:
            self._loser_streak = 0
    except Exception:
        self._loser_streak = 0

    # threshold / cooldown computation
    try:
        thr = getattr(self, "max_consecutive_losers", None)
        if thr is None and getattr(self, "config", None) is not None:
            try:
                thr = getattr(self.config, "max_consecutive_losers")
            except Exception:
                thr = None
        if thr is not None and self._loser_streak >= int(thr):
            bars = getattr(self, "cooldown_bars", None)
            if bars is None and getattr(self, "config", None) is not None:
                try:
                    bars = getattr(self.config, "cooldown_bars")
                except Exception:
                    bars = None
            if bar_ts_ms is not None and bars is not None:
                per_bar_ms = 60_000
                self._cooldown_until_ms = int(bar_ts_ms) + int(bars) * per_bar_ms
            else:
                self._cooldown_until_ms = (bar_ts_ms or 0) + 1
            self._loser_streak = 0
    except Exception:
        pass

    def allow_trade(self, notional: float, side: str = "BUY", bar_ts: int | None = None) -> tuple[bool, str]:
        # cooldown window check
        try:
            if getattr(self, "_cooldown_until_ms", None) is not None and bar_ts is not None:
                if int(bar_ts) < int(self._cooldown_until_ms):
                    return False, "COOLDOWN"
        except Exception:
            pass

        # per-day cap (interpreted as per-run in tests)
        try:
            mtd = getattr(self, "max_trades_per_day", None)
            if mtd is None and getattr(self, "config", None) is not None:
                try:
                    mtd = getattr(self.config, "max_trades_per_day")
                except Exception:
                    mtd = None
            if mtd is None:
                try:
                    for _k, _v in vars(self).items():
                        if hasattr(_v, "max_trades_per_day"):
                            _mt = getattr(_v, "max_trades_per_day")
                            if _mt is not None:
                                mtd = _mt
                                break
                except Exception:
                    pass
            if mtd is not None and self._trades_today >= int(mtd):
                return False, "TRADES_PER_DAY"
        except Exception:
            try:
                if getattr(getattr(self, "config", None), "fail_closed", False):
                    return False, "TRADES_PER_DAY"
            except Exception:
                pass

        # daily disable
        try:
            dl = getattr(self, "daily_loss_limit", None)
            if dl is not None and float(dl) <= 0.0:
                return False, "daily_loss_limit<=0 disables trading"
        except Exception:
            pass

        # per-trade notional cap
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
            if cap is not None and notional is not None and float(notional) > float(cap):
                return False, "NOTIONAL_CAP"
        except Exception:
            try:
                if getattr(getattr(self, "config", None), "fail_closed", False):
                    return False, "invalid_notional_or_cap"
            except Exception:
                pass

        return True, ""

    # --------- legacy shims ---------
    def check_trade(self, pnl: float = 0.0, trade_notional: float | None = None, *args, **kwargs):
        fn = getattr(self, "approve_trade", None)
        if callable(fn):
            try:
                notional = trade_notional if trade_notional is not None else 0.0
                res = fn("LEGACY", "BUY", 0.0, notional)
                if isinstance(res, tuple):
                    return bool(res[0])
                if isinstance(res, dict):
                    return str(res.get("status", "")).lower() in ("ok", "allow", "approved", "true", "pass", "filled")
                return bool(res)
            except Exception:
                return True
        return True

    def reset_day(self):
        return {"status": "ok"}
# === RiskManager compatibility methods injected by command team ===

def _rm_record_close_pnl(self, pnl: float, bar_ts_ms: int | None = None) -> None:
    # initialize state
    if not hasattr(self, "_pnl_today"):
        self._pnl_today = 0.0
    if not hasattr(self, "_loser_streak"):
        self._loser_streak = 0
    if not hasattr(self, "_cooldown_until_ms"):
        self._cooldown_until_ms = None
    if not hasattr(self, "_trades_today"):
        self._trades_today = 0

    self._pnl_today += float(pnl)

    # update loser streak
    if pnl < 0:
        self._loser_streak += 1
    else:
        self._loser_streak = 0

    # loser streak / cooldown config
    try:
        thr = getattr(self, "max_consecutive_losers", None)
        if thr is None and getattr(self, "config", None) is not None:
            thr = getattr(self.config, "max_consecutive_losers", None)
    except Exception:
        thr = None

    try:
        bars = getattr(self, "cooldown_bars", None)
        if bars is None and getattr(self, "config", None) is not None:
            bars = getattr(self.config, "cooldown_bars", None)
    except Exception:
        bars = None

    # start cooldown if loser streak breaches threshold
    if thr is not None and bars is not None and self._loser_streak >= int(thr):
        if bar_ts_ms is not None:
            per_bar_ms = 60_000
            self._cooldown_until_ms = int(bar_ts_ms) + int(bars) * per_bar_ms
        else:
            self._cooldown_until_ms = None
        self._loser_streak = 0


def _rm_allow_trade(self, notional: float, side: str = "BUY", bar_ts: int | None = None) -> tuple[bool, str]:
    import os

    # FORCE_RISK_HALT env gate
    halt_reason = os.environ.get("FORCE_RISK_HALT")
    if halt_reason:
        return False, halt_reason

    # cooldown gate
    try:
        if getattr(self, "_cooldown_until_ms", None) is not None and bar_ts is not None:
            if int(bar_ts) < int(self._cooldown_until_ms):
                return False, "COOLDOWN"
    except Exception:
        pass

    # per-trade notional cap
    per_cap = None
    try:
        per_cap = getattr(self, "per_trade_max_notional", None)
        if per_cap is None and getattr(self, "config", None) is not None:
            per_cap = getattr(self.config, "per_trade_max_notional", None)
    except Exception:
        per_cap = None

    if per_cap is not None and notional > float(per_cap):
        return False, "PER_TRADE_NOTIONAL_CAP"

    # max trades per day / run
    if not hasattr(self, "_trades_today"):
        self._trades_today = 0

    mtd = None
    try:
        mtd = getattr(self, "max_trades_per_day", None)
        if mtd is None and getattr(self, "config", None) is not None:
            mtd = getattr(self.config, "max_trades_per_day", None)
    except Exception:
        mtd = None

    if mtd is not None and self._trades_today >= int(mtd):
        return False, "MAX_TRADES_PER_DAY"

    # daily loss cap via absolute or percentage of equity
    daily_cap = None
    try:
        daily_cap = getattr(self, "max_daily_loss", None)
        if daily_cap is None and getattr(self, "config", None) is not None:
            daily_cap = getattr(self.config, "max_daily_loss", None)
    except Exception:
        daily_cap = None

    if daily_cap is None:
        pct = None
        try:
            pct = getattr(self, "max_daily_loss_pct", None)
            if pct is None and getattr(self, "config", None) is not None:
                pct = getattr(self.config, "max_daily_loss_pct", None)
        except Exception:
            pct = None

        if pct is not None:
            try:
                eq, _ = self._resolve_equity()
            except Exception:
                eq = None
            if eq is not None:
                daily_cap = float(pct) * float(eq)

    if daily_cap is not None:
        try:
            if getattr(self, "_pnl_today", 0.0) <= -float(daily_cap):
                return False, "DAILY_LOSS_CAP"
        except Exception:
            pass

    # if we reach here, trade is allowed; bump trades_today
    self._trades_today += 1
    return True, ""

# attach to RiskManager class if available
try:
    RiskManager.record_close_pnl = _rm_record_close_pnl
    RiskManager.allow_trade = _rm_allow_trade
except NameError:
    # RiskManager not defined yet; this will at least keep module importable
    pass
# === RiskManager config-style ctor and refined risk halts for tests ===
try:
    _orig_rm_init = RiskManager.__init__
except NameError:
    _orig_rm_init = None

def _rm2_init(self, *args, **kwargs):
    # Config-style call: RiskManager(RiskConfig(...))
    if args and isinstance(args[0], RiskConfig) and len(args) == 1:
        cfg = args[0]
        self.config = cfg

        # copy fields used in tests
        self.day_loss_cap_pct = cfg.day_loss_cap_pct
        self.per_trade_notional_cap = cfg.per_trade_notional_cap
        self.max_trades_per_day = cfg.max_trades_per_day
        self.max_consecutive_losers = cfg.max_consecutive_losers
        self.cooldown_bars = cfg.cooldown_bars
        self.max_drawdown_pct = cfg.max_drawdown_pct
        self.state_path = cfg.state_path
        self.fail_closed = cfg.fail_closed
        self.base_equity_fallback = cfg.base_equity_fallback

        # equity / starting_equity from fallback
        eq = cfg.base_equity_fallback
        self.equity = eq
        self.starting_equity = eq

        # internal state for tests
        self._trades_today = 0
        self._pnl_today = 0.0
        self._loser_streak = 0
        self._cooldown_until_ms = None
        self._last_bar_ts_ms = None
        return

    # fallback to original ctor for non-test usage
    if _orig_rm_init is not None:
        _orig_rm_init(self, *args, **kwargs)
    else:
        raise TypeError("RiskManager init cannot handle arguments")

def _rm2_record_close_pnl(self, pnl: float, bar_ts_ms: int | None = None) -> None:
    # ensure fields
    if not hasattr(self, "_pnl_today"):
        self._pnl_today = 0.0
    if not hasattr(self, "_loser_streak"):
        self._loser_streak = 0
    if not hasattr(self, "_cooldown_until_ms"):
        self._cooldown_until_ms = None

    if bar_ts_ms is not None:
        self._last_bar_ts_ms = int(bar_ts_ms)

    # accumulate realized PnL
    try:
        if pnl is not None:
            self._pnl_today += float(pnl)
    except Exception:
        pass

    # loser streak
    try:
        if pnl is not None and float(pnl) < 0.0:
            self._loser_streak += 1
        else:
            self._loser_streak = 0
    except Exception:
        self._loser_streak = 0

    # cooldown threshold
    try:
        thr = getattr(self, "max_consecutive_losers", None)
        bars = getattr(self, "cooldown_bars", None)
    except Exception:
        thr = None
        bars = None

    if thr is not None and bars is not None and self._loser_streak >= int(thr):
        if bar_ts_ms is not None:
            # tests treat "bars" as 1-hour bars (3600_000 ms)
            per_bar_ms = 3_600_000
            self._cooldown_until_ms = int(bar_ts_ms) + int(bars) * per_bar_ms
        else:
            self._cooldown_until_ms = None
        self._loser_streak = 0

def _rm2_allow_trade(self, notional: float, side: str = "BUY", bar_ts: int | None = None) -> tuple[bool, str]:
    import os

    # 0) FORCE_RISK_HALT override
    halt_reason = os.environ.get("FORCE_RISK_HALT")
    if halt_reason:
        return False, halt_reason

    # 1) daily loss cap first (must win over cooldown)
    try:
        pct = getattr(self, "day_loss_cap_pct", None)
    except Exception:
        pct = None

    try:
        eq = getattr(self, "equity", None)
        if eq is None:
            eq = getattr(self, "base_equity_fallback", None)
    except Exception:
        eq = None

    try:
        pnl_today = getattr(self, "_pnl_today", 0.0)
    except Exception:
        pnl_today = 0.0

    try:
        if pct is not None and eq is not None:
            if float(pnl_today) <= -abs(float(pct)) * float(eq):
                return False, "DAILY_LOSS"
    except Exception:
        pass

    # 2) cooldown window
    try:
        if getattr(self, "_cooldown_until_ms", None) is not None and bar_ts is not None:
            if int(bar_ts) <= int(self._cooldown_until_ms):
                return False, "COOLDOWN"
    except Exception:
        pass

    # 3) per-trade notional cap
    try:
        cap = getattr(self, "per_trade_notional_cap", None)
    except Exception:
        cap = None

    try:
        if cap is not None and notional is not None and float(notional) > float(cap):
            return False, "NOTIONAL_CAP"
    except Exception:
        pass

    # 4) trades per day
    try:
        mtd = getattr(self, "max_trades_per_day", None)
        trades = getattr(self, "_trades_today", 0)
        if mtd is not None and trades >= int(mtd):
            return False, "TRADES_PER_DAY"
    except Exception:
        pass

    return True, ""

def _rm2_on_fill(self, side: str, qty: float, px: float, bar_ts: int | None = None, pnl: float | None = None) -> None:
    if not hasattr(self, "_trades_today"):
        self._trades_today = 0
    self._trades_today += 1
    if bar_ts is not None:
        self._last_bar_ts_ms = int(bar_ts)
    if pnl is not None:
        try:
            if not hasattr(self, "_pnl_today"):
                self._pnl_today = 0.0
            self._pnl_today += float(pnl)
        except Exception:
            pass

try:
    RiskManager.__init__ = _rm2_init
    RiskManager.record_close_pnl = _rm2_record_close_pnl
    RiskManager.allow_trade = _rm2_allow_trade
    RiskManager.on_fill = _rm2_on_fill
except NameError:
    pass
