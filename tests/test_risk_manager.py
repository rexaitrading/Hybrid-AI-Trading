import unittest
from src.risk.risk_manager import RiskManager

class TestRiskManager(unittest.TestCase):

    def test_allows_profitable_trade(self):
        """Profitable trade should always be allowed"""
        rm = RiskManager(daily_loss_limit=-0.03, trade_loss_limit=-0.01)
        self.assertTrue(rm.check_trade(0.02))  # +2% profit

    def test_blocks_single_trade_loss(self):
        """Single trade loss exceeding trade limit should block"""
        rm = RiskManager(daily_loss_limit=-0.05, trade_loss_limit=-0.01)
        self.assertFalse(rm.check_trade(-0.02))  # -2% > -1% trade loss limit

    def test_blocks_daily_drawdown(self):
        """Accumulate losses until hitting daily loss limit"""
        rm = RiskManager(daily_loss_limit=-0.03, trade_loss_limit=None)
        self.assertTrue(rm.check_trade(-0.01))   # -1% ok
        self.assertTrue(rm.check_trade(-0.01))   # -2% ok
        self.assertFalse(rm.check_trade(-0.01))  # -3% hits daily limit

    def test_exact_trade_loss_limit(self):
        """Exact match with trade loss limit should block"""
        rm = RiskManager(daily_loss_limit=-0.05, trade_loss_limit=-0.01)
        self.assertFalse(rm.check_trade(-0.01))  # = -1%

    def test_exact_daily_loss_limit(self):
        """Exact match with daily loss limit should block"""
        rm = RiskManager(daily_loss_limit=-0.02, trade_loss_limit=None)
        self.assertTrue(rm.check_trade(-0.01))   # -1% ok
        self.assertFalse(rm.check_trade(-0.01))  # cumulative -2% blocked

    def test_none_trade_loss_limit(self):
        """If trade_loss_limit=None, only daily matters"""
        rm = RiskManager(daily_loss_limit=-0.03, trade_loss_limit=None)
        self.assertTrue(rm.check_trade(-0.02))   # allowed, since only daily is checked

    def test_none_daily_loss_limit(self):
        """If daily_loss_limit=None, only per-trade matters"""
        rm = RiskManager(daily_loss_limit=None, trade_loss_limit=-0.01)
        self.assertFalse(rm.check_trade(-0.02))  # trade exceeds limit
        self.assertTrue(rm.check_trade(0.05))    # profit always allowed

    def test_both_limits_none(self):
        """If both limits=None, always allow"""
        rm = RiskManager(daily_loss_limit=None, trade_loss_limit=None)
        self.assertTrue(rm.check_trade(-999))    # even huge loss allowed
        self.assertTrue(rm.check_trade(0.0))     # break-even allowed
        self.assertTrue(rm.check_trade(999))     # profit allowed

    def test_zero_return_trade(self):
        """Zero return should not block trades"""
        rm = RiskManager(daily_loss_limit=-0.01, trade_loss_limit=-0.01)
        self.assertTrue(rm.check_trade(0.0))     # break-even trade

    def test_accumulate_profits(self):
        """Multiple profitable trades accumulate daily PnL"""
        rm = RiskManager(daily_loss_limit=-0.05, trade_loss_limit=-0.01)
        self.assertTrue(rm.check_trade(0.02))    # +2%
        self.assertTrue(rm.check_trade(0.03))    # +5% total

    def test_reset_day(self):
        """reset_day() should reset cumulative PnL"""
        rm = RiskManager(daily_loss_limit=-0.02, trade_loss_limit=None)
        rm.check_trade(-0.01)                    # accumulate -1%
        rm.reset_day()
        self.assertEqual(rm.daily_pnl, 0.0)      # reset to zero
