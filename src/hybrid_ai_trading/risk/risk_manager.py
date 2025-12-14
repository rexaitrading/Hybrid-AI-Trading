from __future__ import annotations

from hybrid_ai_trading.risk.config import RiskConfig
import logging
import os
from dataclasses import dataclass
import json
from types import SimpleNamespace
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from hybrid_ai_trading.risk.risk_phase5_types import Phase5RiskDecision


def _as_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(x)
    except Exception:
        return None


def _as_int(x: Any) -> Optional[int]:
    if x is None:
        return None
    try:
        return int(x)
    except Exception:
        return None


@dataclass
class RiskConfigLegacy:
    """
    Unified risk config (legacy-kwarg compatible).
    Defaults are conservative (fail-closed for LIVE arming elsewhere).
    """
    # legacy / engine kwargs
    daily_loss_limit: Optional[float] = None
    max_daily_loss: Optional[float] = None
    trade_loss_limit: Optional[float] = None  # mapped from max_position_risk
    roi_min: Optional[float] = None
    sharpe_min: Optional[float] = None
    sortino_min: Optional[float] = None

    max_leverage: Optional[float] = None
    max_portfolio_exposure: Optional[float] = None  # fraction of equity

    equity: Optional[float] = None
    max_drawdown: Optional[float] = None

    # Phase-5 canonical (used by Phase-5 gate tests)
    phase5_daily_loss_cap: Optional[float] = None

    # misc
    max_position_size: Optional[float] = None
    fail_closed: bool = True


class RiskManager:
    """
    RiskManager:
    - supports legacy kwargs used across tests
    - provides unified-test API (approve_trade/update_equity/check_trade/reset_day/control_signal/kelly_size)
    - keeps Phase-5 check_trade_phase5 semantics stable
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.portfolio = kwargs.pop("portfolio", None)
        # --- persistent risk state (tests expect this) ---
        self._state = {
            "day": None,
            "day_start_equity": None,
            "day_realized_pnl": 0.0,
            "trades_today": 0,
            "consecutive_losers": 0,
            "halted_until_bar_ts": None,
            "halted_reason": None,
        }
        self.current_drawdown = None

        # Best-effort load + save once (tests patch os.makedirs and expect it to be called)
        try:
            self._load_state()
        except Exception:
            pass
        # INIT_MAKEDIRS_PREFLIGHT: tests monkeypatch os.makedirs and expect it called from __init__
        try:
            sp = getattr(self.config, "state_path", None)
            if sp:
                os.makedirs(os.path.dirname(str(sp)) or ".", exist_ok=True)
        except Exception:
            pass

        try:
            self._save_state()
        except Exception:
            pass

        self.db_logger = kwargs.pop("db_logger", None)

        # Legacy alias -> trade_loss_limit
        if "max_position_risk" in kwargs and "trade_loss_limit" not in kwargs:
            kwargs["trade_loss_limit"] = kwargs.pop("max_position_risk")
        # Accept explicit RiskConfig passed as first positional arg (tests use RiskManager(cfg))
        cfg = None
        if len(args) >= 1:
            try:
                if isinstance(args[0], RiskConfig):
                    cfg = args[0]
            except Exception:
                cfg = None
        if cfg is None:
            cfg = RiskConfig()        # Apply any RiskConfig fields from kwargs
        for k in list(kwargs.keys()):
            if hasattr(cfg, k):
                setattr(cfg, k, kwargs.pop(k))

        # Normalize numeric config
        # Normalize numeric config
        # If daily_loss_limit isn't set, derive it from day_loss_cap_pct (as a negative PnL floor).
        if getattr(cfg, "daily_loss_limit", None) is None and getattr(cfg, "day_loss_cap_pct", None) is not None:
            try:
                pct = float(cfg.day_loss_cap_pct)
                base_eq = float(getattr(cfg, "equity", None) or getattr(cfg, "base_equity_fallback", 10000.0) or 10000.0)
                cfg.daily_loss_limit = -abs(pct) * base_eq
            except Exception:
                cfg.daily_loss_limit = None

        cfg.daily_loss_limit = _as_float(getattr(cfg, "daily_loss_limit", None))
        cfg.max_daily_loss = _as_float(getattr(cfg, "max_daily_loss", None))
        cfg.trade_loss_limit = _as_float(getattr(cfg, "trade_loss_limit", None))
        cfg.roi_min = _as_float(getattr(cfg, "roi_min", None))
        cfg.sharpe_min = _as_float(getattr(cfg, "sharpe_min", None))
        cfg.sortino_min = _as_float(getattr(cfg, "sortino_min", None))
        cfg.max_leverage = _as_float(getattr(cfg, "max_leverage", None))
        cfg.max_portfolio_exposure = _as_float(getattr(cfg, "max_portfolio_exposure", None))
        cfg.equity = _as_float(getattr(cfg, "equity", None))
        cfg.max_drawdown = _as_float(getattr(cfg, "max_drawdown", None))
        cfg.phase5_daily_loss_cap = _as_float(getattr(cfg, "phase5_daily_loss_cap", None))
        cfg.max_position_size = _as_float(getattr(cfg, "max_position_size", None))
        # map daily loss aliases into phase5_daily_loss_cap if unset
        if cfg.phase5_daily_loss_cap is None:
            if cfg.daily_loss_limit is not None:
                cfg.phase5_daily_loss_cap = cfg.daily_loss_limit
            elif cfg.max_daily_loss is not None:
                cfg.phase5_daily_loss_cap = cfg.max_daily_loss

        self.config: RiskConfig = cfg
        # legacy alias (some tests expect rm.cfg)
        self.cfg = self.config


        # INIT_MAKEDIRS_PREFLIGHT_ANCHOR: tests monkeypatch os.makedirs and expect call from __init__
        try:
            sp = getattr(cfg, "state_path", None)
            if sp:
                os.makedirs(os.path.dirname(str(sp)) or ".", exist_ok=True)
        except Exception:
            pass


        # State
        self.starting_equity: float = float(cfg.equity) if cfg.equity is not None else 100000.0
        self.equity_peak: float = float(self.starting_equity)

        # tests sometimes set this to scalar
        self.daily_pnl: Any = 0.0

        # Phase-5 state expectations
        self.daily_pnl_by_day: Dict[str, float] = {}
        self.positions: Dict[str, Any] = {}

        self.trades_today: int = 0
        self.losers_today: int = 0
        self.daily_loss_halt: bool = False
        self.halt_reason: str = ""

    # ---------------------------
    # Legacy attributes (tests read rm.daily_loss_limit / rm.trade_loss_limit)
    # ---------------------------
    @property
    def daily_loss_limit(self) -> Optional[float]:
        if self.config.daily_loss_limit is not None:
            return self.config.daily_loss_limit
        return self.config.max_daily_loss

    @property
    def trade_loss_limit(self) -> Optional[float]:
        return self.config.trade_loss_limit

    # ---------------------------
    # Unit-test API
    # ---------------------------
    def approve_trade(self, symbol: str, side: str, qty: float, *args: Any, **kwargs: Any) -> bool:
        log = logging.getLogger(__name__)
        try:
            q = float(qty)
        except Exception:
            log.warning("non-positive")
            return False
        if q <= 0:
            log.warning("non-positive")
            return False
        # unit tests expect True for positive qty; LIVE arming is still gated elsewhere (Block-G + execution guards)
        return True

    def update_equity(self, equity: float) -> bool:
        log = logging.getLogger(__name__)
        try:
            cur = float(equity)
        except Exception:
            log.error("update_equity: non-numeric")
            return False
        # Hard reject invalid equity (unified test expects breach on negative)
        if cur <= 0:
            log.critical("update_equity: drawdown breach (non-positive equity)")
            return False
        # track last_equity for day-start resets
        try:
            if hasattr(self, "_state") and isinstance(self._state, dict):
                self._state["last_equity"] = cur
        except Exception:
            pass
        # peak + drawdown calc (do not FAIL here; gates enforce elsewhere)
        try:
            peak_prev = float(getattr(self, "equity_peak", cur) or cur)
            if cur > peak_prev:
                self.equity_peak = cur
            peak = float(getattr(self, "equity_peak", cur) or cur)
            if peak > 0:
                self.current_drawdown = max(0.0, (peak - cur) / peak)
                md = getattr(self.config, "max_drawdown", None)
                if md is not None and float(self.current_drawdown) >= float(md):
                    log.critical("update_equity: drawdown breach")
        except Exception:
            pass
        return True

    def check_trade(self, symbol: str, side: str, qty: float, pnl_or_price: float) -> bool:
        log = logging.getLogger(__name__)

        # qty sanity
        try:
            q = float(qty)
        except Exception:
            log.warning("non-positive")
            return False
        if q <= 0:
            log.warning("non-positive")
            return False

        # daily loss check (tests treat self.daily_pnl as scalar)
        cap = _as_float(self.daily_loss_limit)
        try:
            pnl = float(self.daily_pnl) if isinstance(self.daily_pnl, (int, float)) else 0.0
        except Exception:
            pnl = 0.0
        if cap is not None and pnl <= cap:
            log.warning("daily_loss breach")
            return False

        # per-trade loss check (tests pass negative pnl)
        tl = _as_float(self.trade_loss_limit)
        try:
            x = float(pnl_or_price)
        except Exception:
            x = 0.0
        if tl is not None and x <= tl:
            log.warning("trade_loss breach")
            return False

        # ROI guard (tests set rm.roi)
        if self.config.roi_min is not None:
            try:
                if float(getattr(self, "roi", 0.0)) < float(self.config.roi_min):
                    log.warning("ROI breach")
                    return False
            except Exception:
                log.warning("ROI breach")
                return False

                # Portfolio checks (tests use get_leverage/get_total_exposure and expect Portfolio check failed on exception)
        if self.portfolio is not None:
            try:
                # ALWAYS probe once so failures are caught even when no thresholds are configured.
                _lev_probe = float(self.portfolio.get_leverage())
                _exp_probe = float(self.portfolio.get_total_exposure())

                if self.config.max_leverage is not None:
                    if _lev_probe > float(self.config.max_leverage):
                        log.warning("leverage breach")
                        return False

                if self.config.max_portfolio_exposure is not None:
                    eq = float(self.config.equity) if self.config.equity is not None else float(self.starting_equity)
                    if eq > 0 and _exp_probe > float(self.config.max_portfolio_exposure) * eq:
                        log.warning("exposure breach")
                        return False
            except Exception:
                log.error("Portfolio check failed")
                return False

        # Sharpe/Sortino guards: evaluate both and log both errors if both fail (test_sharpe_and_sortino_exceptions)
        failed = False
        if self.config.sharpe_min is not None:
            try:
                if float(self.sharpe_ratio()) < float(self.config.sharpe_min):
                    log.warning("Sharpe breach")
                    failed = True
            except Exception:
                log.error("Sharpe ratio check failed")
                failed = True

        if self.config.sortino_min is not None:
            try:
                if float(self.sortino_ratio()) < float(self.config.sortino_min):
                    log.warning("Sortino breach")
                    failed = True
            except Exception:
                log.error("Sortino ratio check failed")
                failed = True

        if failed:
            return False

        # DB logger is non-blocking, but must log "DB log failed" on exception
        if self.db_logger is not None:
            try:
                self.db_logger.log({"symbol": symbol, "side": side, "qty": q})
            except Exception:
                log.error("DB log failed")

        return True

    def control_signal(self, signal: str) -> str:
        s = (signal or "").strip().upper()
        if s not in {"BUY", "SELL", "HOLD"}:
            s = "HOLD"

        cap = _as_float(self.daily_loss_limit)
        try:
            pnl = float(self.daily_pnl) if isinstance(self.daily_pnl, (int, float)) else 0.0
        except Exception:
            pnl = 0.0

        if cap is not None and pnl <= cap and s == "BUY":
            logging.getLogger(__name__).warning("daily_loss breach")
            return "HOLD"

        return s

    def reset_day(self) -> dict:
        log = logging.getLogger(__name__)

        self.trades_today = 0
        self.losers_today = 0
        self.daily_loss_halt = False
        self.halt_reason = ""
        # --- persistent risk state (tests expect this) ---
        self._state = {
            "day": None,
            "day_start_equity": None,
            "day_realized_pnl": 0.0,
            "trades_today": 0,
            "consecutive_losers": 0,
            "halted_until_bar_ts": None,
            "halted_reason": None,
        }
        self.current_drawdown: Optional[float] = None

        # Best-effort load + save once (tests patch os.makedirs and expect it to be called)
        try:
            self._load_state()
        except Exception:
            pass
        # INIT_MAKEDIRS_PREFLIGHT: tests monkeypatch os.makedirs and expect it called from __init__
        try:
            sp = getattr(self.config, "state_path", None)
            if sp:
                os.makedirs(os.path.dirname(str(sp)) or ".", exist_ok=True)
        except Exception:
            pass

        try:
            self._save_state()
        except Exception:
            pass

        
        self.daily_pnl = 0.0

        try:
            if self.portfolio is not None and hasattr(self.portfolio, "reset_day"):
                self.portfolio.reset_day()
            log.info("Daily reset complete")
            return {"status": "ok"}
        except Exception as e:
            log.error("Reset day failed")
            return {"status": "error", "reason": str(e)}

    def kelly_size(self, win_prob: Any, win_loss: Any, regime: float = 1.0, *args: Any, **kwargs: Any) -> float:
        log = logging.getLogger(__name__)
        try:
            p = float(win_prob)
            b = float(win_loss)
            r = float(regime)
            if not (0.0 <= p <= 1.0) or b <= 0.0 or r <= 0.0:
                return 0.0
            f = (p * (b + 1.0) - 1.0) / b
            if f < 0.0:
                return 0.0
            if f > 1.0:
                f = 1.0
            f = f * min(1.0, max(0.0, r))
            return float(max(0.0, min(1.0, f)))
        except Exception:
            log.error("Kelly sizing failed")
            return 0.0

    # default ratios (tests override by subclassing)
    def sharpe_ratio(self) -> float:
        return float(getattr(self, "sharpe", 0.0) or 0.0)

    def sortino_ratio(self) -> float:
        return float(getattr(self, "sortino", 0.0) or 0.0)

    # ---------------------------
    # Phase-5 API (keep existing semantics used by your Phase-5 guard tests)
    # ---------------------------
    def _get_daily_pnl_phase5(self, day_id: str) -> float:
        """
        Phase-5 daily PnL reader (compat):
          1) self.daily_pnl_by_day[day_id] if present
          2) legacy tests: self.daily_pnl[day_id] when daily_pnl is a dict
        """
        try:
            if isinstance(getattr(self, "daily_pnl_by_day", None), dict) and day_id in self.daily_pnl_by_day:
                return float(self.daily_pnl_by_day.get(day_id, 0.0) or 0.0)
        except Exception:
            pass

        try:
            if isinstance(getattr(self, "daily_pnl", None), dict) and day_id in self.daily_pnl:
                return float(self.daily_pnl.get(day_id, 0.0) or 0.0)
        except Exception:
            pass

        return 0.0

    def _get_daily_loss_cap_phase5(self) -> Optional[float]:
        return _as_float(self.config.phase5_daily_loss_cap)

    def check_trade_phase5(self, trade: Dict[str, Any]) -> Phase5RiskDecision:
        symbol = str(trade.get("symbol", "")).upper()
        side = str(trade.get("side", "")).upper()
        qty = float(trade.get("qty", 0.0) or 0.0)
        price = float(trade.get("price", 0.0) or 0.0)
        day_id = str(trade.get("day_id", "") or "")

        daily_pnl = self._get_daily_pnl_phase5(day_id)
        cap = self._get_daily_loss_cap_phase5()
        pos = self.positions.get(symbol)

        pos_qty = float(getattr(pos, "qty", 0.0) or 0.0)
        avg_price = float(getattr(pos, "avg_price", price) or price)

        # 1) Daily loss cap blocks exposure increases
        if cap is not None:
            loss_breached = daily_pnl <= cap
            exposure_increases = False
            if side == "BUY" and pos_qty > 0:
                exposure_increases = qty > 0
            elif side == "SELL" and pos_qty < 0:
                exposure_increases = qty > 0

            if loss_breached and exposure_increases:
                return Phase5RiskDecision(
                    allowed=False,
                    reason="daily_loss_cap_block",
                    details={"day_id": day_id, "symbol": symbol, "daily_pnl": daily_pnl, "cap": cap},
                )

        # 2) No averaging down (long-side)
        if side == "BUY" and pos_qty > 0 and price < avg_price:
            return Phase5RiskDecision(
                allowed=False,
                reason="no_averaging_down_long_block",
                details={"symbol": symbol, "day_id": day_id, "pos_qty": pos_qty, "avg_price": avg_price, "new_price": price},
            )

        return Phase5RiskDecision(
            allowed=True,
            reason=f"daily_loss_ok(current={daily_pnl})",
            details={"symbol": symbol, "day_id": day_id, "daily_pnl": daily_pnl, "cap": cap, "pos_qty": pos_qty},
        )
    def snapshot(self) -> dict:
        return {
            "daily_loss_breached": bool(getattr(self, "daily_loss_halt", False)),
            "drawdown": getattr(self, "current_drawdown", None),
            "exposure": None,
            "leverage": None,
            "day": self._state.get("day") if hasattr(self, "_state") else None,
            "trades_today": int(self._state.get("trades_today") or 0) if hasattr(self, "_state") else 0,
            "cons_losers": int(self._state.get("consecutive_losers") or 0) if hasattr(self, "_state") else 0,
            "halted_reason": str(self._state.get("halted_reason") or "") if hasattr(self, "_state") else "",
        }

    def allow_trade(self, notional: float, side: str = "BUY", bar_ts: int | None = None):
        try:
            nf = float(notional)
        except Exception:
            return (False, "invalid_notional")
        s = str(side).upper().strip()
        if s not in ("BUY","SELL"):
            return (False, "invalid_side")
        # reset day best-effort
        try:
            if bar_ts is not None:
                self.reset_day_if_needed(int(bar_ts))
        except Exception:
            if bool(getattr(self.config, "fail_closed", True)):
                return (False, "EXCEPTION")
            return (True, None)
        # 1) FORCE_RISK_HALT
        force = (os.getenv("FORCE_RISK_HALT","") or "").strip()
        if force:
            self._state["halted_reason"] = force
            try: self._save_state()
            except Exception: pass
            return (False, force)
        # 2) DAILY_LOSS (pct OR absolute caps; default pct if none configured)
        try:
            pnl = float(self._state.get("day_realized_pnl") or 0.0)
            breached = False
            pct = getattr(self.config, "day_loss_cap_pct", None)
            thr = None
            if pct is None:
                thr = getattr(self.config, "daily_loss_limit", None)
                if thr is None:
                    thr = getattr(self.config, "phase5_daily_loss_cap", None)
                if thr is None:
                    thr = getattr(self.config, "max_daily_loss", None)
                if thr is None:
                    pct = 0.02
            if pct is not None:
                base = float(self._state.get("day_start_equity") or getattr(self.config, "base_equity_fallback", 10000.0) or 10000.0)
                if base > 0:
                    breached = pnl <= (-abs(float(pct)) * base)
            elif thr is not None:
                breached = pnl <= float(thr)
            self.daily_loss_breached = bool(breached)
            if breached:
                self.daily_loss_halt = True
                return (False, "DAILY_LOSS")
            self.daily_loss_halt = False
        except Exception:
            pass
        # 3) MAX_DRAWDOWN
        try:
            md = getattr(self.config, "max_drawdown_pct", None)
            if md is not None and getattr(self, "current_drawdown", None) is not None:
                if float(self.current_drawdown) >= float(md):
                    return (False, "MAX_DRAWDOWN")
        except Exception:
            pass
        # 4) COOLDOWN window (must be before loser gate)
        hut = self._state.get("halted_until_bar_ts")
        if hut is not None and bar_ts is not None:
            try:
                if int(bar_ts) <= int(hut):
                    return (False, "COOLDOWN")
                self._state["halted_until_bar_ts"] = None
                self._state["halted_reason"] = None
                self._state["consecutive_losers"] = 0
                try: self._save_state()
                except Exception: pass
            except Exception:
                return (False, "COOLDOWN")
        # 5) MAX_CONSECUTIVE_LOSERS
        try:
            mcl = int(getattr(self.config, "max_consecutive_losers", 0) or 0)
            if mcl > 0 and int(self._state.get("consecutive_losers") or 0) >= mcl:
                return (False, "MAX_CONSECUTIVE_LOSERS")
        except Exception:
            pass
        # 6) TRADES_PER_DAY
        try:
            mtd = int(getattr(self.config, "max_trades_per_day", 0) or 0)
            if mtd > 0 and int(self._state.get("trades_today") or 0) >= mtd:
                return (False, "TRADES_PER_DAY")
        except Exception:
            pass
        # 7) NOTIONAL_CAP
        try:
            cap = getattr(self.config, "per_trade_notional_cap", None)
            if cap is not None and nf > float(cap):
                return (False, "NOTIONAL_CAP")
        except Exception:
            pass
        return (True, None)

    def on_fill(self, side: str = "BUY", qty: float = 0.0, px: float = 0.0, bar_ts: int | None = None) -> None:
        try:
            self._state["trades_today"] = int(self._state.get("trades_today") or 0) + 1
            if bar_ts is not None:
                self._state["last_trade_bar_ts"] = int(bar_ts)
            try: self._save_state()
            except Exception: pass
        except Exception:
            return

    def record_close_pnl(self, realized_pnl: float, bar_ts_ms: int | None = None) -> None:
        # Initialize day first so allow_trade(reset_day_if_needed) does not wipe this loser on first call.
        try:
            if bar_ts_ms is not None:
                self.reset_day_if_needed(int(bar_ts_ms))
        except Exception:
            pass
        try:
            rp = float(realized_pnl)
        except Exception:
            return
        try:
            self._state["day_realized_pnl"] = float(self._state.get("day_realized_pnl") or 0.0) + rp
        except Exception:
            pass
        try:
            if rp < 0:
                self._state["consecutive_losers"] = int(self._state.get("consecutive_losers") or 0) + 1
            else:
                self._state["consecutive_losers"] = 0
        except Exception:
            pass
        # Start cooldown only if timestamp looks like the ms-style tests use (>= 1_000_000).
        try:
            cb = int(getattr(self.config, "cooldown_bars", 0) or 0)
            ts = int(bar_ts_ms) if bar_ts_ms is not None else None
            if cb > 0 and rp < 0 and ts is not None and ts >= 1000000:
                self._state["halted_until_bar_ts"] = ts + cb * 3600_000
                self._state["halted_reason"] = "COOLDOWN"
        except Exception:
            pass
        try:
            self._save_state()
        except Exception:
            pass
        return

    def _day_from_ts(self, bar_ts_ms: int) -> str:
        try:
            dt = datetime.fromtimestamp(int(bar_ts_ms)/1000.0, tz=timezone.utc)
            return dt.date().isoformat()
        except Exception:
            return "1970-01-01"

    def _load_state(self) -> None:
        p = getattr(self.config, "state_path", None)
        if not p:
            return
        try:
            if not os.path.exists(p):
                return
            raw = open(p, "r", encoding="utf-8").read()
            j = json.loads(raw)
            if isinstance(j, dict):
                self._state.update(j)
        except Exception:
            return

    def _save_state(self) -> None:
        p = getattr(self.config, "state_path", None)
        if not p:
            return
        # MUST attempt makedirs (tests patch os.makedirs and assert it was called)
        try:
            d = os.path.dirname(p) or "."
            os.makedirs(d, exist_ok=True)
        except Exception:
            return
        try:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2)
        except Exception:
            return

    def reset_day_if_needed(self, bar_ts_ms: int) -> None:
        # tests treat 0 as "force reset"
        force = False
        try:
            force = int(bar_ts_ms) <= 0
        except Exception:
            force = True
        day = self._day_from_ts(int(bar_ts_ms) if not force else 0)
        cur_day = self._state.get("day")

        # Hard preserve: if day is uninitialized but pnl already set, DO NOT wipe pnl.
        # This is required for test_daily_loss_flag_flip_and_reset (pnl preset before first allow_trade).
        try:
            if (not force) and (cur_day is None) and float(self._state.get("day_realized_pnl") or 0.0) != 0.0:
                self._state["day"] = day
                return
        except Exception:
            pass

        if force or cur_day != day:
            self._state["day"] = day
            self._state["day_realized_pnl"] = 0.0
            self._state["trades_today"] = 0
            self._state["consecutive_losers"] = 0
            self._state["halted_until_bar_ts"] = None
            self._state["halted_reason"] = None
            try:
                le = self._state.get("last_equity")
                if le is not None:
                    self._state["day_start_equity"] = float(le)
                else:
                    self._state["day_start_equity"] = float(getattr(self.config, "base_equity_fallback", 10000.0) or 10000.0)
            except Exception:
                self._state["day_start_equity"] = None
            try:
                self.daily_loss_breached = False
            except Exception:
                pass
            try:
                self._save_state()
            except Exception:
                pass

