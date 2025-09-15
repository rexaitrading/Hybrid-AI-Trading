"""
Trade Engine (Hybrid AI Quant Pro v13.2 – Hedge-Fund Grade, AAA Polished)
------------------------------------------------------------------------
- Dual audit logging (primary + backup)
- Enforces intraday sector exposure & hedge rules
- GateScore + Sentiment veto integration
- Smart router with retries + timeout
- Slack/Telegram/Email alert stubs
- Fully integrated with risk guardrails & execution layer
"""

import logging, csv, os, time
from typing import Dict, Optional, Any
from datetime import datetime
import requests, smtplib
from email.mime.text import MIMEText

from hybrid_ai_trading.execution.portfolio_tracker import PortfolioTracker
from hybrid_ai_trading.execution.order_manager import OrderManager
from hybrid_ai_trading.execution.latency_monitor import LatencyMonitor
from hybrid_ai_trading.execution.smart_router import SmartOrderRouter
from hybrid_ai_trading.risk.risk_manager import RiskManager
from hybrid_ai_trading.risk.kelly_sizer import KellySizer
from hybrid_ai_trading.risk.sentiment_filter import SentimentFilter
from hybrid_ai_trading.risk.gatescore import GateScore
from hybrid_ai_trading.risk.regime_detector import RegimeDetector
from hybrid_ai_trading.performance_tracker import PerformanceTracker

logger = logging.getLogger(__name__)


class TradeEngine:
    def __init__(self, config: dict,
                 portfolio: Optional[PortfolioTracker] = None,
                 brokers: Optional[dict] = None):
        self.config = config or {}
        self.portfolio = portfolio or PortfolioTracker(
            self.config.get("risk", {}).get("equity", 100000.0)
        )

        # --- Risk Manager ---
        risk_cfg = self.config.get("risk", {})
        self.risk_manager = RiskManager(
            daily_loss_limit=risk_cfg.get("max_daily_loss", -0.03),
            trade_loss_limit=risk_cfg.get("max_position_risk", -0.01),
            max_leverage=risk_cfg.get("max_leverage", 5.0),
            equity=risk_cfg.get("equity", 100000.0),
            max_portfolio_exposure=risk_cfg.get("max_portfolio_exposure", 0.5),
            portfolio=self.portfolio,
        )

        # --- Kelly Sizer ---
        kelly_cfg = risk_cfg.get("kelly", {})
        self.base_fraction = kelly_cfg.get("fraction", 1.0)
        self.kelly_sizer = KellySizer(
            win_rate=kelly_cfg.get("win_rate", 0.5),
            payoff=kelly_cfg.get("payoff", 1.0),
            fraction=self.base_fraction,
        )

        # --- Filters ---
        sent_cfg = self.config.get("sentiment", {})
        self.sentiment_filter = SentimentFilter(
            enabled=self.config.get("features", {}).get("enable_emotional_filter", True),
            threshold=sent_cfg.get("threshold", 0.8),
            neutral_zone=sent_cfg.get("neutral_zone", 0.2),
            bias=sent_cfg.get("bias", "none"),
            model=sent_cfg.get("model", "vader"),
            smoothing=sent_cfg.get("smoothing", 1),
        )

        gs_cfg = self.config.get("gatescore", {})
        self.gatescore = GateScore(
            enabled=gs_cfg.get("enabled", True),
            threshold=gs_cfg.get("threshold", 0.85),
            models=gs_cfg.get("models", ["sentiment", "price", "macro", "regime"]),
            weights=gs_cfg.get("weights", {}),
            adaptive=gs_cfg.get("adaptive", True),
        )

        reg_cfg = dict(self.config.get("regime", {}))
        self.regime_enabled = reg_cfg.pop("enabled", True)
        self.regime_detector = RegimeDetector(**reg_cfg) if self.regime_enabled else None

        # --- Performance Tracker ---
        self.performance_tracker = PerformanceTracker(window=50)

        # --- Order Manager ---
        self.order_manager = OrderManager(
            risk_manager=self.risk_manager,
            portfolio=self.portfolio,
            dry_run=self.config.get("mode", "paper") != "live",
            costs=self.config.get("costs", {}),
            use_paper_simulator=self.config.get("use_paper_simulator", False),
        )

        # --- Execution Layer ---
        self.latency_monitor = LatencyMonitor(
            threshold_ms=self.config.get("alerts", {}).get("latency_threshold_ms", 500)
        )
        self.router = SmartOrderRouter(
            brokers or {"alpaca": self.order_manager},
            self.config.get("execution", {}),
        )

        # --- Audit Logs ---
        self.audit_log = self.config.get("audit_log_path", "logs/trade_blotter.csv")
        self.backup_log = self.config.get("backup_log_path", "logs/trade_blotter_backup.csv")
        for path in [self.audit_log, self.backup_log]:
            folder = os.path.dirname(path) or "."
            os.makedirs(folder, exist_ok=True)
            if not os.path.exists(path):
                with open(path, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(
                        ["time", "symbol", "side", "size", "price", "status", "equity", "reason"]
                    )

        logger.info("✅ TradeEngine v13.2 initialized")

    # ------------------------------------------------------------------
    def adaptive_fraction(self) -> float:
        """Scale Kelly fraction dynamically with drawdown."""
        history = self.portfolio.history
        if not history or self.portfolio.equity <= 0:
            return self.base_fraction
        peak = max(eq for _, eq in history)
        if peak <= 0:
            return self.base_fraction
        dd = (peak - self.portfolio.equity) / peak
        if dd > 0.3:
            return self.base_fraction * 0.5
        elif dd > 0.1:
            return self.base_fraction * 0.75
        return self.base_fraction

    # ------------------------------------------------------------------
    def process_signal(
        self, symbol: str, signal: str, price: float,
        size: Optional[int] = None, algo: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process trading signal with risk/filters and route order."""

        # --- Guardrails ---
        sharpe_min = self.config.get("risk", {}).get("sharpe_min", -1)
        max_dd = self.config.get("risk", {}).get("max_drawdown", 1.0)
        if self.portfolio.equity <= 0:
            return {"status": "blocked", "reason": "Equity depleted"}
        if self.performance_tracker.sharpe_ratio() < sharpe_min:
            return {"status": "blocked", "reason": "Sharpe below min"}
        if self.portfolio.get_drawdown() > max_dd:
            return {"status": "blocked", "reason": "Drawdown exceeded"}

        # --- Sector / Hedge ---
        if self._sector_exposure_breach(symbol):
            return {"status": "blocked", "reason": "Sector exposure breach"}
        if self._hedge_trigger(symbol):
            return {"status": "blocked", "reason": "Hedge rule triggered"}

        # --- Validate ---
        if not isinstance(signal, str):
            return {"status": "rejected", "reason": "Signal not string"}
        signal = signal.upper().strip()
        if signal not in {"BUY", "SELL", "HOLD"}:
            return {"status": "rejected", "reason": f"Invalid signal {signal}"}
        if signal == "HOLD":
            return {"status": "ignored", "reason": "Signal = HOLD"}
        if price is None or price <= 0:
            return {"status": "rejected", "reason": "Invalid price"}

        # --- GateScore veto ---
        try:
            if self.gatescore and not self.gatescore.allow_trade(symbol, signal, price):
                return {"status": "blocked", "reason": "GateScore veto"}
        except Exception as e:
            logger.error(f"GateScore exception: {e}")
            return {"status": "blocked", "reason": "GateScore exception"}

        # --- Sentiment veto ---
        try:
            if self.sentiment_filter and not self.sentiment_filter.allow_trade("headline", side=signal):
                return {"status": "blocked", "reason": "Sentiment veto"}
        except Exception as e:
            logger.error(f"Sentiment exception: {e}")
            return {"status": "blocked", "reason": "Sentiment exception"}

        # --- Kelly sizing ---
        if size is None:
            try:
                size = max(1, int(self.kelly_sizer.size_position(self.portfolio.equity, price)))
            except Exception as e:
                logger.error(f"⚠️ Kelly sizing failed: {e}", exc_info=True)
                size = 1

        # --- Algo Routing ---
        if algo:
            try:
                if algo.lower() == "twap":
                    from hybrid_ai_trading.algos.twap import TWAPExecutor
                    return TWAPExecutor(self.order_manager).execute(symbol, signal, size, price)
                elif algo.lower() == "vwap":
                    from hybrid_ai_trading.algos.vwap import VWAPExecutor
                    return VWAPExecutor(self.order_manager).execute(symbol, signal, size, price)
                elif algo.lower() == "iceberg":
                    from hybrid_ai_trading.algos.iceberg import IcebergExecutor
                    return IcebergExecutor(self.order_manager).execute(symbol, signal, size, price)
                else:
                    logger.warning(f"⚠️ Unknown algo {algo}, falling back to SmartRouter")
            except Exception as e:
                return {"status": "error", "reason": f"Algo {algo} failure: {e}"}

        # --- Smart Router ---
        retries = self.config.get("execution", {}).get("max_order_retries", 1)
        timeout_sec = self.config.get("execution", {}).get("timeout_sec", 5)
        result = None
        for attempt in range(retries):
            try:
                result = self.latency_monitor.measure(
                    self.router.route_order, symbol, signal, size, price, timeout_sec=timeout_sec
                )
                if isinstance(result, dict) and result.get("status") != "error":
                    break
            except Exception as e:
                logger.error(f"Retry {attempt+1}/{retries} failed: {e}")
                time.sleep(0.2)

        # --- Audit log ---
        self._write_audit(symbol, signal, size, price, result)

        # --- Normalize ---
        if isinstance(result, dict):
            return result
        return {"status": "error", "reason": "Router failure"}

    # ------------------------------------------------------------------
    def _sector_exposure_breach(self, symbol: str) -> bool:
        cap = self.config.get("risk", {}).get("intraday_sector_exposure", 1.0)
        tech = {"AAPL", "MSFT", "NVDA", "AMD", "META", "GOOGL"}
        if symbol in tech:
            exposure = sum(v["size"] for s, v in self.portfolio.get_positions().items() if s in tech)
            return exposure / max(self.portfolio.equity, 1) > cap
        return False

    def _hedge_trigger(self, symbol: str) -> bool:
        hedge_rules = self.config.get("risk", {}).get("hedge_rules", {})
        return symbol in hedge_rules.get("equities_vol_spike", [])

    def _write_audit(self, symbol, side, size, price, result):
        try:
            status = result.get("status", "error") if isinstance(result, dict) else "error"
            reason = result.get("reason", "router error") if isinstance(result, dict) else "router error"
            row = [datetime.utcnow().isoformat(), symbol, side, size, price, status, self.portfolio.equity, reason]
            for path in [self.audit_log, self.backup_log]:
                with open(path, "a", newline="") as f:
                    csv.writer(f).writerow(row)
        except Exception as e:
            logger.error(f"Audit log write failed: {e}")

    # ------------------------------------------------------------------
    def reset_day(self):
        try:
            self.risk_manager.reset_day()
            return {"status": "ok", "reason": "Daily reset complete"}
        except Exception as e:
            return {"status": "error", "reason": f"RiskManager reset failed: {e}"}

    def get_positions(self): return self.portfolio.get_positions()
    def get_equity(self): return self.portfolio.equity
    def get_history(self): return self.portfolio.history

    # ------------------------------------------------------------------
    def alert(self, message: str):
        alerts = self.config.get("alerts", {})
        if alerts.get("slack_webhook_env") and os.getenv(alerts["slack_webhook_env"]):
            try:
                requests.post(os.getenv(alerts["slack_webhook_env"]), json={"text": message})
            except Exception as e:
                logger.error(f"Slack alert failed: {e}")

        if alerts.get("telegram_bot_env") and alerts.get("telegram_chat_id_env"):
            bot = os.getenv(alerts["telegram_bot_env"])
            chat_id = os.getenv(alerts["telegram_chat_id_env"])
            if bot and chat_id:
                try:
                    requests.get(
                        f"https://api.telegram.org/bot{bot}/sendMessage",
                        params={"chat_id": chat_id, "text": message},
                    )
                except Exception as e:
                    logger.error(f"Telegram alert failed: {e}")

        if alerts.get("email_env") and os.getenv(alerts["email_env"]):
            try:
                msg = MIMEText(message)
                msg["Subject"] = "HybridAI Trading Alert"
                msg["From"] = os.getenv(alerts["email_env"])
                msg["To"] = os.getenv(alerts["email_env"])
                with smtplib.SMTP("localhost") as s:
                    s.send_message(msg)
            except Exception as e:
                logger.error(f"Email alert failed: {e}")
