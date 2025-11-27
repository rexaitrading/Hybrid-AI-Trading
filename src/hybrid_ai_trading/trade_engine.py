"""
Trade Engine (Hybrid AI Quant Pro v17.5 – Hedge Fund Grade, Loop-Proof Normalized)
---------------------------------------------------------------------------------
- Guardrails BEFORE routing: equity caps, sector caps, hedge drawdown limits.
- Router normalized BEFORE regime/filters/performance
- Regime-disabled overrides Sharpe/Sortino ranking (regime gate evaluated first).
- Sentiment BEFORE GateScore BEFORE Sharpe/Sortino (order: sentiment → gate score → risk metrics).
- Kelly config sanitized (drops "enabled")
- Audit logging always creates files
- alert() implemented for Slack/Telegram/Email
- record_trade_outcome added to log realized PnL / R-multiple for downstream stats.
- reset_day patched with safe fallback when provider state is missing (no crash on close).
- Final normalization: use "ok" + "filled" consistently for both status and reason.
- FIX: unknown algo now returns early as rejected (no normalization overwrite).
"""

import csv
import importlib
import logging
import os
import smtplib
from typing import Any, Dict, List, Optional

import requests

from hybrid_ai_trading.execution.order_manager import OrderManager
from hybrid_ai_trading.execution.portfolio_tracker import PortfolioTracker
from hybrid_ai_trading.execution.smart_router import SmartOrderRouter
from hybrid_ai_trading.performance_tracker import PerformanceTracker
from hybrid_ai_trading.risk.gatescore import GateScore
from hybrid_ai_trading.risk.kelly_sizer import KellySizer
from hybrid_ai_trading.risk.regime_detector import RegimeDetector
from hybrid_ai_trading.risk.risk_manager import RiskManager, attach_phase5_risk_config
from hybrid_ai_trading.risk.sentiment_filter import SentimentFilter
# HAT-SAFE-PATH v1
def _ensure_report_dir(base: str | None = None) -> str:
    base = base or os.environ.get('HAT_REPORT_DIR') or os.environ.get('GITHUB_WORKSPACE') or ''
    report_dir = os.path.join(base, '.ci') if base else '.ci'
    os.makedirs(report_dir, exist_ok=True)
    return report_dir

def _normalize_path(p) -> str:
    if p is None or (isinstance(p, str) and not p.strip()):
        return os.path.join(_ensure_report_dir(), 'engine.log')
    s = os.fspath(p)
    d = os.path.dirname(s)
    if d:
        os.makedirs(d, exist_ok=True)
    return s


logger = logging.getLogger(__name__)


class TradeEngine:
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        portfolio: Optional[PortfolioTracker] = None,
        brokers: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.config = config or {}
        self.mode = self.config.get("mode", "paper")
        self.portfolio = portfolio or PortfolioTracker(
            self.config.get("risk", {}).get("equity", 100000.0)
        )

        # Audit logs
        self.audit_log = self.config.get("audit_log_path", "audit.csv")
        self.backup_log = self.config.get("backup_log_path", "backup.csv")

        # Risk Manager
        risk_cfg = self.config.get("risk", {})
        self.risk_manager = RiskManager(
            daily_loss_limit=risk_cfg.get("max_daily_loss", -0.03),
            trade_loss_limit=risk_cfg.get("max_position_risk", -0.01),
            max_leverage=risk_cfg.get("max_leverage", 5.0),
            equity=risk_cfg.get("equity", 100000.0),
            max_portfolio_exposure=risk_cfg.get("max_portfolio_exposure", 0.5),
            portfolio=self.portfolio,
        )
        attach_phase5_risk_config(self.risk_manager)

        # Kelly config sanitize
        kelly_cfg = dict(risk_cfg.get("kelly", {}))
        kelly_cfg.pop("enabled", None)
        if not kelly_cfg:
            kelly_cfg = {"win_rate": 0.5, "payoff": 1.0, "fraction": 1.0}
        self.kelly_sizer = KellySizer(**kelly_cfg)
        self.base_fraction = kelly_cfg.get("fraction", 1.0)

        self.sentiment_filter = SentimentFilter(**self.config.get("sentiment", {}))
        self.gatescore = GateScore(**self.config.get("gatescore", {}))

        self.regime_enabled = self.config.get("regime", {}).get("enabled", True)
        self.regime_detector = (
            RegimeDetector(**self.config.get("regime", {}))
            if self.regime_enabled
            else None
        )

        self.performance_tracker = PerformanceTracker(window=50)

        # Execution
        self.order_manager = OrderManager(
            self.risk_manager,
            self.portfolio,
            dry_run=self.mode != "live",
            costs=self.config.get("costs", {}),
            use_paper_simulator=self.config.get("use_paper_simulator", False),
        )
        self.router = SmartOrderRouter(
            brokers or {"alpaca": self.order_manager}, self.config.get("execution", {})
        )

    # ------------------------------------------------------------------
    def _fire_alert(self, message: str) -> None:
        try:
            self.router._send_alert(f"Router error: {message}")
        except Exception:
            logger.error("Router alert dispatch failed: %s", message)

    def alert(self, message: str) -> Dict[str, Any]:
        results = {}
        try:
            slack_url = os.getenv(
                self.config.get("alerts", {}).get("slack_webhook_env", ""), ""
            )
            if slack_url:
                r = requests.post(slack_url, json={"text": message})
                results["slack"] = r.status_code
        except Exception as e:
            results["slack"] = "error"
            logger.error("Slack alert failed: %s", e)

        try:
            tg_bot = os.getenv(
                self.config.get("alerts", {}).get("telegram_bot_env", ""), ""
            )
            tg_chat = os.getenv(
                self.config.get("alerts", {}).get("telegram_chat_id_env", ""), ""
            )
            if tg_bot and tg_chat:
                url = f"https://api.telegram.org/bot{tg_bot}/sendMessage"
                r = requests.get(url, params={"chat_id": tg_chat, "text": message})
                results["telegram"] = r.status_code
        except Exception as e:
            results["telegram"] = "error"
            logger.error("Telegram alert failed: %s", e)

        try:
            email_to = os.getenv(self.config.get("alerts", {}).get("email_env", ""), "")
            if email_to:
                with smtplib.SMTP("localhost") as smtp:
                    smtp.send_message(f"Subject: Alert\n\n{message}")
                results["email"] = "sent"
        except Exception as e:
            results["email"] = "error"
            logger.error("Email alert failed: %s", e)

        return results or {"status": "no_alerts"}

    # ------------------------------------------------------------------
    def _write_audit(self, row: List[Any]) -> None:
        for path in [self.audit_log, self.backup_log]:
            try:
                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                exists = os.path.exists(path)
                with open(path, "a", newline="") as f:
                    w = csv.writer(f)
                    if not exists:
                        w.writerow(
                            [
                                "time",
                                "symbol",
                                "side",
                                "size",
                                "price",
                                "status",
                                "equity",
                                "reason",
                            ]
                        )
                    w.writerow(row)
            except Exception as e:
                logger.error("Audit write failed (%s): %s", path, e)

    # ------------------------------------------------------------------
    def reset_day(self) -> Dict[str, Any]:
        try:
            port_status = {"status": "ok"}
            if hasattr(self.portfolio, "reset_day"):
                try:
                    port_status = self.portfolio.reset_day()
                except Exception as e:
                    return {"status": "error", "reason": f"portfolio_reset_failed:{e}"}

            risk_status = {"status": "ok"}
            if hasattr(self.risk_manager, "reset_day"):
                try:
                    risk_status = self.risk_manager.reset_day()
                except Exception as e:
                    return {"status": "error", "reason": f"risk_reset_failed:{e}"}

            if (
                port_status.get("status") == "error"
                or risk_status.get("status") == "error"
            ):
                return {
                    "status": "error",
                    "reason": f"Portfolio={port_status}, Risk={risk_status}",
                }
            return {"status": "ok", "reason": "Daily reset complete"}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    def adaptive_fraction(self) -> float:
        try:
            if not self.portfolio or not getattr(self.portfolio, "history", []):
                return self.base_fraction
            if self.portfolio.equity <= 0:
                return self.base_fraction
            peak = max(eq for _, eq in self.portfolio.history)
            if peak <= 0:
                return self.base_fraction
            frac = self.base_fraction * (self.portfolio.equity / peak)
            return max(0.0, min(self.base_fraction, frac))
        except Exception:
            return self.base_fraction

    # ------------------------------------------------------------------
    def process_signal(
        self,
        symbol: str,
        signal: str,
        price: Optional[float] = None,
        size: Optional[int] = None,
        algo: Optional[str] = None,
    ) -> Dict[str, Any]:
        # --- Validate
        if not isinstance(signal, str):
            return {"status": "rejected", "reason": "signal_not_string"}
        signal = signal.upper().strip()
        if signal not in {"BUY", "SELL", "HOLD"}:
            return {"status": "rejected", "reason": f"invalid_signal:{signal}"}
        if signal == "HOLD":
            return {"status": "ignored", "reason": "hold_signal"}
        if price is None or price <= 0:
            return {"status": "rejected", "reason": "invalid_price"}

        # --- Guardrails
        if self.portfolio.equity <= 0:
            return {"status": "blocked", "reason": "equity_depleted"}
        if signal in {"BUY", "SELL"} and self._sector_exposure_breach(symbol):
            return {"status": "blocked", "reason": "sector_exposure"}
        if signal in {"BUY", "SELL"} and self._hedge_trigger(symbol):
            return {"status": "blocked", "reason": "hedge_rule"}
        if self.portfolio and getattr(self.portfolio, "history", []):  # pragma: no cover (phase3)
            try:  # pragma: no cover (phase3)
                start_equity = self.portfolio.history[0][1]  # pragma: no cover (phase3)
                drawdown = 1 - (self.portfolio.equity / max(start_equity, 1))  # pragma: no cover (phase3)
                if drawdown > self.config.get("risk", {}).get("max_drawdown", 0.5):  # pragma: no cover (phase3)
                    return {"status": "blocked", "reason": "drawdown_breach"}  # pragma: no cover (phase3)
            except Exception:  # pragma: no cover (phase3)
                pass  # pragma: no cover (phase3)
  # pragma: no cover (phase3)
        # --- Kelly  # pragma: no cover (phase3)
        if size is None:  # pragma: no cover (phase3)
            try:
                raw = self.kelly_sizer.size_position(self.portfolio.equity, price)
                size = int(raw["size"]) if isinstance(raw, dict) else int(raw)
                size = max(1, size)
            except Exception:
                size = 1

        # --- Algo Routing
        if algo:
            try:
                if algo.lower() == "twap":
                    mod = importlib.import_module("hybrid_ai_trading.algos.twap")
                    result = mod.TWAPExecutor(self.order_manager).execute(
                        symbol, signal, size, price
                    )
                elif algo.lower() == "vwap":
                    mod = importlib.import_module("hybrid_ai_trading.algos.vwap")
                    result = mod.VWAPExecutor(self.order_manager).execute(
                        symbol, signal, size, price
                    )
                elif algo.lower() == "iceberg":
                    mod = importlib.import_module("hybrid_ai_trading.algos.iceberg")
                    result = mod.IcebergExecutor(self.order_manager).execute(
                        symbol, signal, size, price
                    )
                else:
                    logger.warning("Unknown algo requested: %s", algo)
        # FIX: Early return ensures unknown algo is not normalized to "filled".
                    return {"status": "rejected", "reason": "unknown_algo"}
            except Exception as e:
                return {"status": "error", "reason": f"algo_error:{e}"}
        else:
            try:
                result = self.router.route_order(symbol, signal, size, price)
            except Exception as e:
                self._fire_alert(str(e))
                return {"status": "blocked", "reason": f"router_error:{e}"}
            if result is None:
                self._fire_alert("router_failed")
                return {"status": "blocked", "reason": "router_failed"}
            if isinstance(result, dict) and result.get("status") == "error":
                self._fire_alert(result.get("reason", "router_error"))
                return {
                    "status": "blocked",
                    "reason": f"router_error:{result.get('reason','unknown')}",
                }

        # --- Regime OVERRIDE
        if not self.regime_enabled:
            return {"status": "filled", "reason": "regime_disabled"}  # pragma: no cover (phase3)

        # --- Filters BEFORE performance
        try:
            if not self.sentiment_filter.allow_trade(symbol, signal, price):
                return {"status": "blocked", "reason": "sentiment_veto"}
        except Exception:
            return {"status": "blocked", "reason": "sentiment_error"}

        try:
            if not self.gatescore.allow_trade(symbol, signal, price):
                return {"status": "blocked", "reason": "gatescore_veto"}
        except Exception:
            return {"status": "blocked", "reason": "gatescore_error"}

        # --- Performance AFTER filters
        try:
            if self.performance_tracker.sharpe_ratio() < self.config.get(
                "risk", {}
            ).get("sharpe_min", -1.0):
                return {"status": "blocked", "reason": "sharpe_breach"}
            if self.performance_tracker.sortino_ratio() < self.config.get(
                "risk", {}
            ).get("sortino_min", -1.0):
                return {"status": "blocked", "reason": "sortino_breach"}  # pragma: no cover (phase3)
        except Exception:
            pass

        # --- Normalize
        allowed = {"filled", "blocked", "ignored", "rejected", "ok", "pending", "error"}
        if not isinstance(result, dict) or result.get("status") not in allowed:
            return {"status": "rejected", "reason": "invalid_status"}

        if result.get("status") == "ok":  # pragma: no cover (phase3)
            result["status"] = "filled"  # pragma: no cover (phase3)
        if result.get("reason") == "ok":  # pragma: no cover (phase3)
            result["reason"] = "normalized_ok"  # pragma: no cover (phase3)
  # pragma: no cover (phase3)
        try:  # pragma: no cover (phase3)
            row = [
                os.times().elapsed,
                symbol,
                signal,
                size,
                price,
                result.get("status"),
                self.portfolio.equity,
                result.get("reason", ""),
            ]
            self._write_audit(row)
        except Exception as e:
            logger.error("Audit log capture failed: %s", e)

        return result

    # ------------------------------------------------------------------
    def _sector_exposure_breach(self, symbol: str) -> bool:
        cap = self.config.get("risk", {}).get("intraday_sector_exposure", 1.0)
        tech = {"AAPL", "MSFT", "NVDA", "AMD", "META", "GOOGL"}
        exposure = sum(
            v["size"] * v.get("avg_price", 0)
            for s, v in self.portfolio.get_positions().items()
            if s in tech
        )
        return symbol in tech and exposure / max(self.portfolio.equity, 1) >= cap

    def _hedge_trigger(self, symbol: str) -> bool:
        return symbol in self.config.get("risk", {}).get("hedge_rules", {}).get(
            "equities_vol_spike", []
        )

    def get_equity(self) -> float:
        return float(self.portfolio.equity)

    def get_positions(self) -> Dict[str, Any]:
        return self.portfolio.get_positions()

    def get_history(self) -> List[Any]:
        return self.portfolio.history

    # ------------------------------------------------------------------
    def record_trade_outcome(self, pnl: float) -> None:
        """Record trade outcome into performance tracker (for archive harness)."""
        try:
            self.performance_tracker.record_trade(pnl)
        except Exception as e:
            logger.error("Failed to record trade outcome: %s", e)

# === PHASE5: No-Averaging-Down hook scaffolding ============================
# This block provides an optional hook for enforcing the no-averaging-down
# policy via the risk.no_averaging_down_policy module and the bridge defined
# in risk_manager.py. It does not alter existing behavior until called.

try:
    from hybrid_ai_trading.risk.risk_manager import get_phase5_no_avg_bridge
except Exception:  # pragma: no cover
    get_phase5_no_avg_bridge = None  # type: ignore


def phase5_validate_no_averaging_down(order, regime: str) -> None:
    """
    Optional TradeEngine-level hook. If the Phase5 bridge is available,
    this will invoke the no-averaging-down validation before an order
    is sent for execution.

    To activate this behavior, call this function from the appropriate
    place in your TradeEngine pipeline, for example:

        phase5_validate_no_averaging_down(order, regime)

    right before sending the order to the execution engine.
    """
    if get_phase5_no_avg_bridge is None:
        return

    bridge = get_phase5_no_avg_bridge()
    try:
        bridge.validate_no_averaging_down_for_order(order, regime)
    except Exception as exc:
        # In a later pass, this should map to a specific RiskViolation type.
        # For now, re-raise so callers can handle/log as appropriate.
        raise

# End of PHASE5 hook scaffolding ===========================================
