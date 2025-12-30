from __future__ import annotations

import datetime as _dt
import os

import pytest

from hybrid_ai_trading.broker import ib_safe


REAL_DATETIME = _dt.datetime


class _FakeDateTime:
    @classmethod
    def now(cls):
        # Saturday
        return REAL_DATETIME(2025, 1, 4, 12, 0, 0)

    @staticmethod
    def datetime(*a, **k):
        return _dt.datetime(*a, **k)


def test_assert_live_allowed_does_not_weekend_block_under_pytest(monkeypatch):
    # Force "live intent" path
    monkeypatch.setenv("HAT_IS_PAPER", "0")
    monkeypatch.delenv("HAT_LIVE_DISABLED", raising=False)
    monkeypatch.delenv("HAT_CONFIRM_LIVE", raising=False)

    # Ensure pytest marker is present (what ib_safe checks)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "unit_test::test")

    # Monkeypatch datetime used inside ib_safe._assert_live_allowed
    import datetime as _real_dt
    monkeypatch.setattr(_real_dt, "datetime", _FakeDateTime)

    # Should NOT raise weekend block
    ib_safe._assert_live_allowed(ctx=None)


def test_assert_live_allowed_weekend_blocks_without_pytest_marker(monkeypatch):
    monkeypatch.setenv("HAT_IS_PAPER", "0")
    monkeypatch.delenv("HAT_LIVE_DISABLED", raising=False)
    monkeypatch.delenv("HAT_CONFIRM_LIVE", raising=False)

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    import datetime as _real_dt
    monkeypatch.setattr(_real_dt, "datetime", _FakeDateTime)

    with pytest.raises(RuntimeError):
        ib_safe._assert_live_allowed(ctx=None)
