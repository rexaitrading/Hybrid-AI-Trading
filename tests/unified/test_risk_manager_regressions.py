import logging

from hybrid_ai_trading.risk.risk_manager import RiskManager


def test_control_signal_respects_absolute_daily_limit(caplog):
    rm = RiskManager(daily_loss_limit=-0.01)
    rm.daily_pnl = -1.0
    caplog.set_level(logging.WARNING)
    assert rm.control_signal("BUY") == "HOLD"
    assert "daily_loss" in caplog.text


def test_reset_day_failure_has_reason(caplog):
    class BadPort:
        def reset_day(self):
            raise RuntimeError("boom!")

    rm = RiskManager(portfolio=BadPort())
    caplog.set_level(logging.ERROR)
    out = rm.reset_day()
    assert out["status"] == "error" and "reason" in out


def test_leverage_log_lowercase(caplog):
    class P:
        def get_leverage(self):
            return 10

        def get_total_exposure(self):
            return 0

    rm = RiskManager(portfolio=P(), max_leverage=5, equity=100000)
    caplog.set_level(logging.WARNING)
    assert not rm.check_trade("AAPL", "BUY", 1, 1000)
    assert "leverage" in caplog.text  # lowercase token must match
