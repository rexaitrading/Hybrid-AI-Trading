import unittest
from unittest.mock import patch
from src.signals.breakout_v1 import breakout_signal

class TestBreakoutSignal(unittest.TestCase):

    @patch("src.signals.breakout_v1.get_ohlcv_latest")
    def test_breakout_detected(self, mock_get):
        """Price breaks above resistance → BUY"""
        mock_get.return_value = [
            {"price_open": 100, "price_high": 101, "price_low": 99, "price_close": 100},
            {"price_open": 101, "price_high": 102, "price_low": 100, "price_close": 102},
            {"price_open": 108, "price_high": 111, "price_low": 107, "price_close": 110},
        ]
        signal = breakout_signal("FAKE")
        self.assertEqual(signal, "BUY")

    @patch("src.signals.breakout_v1.get_ohlcv_latest")
    def test_no_breakout(self, mock_get):
        """Prices flat → HOLD"""
        mock_get.return_value = [
            {"price_open": 100, "price_high": 101, "price_low": 99, "price_close": 100},
            {"price_open": 101, "price_high": 102, "price_low": 100, "price_close": 101},
            {"price_open": 100, "price_high": 101, "price_low": 99, "price_close": 100},
        ]
        signal = breakout_signal("FAKE")
        self.assertEqual(signal, "HOLD")

    @patch("src.signals.breakout_v1.get_ohlcv_latest")
    def test_false_breakout(self, mock_get):
        """Spike then revert → HOLD"""
        mock_get.return_value = [
            {"price_open": 100, "price_high": 101, "price_low": 99, "price_close": 100},
            {"price_open": 110, "price_high": 111, "price_low": 109, "price_close": 110},
            {"price_open": 100, "price_high": 101, "price_low": 99, "price_close": 100},
        ]
        signal = breakout_signal("FAKE")
        self.assertEqual(signal, "HOLD")

    @patch("src.signals.breakout_v1.get_ohlcv_latest")
    def test_breakdown_detected(self, mock_get):
        """Price breaks below support → SELL"""
        mock_get.return_value = [
            {"price_open": 100, "price_high": 101, "price_low": 99, "price_close": 100},
            {"price_open": 98, "price_high": 99, "price_low": 97, "price_close": 98},
            {"price_open": 90, "price_high": 91, "price_low": 89, "price_close": 90},
        ]
        signal = breakout_signal("FAKE")
        self.assertEqual(signal, "SELL")

    @patch("src.signals.breakout_v1.get_ohlcv_latest")
    def test_short_history(self, mock_get):
        """Not enough bars → HOLD"""
        mock_get.return_value = [
            {"price_open": 100, "price_high": 101, "price_low": 99, "price_close": 100}
        ]
        signal = breakout_signal("FAKE")
        self.assertEqual(signal, "HOLD")

