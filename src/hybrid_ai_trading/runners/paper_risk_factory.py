from __future__ import annotations

from typing import Any, Dict

from hybrid_ai_trading.risk.kelly_sizer import KellySizer
from hybrid_ai_trading.risk.regime_detector import RegimeDetector
from hybrid_ai_trading.risk.risk_manager import RiskConfig, RiskManager
from hybrid_ai_trading.risk.sentiment_filter import SentimentFilter


def build_risk_stack(cfg: Dict[str, Any]) -> RiskManager:
    rsec = (cfg.get("risk") or {}) if isinstance(cfg, dict) else {}
    rc = RiskConfig(
        day_loss_cap_pct=rsec.get("day_loss_cap_pct"),
        per_trade_notional_cap=rsec.get("per_trade_notional_cap"),
        max_trades_per_day=rsec.get("max_trades_per_day"),
        max_consecutive_losers=rsec.get("max_consecutive_losers"),
        cooldown_bars=rsec.get("cooldown_bars"),
        max_drawdown_pct=rsec.get("max_drawdown_pct"),
        base_equity_fallback=rsec.get("base_equity_fallback", 100_000.0),
        fail_closed=bool(rsec.get("fail_closed", False)),
        max_portfolio_exposure=rsec.get("max_portfolio_exposure"),
        max_leverage=rsec.get("max_leverage"),
        equity=rsec.get("equity"),
    )
    rm = RiskManager(
        daily_loss_limit=rsec.get("daily_loss_limit"),
        max_portfolio_exposure=rc.max_portfolio_exposure,
        max_leverage=rc.max_leverage,
        equity=rc.equity,
        config=rc,
    )
    rm.kelly = KellySizer()
    rm.sent = SentimentFilter(enabled=True, model="vader", neutral_zone=0.1)
    rm.regime = RegimeDetector(enabled=True, lookback_days=90)
    return rm
