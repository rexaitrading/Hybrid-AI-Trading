"""
Unit Tests: Market Logger
(Hybrid AI Quant Pro v9.6 – Hedge-Fund OE Grade, 100% Coverage)
----------------------------------------------------------------
Covers:
- ImportError when ib_insync not available
- connect() success and failure branches
- start_logging:
    * not connected error
    * subscribes and logs ticks (header + row written)
    * subscription failure branch
    * KeyboardInterrupt shutdown branch
    * generic Exception in loop branch
    * log_tick error branch
- shutdown() unsubscribes and disconnects (success + exception + finally branch)
- CLI main() path (IB None exits, IB present runs stubbed connect/logging)
"""

import csv
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import hybrid_ai_trading.execution.market_logger as ml


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
class FakeEvent(list):
    """Fake event handler supporting += operator like ib_insync.Event."""
    def __iadd__(self, other):
        self.append(other)
        return self


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------
def test_importerror_if_no_ib(monkeypatch):
    monkeypatch.setattr(ml, "IB", None)
    monkeypatch.setattr(ml, "Stock", None)
    with pytest.raises(ImportError):
        ml.MarketLogger(["AAPL"])


def test_connect_success(monkeypatch):
    fake_ib = MagicMock()
    monkeypatch.setattr(ml, "IB", MagicMock(return_value=fake_ib))
    monkeypatch.setattr(ml, "Stock", object)

    mlogger = ml.MarketLogger(["AAPL"])
    mlogger.connect(port=7496, client_id=42)

    fake_ib.connect.assert_called_once()
    assert mlogger.ib == fake_ib


def test_connect_failure(monkeypatch):
    fake_ib = MagicMock()
    fake_ib.connect.side_effect = Exception("boom")
    monkeypatch.setattr(ml, "IB", MagicMock(return_value=fake_ib))
    monkeypatch.setattr(ml, "Stock", object)

    mlogger = ml.MarketLogger(["AAPL"])
    with pytest.raises(RuntimeError):
        mlogger.connect()


def test_start_logging_not_connected(monkeypatch):
    """Covers the `if not self.ib` branch."""
    monkeypatch.setattr(ml, "IB", MagicMock())
    monkeypatch.setattr(ml, "Stock", MagicMock())
    mlogger = ml.MarketLogger(["AAPL"])
    # deliberately do not connect
    with pytest.raises(RuntimeError):
        mlogger.start_logging()


def test_start_logging_and_write_csv(tmp_path, monkeypatch, caplog):
    fake_ib = MagicMock()
    fake_ticker = MagicMock()
    fake_ticker.last, fake_ticker.bid, fake_ticker.ask = 123.45, 123.40, 123.50
    fake_ticker.updateEvent = FakeEvent()
    fake_ib.reqMktData.return_value = fake_ticker

    monkeypatch.setattr(ml, "IB", MagicMock(return_value=fake_ib))
    monkeypatch.setattr(ml, "Stock", MagicMock(return_value=MagicMock()))

    mlogger = ml.MarketLogger(["AAPL"], outdir=tmp_path)
    mlogger.ib = fake_ib

    caplog.set_level(logging.DEBUG, logger="hybrid_ai_trading.execution.market_logger")
    fake_ib.run = MagicMock(side_effect=KeyboardInterrupt)

    mlogger.start_logging()  # stops at KeyboardInterrupt → shutdown called

    # Fire tick manually
    for cb in fake_ticker.updateEvent:
        cb()

    csv_file = tmp_path / "AAPL_ticks.csv"
    with open(csv_file, newline="") as fh:
        lines = list(csv.reader(fh))

    assert lines[0] == ["timestamp", "symbol", "last", "bid", "ask"]
    assert lines[1][1] == "AAPL"
    assert any("Tick logged" in rec.message for rec in caplog.records)


def test_start_logging_logtick_error(tmp_path, monkeypatch, caplog):
    """Covers the inner except block when log_tick fails."""
    fake_ib = MagicMock()
    fake_ticker = MagicMock()
    fake_ticker.last = 123.45
    fake_ticker.updateEvent = FakeEvent()
    fake_ib.reqMktData.return_value = fake_ticker

    monkeypatch.setattr(ml, "IB", MagicMock(return_value=fake_ib))
    monkeypatch.setattr(ml, "Stock", MagicMock(return_value=MagicMock()))

    mlogger = ml.MarketLogger(["AAPL"], outdir=tmp_path)
    mlogger.ib = fake_ib

    real_writer = csv.writer

    class FlakyWriter:
        def __init__(self, f): self._w = real_writer(f)
        def writerow(self, row):
            if "AAPL" in row:  # fail only on tick rows, not header
                raise Exception("tick fail")
            return self._w.writerow(row)

    monkeypatch.setattr(csv, "writer", FlakyWriter)

    fake_ib.run = MagicMock(side_effect=KeyboardInterrupt)
    mlogger.start_logging()

    # Fire tick manually to trigger error
    for cb in fake_ticker.updateEvent:
        cb()

    assert "Failed to log tick" in caplog.text


def test_start_logging_generic_exception(monkeypatch, caplog):
    """Covers outer exception in start_logging (non-KeyboardInterrupt)."""
    fake_ib = MagicMock()
    fake_ticker = MagicMock()
    fake_ticker.updateEvent = FakeEvent()
    fake_ib.reqMktData.return_value = fake_ticker
    fake_ib.run.side_effect = Exception("boom")

    monkeypatch.setattr(ml, "IB", MagicMock(return_value=fake_ib))
    monkeypatch.setattr(ml, "Stock", MagicMock(return_value=MagicMock()))

    mlogger = ml.MarketLogger(["AAPL"])
    mlogger.ib = fake_ib

    caplog.set_level(logging.ERROR, logger="hybrid_ai_trading.execution.market_logger")
    mlogger.start_logging()
    assert "stopped unexpectedly" in caplog.text


def test_start_logging_subscription_failure(monkeypatch, caplog):
    fake_ib = MagicMock()
    fake_ib.reqMktData.side_effect = Exception("sub fail")

    monkeypatch.setattr(ml, "IB", MagicMock(return_value=fake_ib))
    monkeypatch.setattr(ml, "Stock", MagicMock(return_value=MagicMock()))

    mlogger = ml.MarketLogger(["AAPL"])
    mlogger.ib = fake_ib

    caplog.set_level(logging.ERROR, logger="hybrid_ai_trading.execution.market_logger")
    fake_ib.run = MagicMock(side_effect=KeyboardInterrupt)

    mlogger.start_logging()
    assert "Subscription failed" in caplog.text


def test_start_logging_keyboard_interrupt(monkeypatch, caplog):
    fake_ib = MagicMock()
    fake_ticker = MagicMock()
    fake_ticker.updateEvent = FakeEvent()
    fake_ib.reqMktData.return_value = fake_ticker

    monkeypatch.setattr(ml, "IB", MagicMock(return_value=fake_ib))
    monkeypatch.setattr(ml, "Stock", MagicMock(return_value=MagicMock()))

    mlogger = ml.MarketLogger(["AAPL"])
    mlogger.ib = fake_ib

    caplog.set_level(logging.INFO, logger="hybrid_ai_trading.execution.market_logger")
    fake_ib.run = MagicMock(side_effect=KeyboardInterrupt)

    mlogger.start_logging()
    assert "Interrupted by user" in caplog.text
    assert "Disconnected from IBKR" in caplog.text


def test_shutdown_success(monkeypatch):
    fake_ib = MagicMock()
    fake_ticker = MagicMock(contract="FAKE")
    monkeypatch.setattr(ml, "IB", MagicMock(return_value=fake_ib))
    monkeypatch.setattr(ml, "Stock", object)

    mlogger = ml.MarketLogger(["AAPL"])
    mlogger.ib = fake_ib
    mlogger.subscriptions = {"AAPL": fake_ticker}

    mlogger.shutdown()

    fake_ib.cancelMktData.assert_called_once_with("FAKE")
    fake_ib.disconnect.assert_called_once()
    assert mlogger.subscriptions == {}
    assert mlogger.ib is None


def test_shutdown_with_exceptions(monkeypatch, caplog):
    fake_ib = MagicMock()
    fake_ib.cancelMktData.side_effect = Exception("cancel fail")
    fake_ib.disconnect.side_effect = Exception("disconnect fail")
    fake_ticker = MagicMock(contract="FAKE")

    monkeypatch.setattr(ml, "IB", MagicMock(return_value=fake_ib))
    monkeypatch.setattr(ml, "Stock", object)

    mlogger = ml.MarketLogger(["AAPL"])
    mlogger.ib = fake_ib
    mlogger.subscriptions = {"AAPL": fake_ticker}

    caplog.set_level(logging.WARNING, logger="hybrid_ai_trading.execution.market_logger")
    mlogger.shutdown()

    assert "unsubscribe" in caplog.text or "disconnect" in caplog.text


def test_cli_main_exits(monkeypatch):
    """Covers CLI main() branch when IB is None."""
    monkeypatch.setattr(ml, "IB", None)
    monkeypatch.setattr(ml, "Stock", None)
    monkeypatch.setattr(ml, "MarketLogger", MagicMock())

    with patch.object(sys, "exit") as mock_exit:
        ml.main()
        mock_exit.assert_called_once()


def test_cli_main_runs_with_ib(monkeypatch):
    """Covers CLI main() branch when IB is present."""
    fake_logger = MagicMock()
    monkeypatch.setattr(ml, "IB", MagicMock())
    monkeypatch.setattr(ml, "Stock", MagicMock())
    monkeypatch.setattr(ml, "MarketLogger", MagicMock(return_value=fake_logger))

    fake_logger.connect = MagicMock()
    fake_logger.start_logging = MagicMock()

    ml.main()
    fake_logger.connect.assert_called_once()
    fake_logger.start_logging.assert_called_once()
