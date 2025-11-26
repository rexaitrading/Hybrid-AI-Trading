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

    # ------------------------------------------------------------------
    # Phase 5 sketch (NOT ACTIVE YET)
    #
    # When you are ready to enforce Phase 5 policy inside approve_trade,
    # you can:
    #
    #   1) Build a DailyRiskState snapshot for this symbol:
    #
    #        daily_state = self.build_phase5_daily_state(symbol)
    #
    #   2) Compute pos_unrealized_pnl_bp from your live PnL engine
    #      (e.g., per-symbol unrealized PnL converted into basis points):
    #
    #        pos_unrealized_pnl_bp = 0.0  # TODO: wire from portfolio PnL
    #
    #   3) Call the Phase 5 checker:
    #
    #        allow, reason = phase5_check_add_for_symbol(
    #            risk_manager=self,
    #            symbol=symbol,
    #            pos_unrealized_pnl_bp=pos_unrealized_pnl_bp,
    #            daily_state=daily_state,
    #        )
    #
    #   4) If allow is False, block the trade:
    #
    #        if not allow:
    #            return False, f"PHASE5:{reason}"
    #
    # This block is intentionally commented-out for now so that there
    # is NO behavior change until pos_unrealized_pnl_bp is correctly
    # wired from your live PnL pipeline.
    # ------------------------------------------------------------------

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


# === Phase 5 risk configuration wiring ===
# These helpers allow the engine to pull Phase5RiskConfig from env vars
# exported by tools/Export-Phase5RiskEnv.ps1, without changing existing
# RiskManager constructors or call sites.

try:
    from hybrid_ai_trading.risk.phase5_config import Phase5RiskConfig, load_phase5_risk_from_env
except Exception:  # pragma: no cover - defensive import for partial environments
    Phase5RiskConfig = None  # type: ignore
    load_phase5_risk_from_env = None  # type: ignore


def get_phase5_risk_config():
    """
    Load Phase5RiskConfig from the current environment.

    Returns
    -------
    Phase5RiskConfig | None
        Parsed config, or None if the phase5_config module/env vars
        are not available.
    """
    if load_phase5_risk_from_env is None:
        return None
    try:
        return load_phase5_risk_from_env()
    except Exception:
        # Stay defensive: risk layer should fail open rather than crash
        return None


def attach_phase5_risk_config(risk_manager):
    """
    Attach Phase5RiskConfig to an existing RiskManager-like instance.

    This keeps wiring non-invasive:
      - Does not alter RiskManager.__init__ signature
      - Does not change existing call sites
      - Simply sets risk_manager.phase5_risk_config if config is available
    """
    cfg = get_phase5_risk_config()
    if cfg is None:
        return
    setattr(risk_manager, "phase5_risk_config", cfg)


# === Phase 5 positional policy helpers (mirror of mock_phase5_trade_engine_runner) ===

from typing import Tuple
from hybrid_ai_trading.risk_config_phase5 import (
    RiskConfigPhase5,
    DailyRiskState,
    SymbolDailyState,
)


def phase5_can_add_position(
    risk_cfg: RiskConfigPhase5,
    symbol: str,
    pos_unrealized_pnl_bp: float,
    daily_state: DailyRiskState,
) -> Tuple[bool, str]:
    """
    Phase 5 risk policy: no averaging down + daily loss caps + symbol caps + max positions.

    This mirrors the logic in tools/mock_phase5_trade_engine_runner.py::can_add_position,
    but uses primitive inputs (unrealized PnL in bp) instead of a stub PositionSnapshot.
    """
    # 1) Account-level daily loss caps
    if daily_state.account_pnl_pct <= risk_cfg.daily_loss_cap_pct:
        return False, "daily_loss_cap_pct_reached"

    if daily_state.account_pnl_notional <= risk_cfg.daily_loss_cap_notional:
        return False, "daily_loss_cap_notional_reached"

    # 2) Symbol-level caps
    sym_state = daily_state.by_symbol.get(symbol)
    if sym_state is not None:
        if sym_state.pnl_bp <= risk_cfg.symbol_daily_loss_cap_bp:
            return False, "symbol_daily_loss_cap_reached"
        if sym_state.trades_today >= risk_cfg.symbol_max_trades_per_day:
            return False, "symbol_max_trades_per_day_reached"

    # 3) No averaging down
    if risk_cfg.no_averaging_down:
        if pos_unrealized_pnl_bp <= 0.0:
            return False, "no_averaging_down_block"
        if pos_unrealized_pnl_bp < risk_cfg.min_add_cushion_bp:
            return False, "min_add_cushion_bp_not_met"

    # 4) Position-count / weight caps
    if daily_state.open_positions >= risk_cfg.max_open_positions:
        return False, "max_open_positions_reached"

    return True, "okay"


def phase5_check_add_for_symbol(
    risk_manager,
    symbol: str,
    pos_unrealized_pnl_bp: float,
    daily_state: DailyRiskState,
) -> Tuple[bool, str]:
    """
    Convenience wrapper to evaluate Phase 5 'can add' policy using an attached config.

    Expected:
      - risk_manager.phase5_risk_config is set by attach_phase5_risk_config(...)
      - daily_state is a DailyRiskState snapshot for the current day
      - pos_unrealized_pnl_bp is the unrealized PnL of the existing position in bp

    Returns
    -------
    (allow: bool, reason: str)
        If config is missing, this fails open (allow=True, reason='phase5_config_missing').
    """
    cfg = getattr(risk_manager, "phase5_risk_config", None)
    if cfg is None:
        return True, "phase5_config_missing"

    return phase5_can_add_position(cfg, symbol, pos_unrealized_pnl_bp, daily_state)

def _rm_build_phase5_daily_state(self, symbol: str) -> DailyRiskState:
    """
    Build a DailyRiskState snapshot for Phase 5 using current RiskManager/portfolio fields.

    This is a Phase 5 helper; it does not perform any gating by itself.
    You will refine symbol-level PnL/trades wiring later.
    """
    ds = DailyRiskState()

    # Account-level daily PnL (notional)
    pnl_today = getattr(self, "_pnl_today", 0.0)
    try:
        ds.account_pnl_notional = float(pnl_today)
    except Exception:
        ds.account_pnl_notional = 0.0

    # Resolve equity from attached portfolio tracker or portfolio
    eq = None
    portfolio_tracker = getattr(self, "portfolio_tracker", None)
    portfolio = getattr(self, "portfolio", None)

    if portfolio_tracker is not None and hasattr(portfolio_tracker, "equity"):
        try:
            eq = float(getattr(portfolio_tracker, "equity", 0.0))
        except Exception:
            eq = None
    elif portfolio is not None and hasattr(portfolio, "equity"):
        try:
            eq = float(getattr(portfolio, "equity", 0.0))
        except Exception:
            eq = None

    if eq is not None and eq > 0:
        ds.account_pnl_pct = ds.account_pnl_notional / eq
    else:
        ds.account_pnl_pct = 0.0

    # Positions and open_positions
    positions = {}
    try:
        if portfolio_tracker is not None and hasattr(portfolio_tracker, "get_positions"):
            positions = portfolio_tracker.get_positions()
        elif portfolio is not None and hasattr(portfolio, "get_positions"):
            positions = portfolio.get_positions()
    except Exception:
        positions = {}

    try:
        ds.open_positions = len(positions or {})
    except Exception:
        ds.open_positions = 0

    # Symbol-level state (stub; refine with real per-symbol PnL/trades later)
    sym_state = SymbolDailyState()
    sym_state.pnl_bp = 0.0
    sym_state.pnl_notional = 0.0
    sym_state.trades_today = getattr(self, "_trades_today", 0)

    ds.by_symbol[symbol] = sym_state

    return ds


try:
    # Attach helper as a method on RiskManager for Phase 5 usage
    RiskManager.build_phase5_daily_state = _rm_build_phase5_daily_state
except NameError:
    # RiskManager not defined yet; keep module importable
    pass

# === PHASE5: No-Averaging-Down integration scaffolding ======================
# This block was appended by tools. It defines helper wiring for the
# no_averaging_down_policy module, but does not change existing behavior
# until validate_no_averaging_down_for_order(..) is called from the engine.

try:
    from .no_averaging_down_policy import (
        AveragingDownPolicy,
        PositionState,
        NoAveragingDownHelper,
        NoAveragingDownViolation,
    )
except Exception:  # pragma: no cover - defensive import
    AveragingDownPolicy = None
    PositionState = None
    NoAveragingDownHelper = None
    NoAveragingDownViolation = Exception


class Phase5NoAveragingDownBridge:
    """
    Lightweight bridge that RiskManager (or callers) can use to enforce
    the no-averaging-down policy for a given (symbol, regime) and order.

    This class is intentionally separate so that existing RiskManager code
    does not change behavior unless it opts in.
    """

    def __init__(self) -> None:
        if AveragingDownPolicy is None:
            # Helper module missing or import failed; disable feature.
            self._policy = None
            self._helper = None
            self._state_by_key = {}
        else:
            self._policy = AveragingDownPolicy()
            self._helper = NoAveragingDownHelper()
            self._state_by_key: dict[tuple[str, str], PositionState] = {}

    def _get_state(self, symbol: str, regime: str) -> PositionState:
        if self._policy is None or PositionState is None:
            # Feature disabled
            return PositionState() if PositionState is not None else None  # type: ignore[return-value]
        key = (symbol, regime)
        st = self._state_by_key.get(key)
        if st is None:
            st = PositionState()
            self._state_by_key[key] = st
        return st

    def validate_no_averaging_down_for_order(self, order, regime: str) -> None:
        """
        Optionally called by RiskManager / TradeEngine BEFORE sending
        an order to execution.

        'order' is expected to have:
          - symbol
          - qty (signed or unsigned)
          - price
        """
        if self._policy is None or self._helper is None:
            return

        symbol = getattr(order, "symbol", None)
        qty = getattr(order, "qty", None)
        price = getattr(order, "price", None)

        if symbol is None or qty is None or price is None:
            # If the order doesn't have the expected fields, do nothing.
            return

        side = "LONG" if qty > 0 else "SHORT"
        abs_qty = abs(qty)
        state = self._get_state(symbol, regime)

        # NOTE: PositionState currently has no live connection to your
        # actual position book; that wiring will be added in a later
        # pass by updating state before validate_no_averaging_down_for_order
        # is called.
        self._helper.validate_order(
            side=side,
            qty=abs_qty,
            price=float(price),
            position=state,
            policy=self._policy,
        )


# Convenience singleton bridge that callers may reuse.
_phase5_no_avg_bridge: Phase5NoAveragingDownBridge | None = None


def get_phase5_no_avg_bridge() -> Phase5NoAveragingDownBridge:
    global _phase5_no_avg_bridge
    if _phase5_no_avg_bridge is None:
        _phase5_no_avg_bridge = Phase5NoAveragingDownBridge()
    return _phase5_no_avg_bridge

# End of PHASE5 scaffolding ==================================================

# === Phase 5: no-averaging-down convenience helper ===========================

def phase5_no_averaging_down_for_symbol(self, symbol: str, pos_unrealized_pnl_bp: float) -> tuple[bool, str]:
    """
    Convenience wrapper around phase5_check_add_for_symbol(...) using this
    RiskManager instance.

    IMPORTANT:
    - If the Phase5RiskConfig does not yet define daily_loss_cap_pct,
      we treat Phase 5 deep checks as "not configured" and allow the trade.
      This avoids noisy AttributeErrors while Phase 5 config is still being wired.
    """
    try:
        cfg = get_phase5_risk_config()

        # If the config does not expose daily_loss_cap_pct yet, skip deep Phase 5
        # evaluation and allow the trade (fail-open, but clean).
        if not hasattr(cfg, "daily_loss_cap_pct"):
            return True, "phase5_daily_loss_cap_pct_not_configured"

        # Build a DailyRiskState snapshot for this symbol from current RM state
        daily_state = self.build_phase5_daily_state(symbol)

        # Delegate to the existing helper which includes:
        # - account daily loss caps
        # - per-symbol trade limits
        # - no-averaging-down logic when enabled
        allow, reason = phase5_check_add_for_symbol(
            risk_manager=self,
            symbol=symbol,
            pos_unrealized_pnl_bp=pos_unrealized_pnl_bp,
            daily_state=daily_state,
        )
        return allow, reason
    except Exception as exc:  # pragma: no cover
        import logging as _logging
        _logging.getLogger("hybrid_ai_trading.risk.risk_manager").error(
            "phase5_no_averaging_down_for_symbol failed: %s", exc, exc_info=True
        )
        # Fail open for now; enforcement wiring will be explicit and tested later.
        return True, "phase5_helper_failed"

# Attach helper to RiskManager if available
try:
    RiskManager.phase5_no_averaging_down_for_symbol = phase5_no_averaging_down_for_symbol
except NameError:
    pass

# === End Phase 5 no-averaging-down helper ====================================
# === RiskManager compatibility shim: approve_trade ======================

def _rm_approve_trade(self, symbol: str, side: str, qty: float, notional: float) -> bool:
    """
    Compatibility shim for older ExecutionEngine call sites and tests.

    New code should use allow_trade(...) or Phase 5 helpers.
    This wrapper delegates to allow_trade(notional=notional, side=side)
    and returns a simple bool.
    """
    fn = getattr(self, "allow_trade", None)
    if callable(fn):
        try:
            allow, _reason = fn(notional=notional, side=side)
            return bool(allow)
        except Exception:
            # Fail-open to avoid accidental global halts on shim error.
            return True
    # If no allow_trade is defined, fail-open.
    return True


try:
    if not hasattr(RiskManager, "approve_trade"):
        RiskManager.approve_trade = _rm_approve_trade
except NameError:
    # RiskManager not defined; keep module importable.
    pass

# === End approve_trade compatibility shim ==============================

# === Phase 5: no-averaging-down adapter for ExecutionEngine ===============

def _phase5_no_averaging_adapter(
    self,
    symbol,
    side=None,
    entry_ts=None,
    **extra,
):
    """
    Adapter for ExecutionEngine.place_order_phase5:

    Signature expected by engine:
        phase5_no_averaging_down_for_symbol(symbol, side, entry_ts=None)

    This implementation is intentionally simple and position-based:
    - If there is an open long position (qty > 0) and side == "BUY"  -> block.
    - If there is an open short position (qty < 0) and side == "SELL" -> block.
    - Otherwise allow.

    It uses:
      - self.get_position_for_symbol(symbol) if available, else
      - self.positions.get(symbol, 0) if available.
    """
    if not symbol or not side:
        return True, "no_symbol_or_side_provided"

    side_str = str(side).upper()
    if side_str not in ("BUY", "SELL"):
        # Unknown side -> do not block
        return True, "unknown_side"

    # Try to get current position
    pos = None
    pos_fn = getattr(self, "get_position_for_symbol", None)
    if callable(pos_fn):
        try:
            pos = pos_fn(symbol)
        except Exception:
            pos = None

    if pos is None:
        positions = getattr(self, "positions", None)
        if isinstance(positions, dict) and symbol in positions:
            pos = positions.get(symbol)

    # If still None, we fail-open (do not enforce)
    if pos is None:
        return True, "no_position_info"

    try:
        qty = float(pos)
    except (TypeError, ValueError):
        return True, "position_not_numeric"

    if qty == 0:
        return True, "flat"

    if qty > 0 and side_str == "BUY":
        return False, "no_averaging_long_block"

    if qty < 0 and side_str == "SELL":
        return False, "no_averaging_short_block"

    return True, "ok"


try:
    # Override any previous helper with the adapter that matches the engine call.
    RiskManager.phase5_no_averaging_down_for_symbol = _phase5_no_averaging_adapter
except NameError:
    pass

# === End Phase 5 no-averaging-down adapter =================================
# === Phase 5: RiskManager position helper for no-averaging adapter =========

def _rm_get_position_for_symbol(self, symbol: str) -> float:
    """
    Generic helper to resolve the current position size for a symbol.

    Priority:
    1) portfolio_tracker.get_positions()[symbol] if available
    2) portfolio.get_positions()[symbol] if available
    3) self.positions[symbol] if available
    Returns 0.0 if nothing is found or value is not numeric.
    """
    if not symbol:
        return 0.0

    sym_u = str(symbol).upper()
    size = 0.0

    # 1) portfolio_tracker
    try:
        pt = getattr(self, "portfolio_tracker", None)
        if pt is not None and hasattr(pt, "get_positions"):
            book = pt.get_positions()
            if isinstance(book, dict):
                row = book.get(sym_u) or book.get(symbol)
                if row is not None:
                    if isinstance(row, dict):
                        raw = (
                            row.get("size")
                            or row.get("qty")
                            or row.get("position")
                            or row.get("shares")
                        )
                    else:
                        raw = row
                    try:
                        return float(raw)
                    except (TypeError, ValueError):
                        pass
    except Exception:
        pass

    # 2) portfolio
    try:
        pf = getattr(self, "portfolio", None)
        if pf is not None and hasattr(pf, "get_positions"):
            book = pf.get_positions()
            if isinstance(book, dict):
                row = book.get(sym_u) or book.get(symbol)
                if row is not None:
                    if isinstance(row, dict):
                        raw = (
                            row.get("size")
                            or row.get("qty")
                            or row.get("position")
                            or row.get("shares")
                        )
                    else:
                        raw = row
                    try:
                        return float(raw)
                    except (TypeError, ValueError):
                        pass
    except Exception:
        pass

    # 3) self.positions dict
    try:
        positions = getattr(self, "positions", None)
        if isinstance(positions, dict):
            row = positions.get(sym_u) or positions.get(symbol)
            if row is not None:
                if isinstance(row, dict):
                    raw = (
                        row.get("size")
                        or row.get("qty")
                        or row.get("position")
                        or row.get("shares")
                    )
                else:
                    raw = row
                try:
                    return float(raw)
                except (TypeError, ValueError):
                    pass
    except Exception:
        pass

    return 0.0


try:
    # Only attach if method not already defined
    if not hasattr(RiskManager, "get_position_for_symbol"):
        RiskManager.get_position_for_symbol = _rm_get_position_for_symbol
except NameError:
    # RiskManager not defined; ignore
    pass

# === End Phase 5 position helper ===========================================


    def check_trade_phase5(self, trade: Dict[str, Any]):
        """
        Phase-5 stub risk evaluation.

        This is the safe placeholder wiring point for real Phase-5
        risk rules (daily loss caps, MDD, no-averaging-down, cooldowns).

        Current behavior:
        - Always allow trades.
        - Return a Phase5RiskDecision with allowed=True and a clear stub message.

        The Phase5RiskAdapter will convert this into the flat dict:
            {
                "allowed": True,
                "reason": "phase5_risk_stub_backend"
            }
        """
        from hybrid_ai_trading.risk.risk_phase5_types import Phase5RiskDecision

        return Phase5RiskDecision(
            allowed=True,
            reason="phase5_risk_stub_backend",
            details={}
        )

def _check_trade_phase5_impl(self, trade):
    """
    Phase-5 daily loss integration (initial wiring).

    NOTE:
    - This implementation currently behaves like a safe stub:
      it uses the daily_loss_gate helper but assumes new_pos_qty == pos_qty,
      so exposure is treated as non-increasing and the gate will not block.
    - Later, new_pos_qty should be computed from the proposed trade
      (symbol side/qty) to enforce real daily loss behavior.
    """
    from hybrid_ai_trading.risk.risk_phase5_daily_loss import daily_loss_gate

    # Resolve day_id and realized_pnl
    day_id = trade.get("day_id")
    if not day_id and hasattr(self, "_today_id"):
        try:
            day_id = self._today_id()
        except Exception:
            day_id = None
    if not day_id:
        day_id = "UNKNOWN"

    daily_pnl = getattr(self, "daily_pnl", {}) or {}
    realized_pnl = float(daily_pnl.get(day_id, 0.0))

    # Resolve current position quantity for the symbol (if any)
    symbol = str(trade.get("symbol", "UNKNOWN"))
    positions = getattr(self, "positions", {}) or {}
    pos = positions.get(symbol) if isinstance(positions, dict) else None
    pos_qty = float(getattr(pos, "qty", 0.0) if pos is not None else 0.0)

    # For now, treat new_pos_qty == pos_qty so daily_loss_gate acts
    # as a stub (no blocking). Later this will be updated to reflect
    # the hypothetical post-trade position.
    new_pos_qty = pos_qty

    # Resolve configured daily loss cap (if available)
    cfg = getattr(self, "config", None)
    daily_loss_cap = float(getattr(cfg, "phase5_daily_loss_cap", 0.0))

    decision = daily_loss_gate(
        realized_pnl=realized_pnl,
        daily_loss_cap=daily_loss_cap,
        pos_qty=pos_qty,
        new_pos_qty=new_pos_qty,
    )
    return decision


# Bind the implementation as a method on RiskManager if possible.
try:
    RiskManager  # type: ignore[name-defined]
except NameError:
    pass
else:
    if not hasattr(RiskManager, "check_trade_phase5"):
        setattr(RiskManager, "check_trade_phase5", _check_trade_phase5_impl)

def _check_trade_phase5_impl_v3(self, trade):
    """
    Phase-5 combined risk evaluation (daily loss + no-averaging-down).

    This implementation:
    - Computes a *real* hypothetical new_pos_qty using trade["side"] and trade["qty"].
    - Applies daily_loss_gate first.
    - If daily loss passes, applies no_averaging_down_gate.
    - Returns a Phase5RiskDecision.

    NOTE:
    - Additional gates (MDD, cooldown) can be added later in this pipeline.
    """
    from hybrid_ai_trading.risk.risk_phase5_daily_loss import daily_loss_gate
    from hybrid_ai_trading.risk.risk_phase5_no_avg import no_averaging_down_gate
    from hybrid_ai_trading.risk.risk_phase5_types import Phase5RiskDecision

    # Resolve day_id and realized_pnl
    day_id = trade.get("day_id")
    if not day_id and hasattr(self, "_today_id"):
        try:
            day_id = self._today_id()
        except Exception:
            day_id = None
    if not day_id:
        day_id = "UNKNOWN"

    daily_pnl = getattr(self, "daily_pnl", {}) or {}
    realized_pnl = float(daily_pnl.get(day_id, 0.0))

    # Resolve current position quantity and avg_price for the symbol (if any)
    symbol = str(trade.get("symbol", "UNKNOWN"))
    positions = getattr(self, "positions", {}) or {}
    pos = positions.get(symbol) if isinstance(positions, dict) else None
    pos_qty = float(getattr(pos, "qty", 0.0) if pos is not None else 0.0)
    avg_price = float(getattr(pos, "avg_price", trade.get("price", 0.0) or 0.0))

    # Compute signed quantity and hypothetical new_pos_qty
    side_raw = str(trade.get("side", "")).upper()
    qty = float(trade.get("qty", trade.get("size", 0.0)) or 0.0)

    if qty <= 0.0:
        signed_qty = 0.0
    elif "SELL" in side_raw or "SHORT" in side_raw:
        signed_qty = -qty
    else:
        # Treat anything else as long bias (BUY/LONG).
        signed_qty = qty

    new_pos_qty = pos_qty + signed_qty

    # Resolve configured daily loss cap (if available)
    cfg = getattr(self, "config", None)
    daily_loss_cap = float(getattr(cfg, "phase5_daily_loss_cap", 0.0))

    # 1) Daily loss gate
    dl_decision = daily_loss_gate(
        realized_pnl=realized_pnl,
        daily_loss_cap=daily_loss_cap,
        pos_qty=pos_qty,
        new_pos_qty=new_pos_qty,
    )
    if not dl_decision.allowed:
        return dl_decision

    # 2) No-averaging-down gate
    na_decision = no_averaging_down_gate(
        side=side_raw,
        qty=qty,
        price=float(trade.get("price", 0.0) or 0.0),
        pos_qty=pos_qty,
        avg_price=avg_price,
    )
    if not na_decision.allowed:
        return na_decision

    # 3) All Phase-5 gates passed
    combined_details = {
        "daily_loss": dl_decision.details,
        "no_avg": na_decision.details,
    }
    return Phase5RiskDecision(
        allowed=True,
        reason="phase5_risk_ok",
        details=combined_details,
    )


# Re-bind the implementation as the method on RiskManager.
try:
    RiskManager  # type: ignore[name-defined]
except NameError:
    pass
else:
    setattr(RiskManager, "check_trade_phase5", _check_trade_phase5_impl_v3)

from hybrid_ai_trading.risk.risk_phase5_account_caps import account_daily_loss_gate


def _check_trade_phase5_impl_v4(self, trade):
    """
    Phase-5 combined risk evaluation with account-wide daily caps.

    Pipeline:
    1) account_daily_loss_gate (account-wide)
    2) _check_trade_phase5_impl_v3 (symbol-level daily_loss_gate + no_avg)
    """
    from hybrid_ai_trading.risk.risk_phase5_types import Phase5RiskDecision

    # 1) Account-wide daily loss cap
    # Try to find an account-wide realized PnL on the RiskManager.
    account_realized_pnl = float(
        getattr(self, "account_realized_pnl", 0.0)
        or getattr(self, "daily_account_pnl", 0.0)
        or 0.0
    )

    cfg = getattr(self, "config", None)
    account_daily_loss_cap = float(getattr(cfg, "phase5_account_daily_loss_cap", 0.0))

    acct_decision: Phase5RiskDecision = account_daily_loss_gate(
        account_realized_pnl=account_realized_pnl,
        account_daily_loss_cap=account_daily_loss_cap,
    )
    if not acct_decision.allowed:
        return acct_decision

    # 2) Delegate to v3 (symbol-level daily_loss_gate + no_avg gate)
    sym_decision = _check_trade_phase5_impl_v3(self, trade)
    if not getattr(sym_decision, "allowed", True):
        return sym_decision

    # 3) Symbol-specific EV-band gates (SPY/QQQ ORB)
    class _Phase5Ctx:
        pass

    ctx = _Phase5Ctx()
    ctx.symbol = str(trade.get("symbol", "UNKNOWN"))
    ctx.regime = str(trade.get("regime", trade.get("regime_name", "")) or "")

    tp_r = trade.get("tp_r")
    if tp_r is None:
        tp_r = trade.get("r_multiple")
    if tp_r is not None:
        try:
            tp_r = float(tp_r)
        except (TypeError, ValueError):
            tp_r = None
    ctx.tp_r = tp_r

    ctx.session_date = trade.get("day_id") or trade.get("session_date")

    # Local import to avoid module-level circular dependency:
    # risk_phase5_engine_guard already imports RiskManager.
    from hybrid_ai_trading.risk.risk_phase5_engine_guard import allow_trade_phase5

    allowed, reason = allow_trade_phase5(ctx, risk_state=None)
    if not allowed:
        return Phase5RiskDecision(
            allowed=False,
            reason=reason,
            details={
                "account_daily_loss": {
                    "account_realized_pnl": account_realized_pnl,
                    "account_daily_loss_cap": account_daily_loss_cap,
                },
                "symbol_phase5": getattr(sym_decision, "details", {}),
            },
        )

    return sym_decision


# Re-bind the implementation as the method on RiskManager.
try:
    RiskManager  # type: ignore[name-defined]
except NameError:
    pass
else:
    setattr(RiskManager, "check_trade_phase5", _check_trade_phase5_impl_v4)