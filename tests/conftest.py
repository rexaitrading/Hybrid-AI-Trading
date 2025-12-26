from __future__ import annotations

import sys
import pytest


@pytest.fixture(autouse=True)
def _restore_algos_modules():
    """
    Prevent cross-test leakage via sys.modules injection for hybrid_ai_trading.algos.*.
    Many tests replace sys.modules entries to simulate algo executors; this fixture
    snapshots and restores those entries around each test.
    """
    prefix = "hybrid_ai_trading.algos."
    before = {k: sys.modules.get(k) for k in list(sys.modules.keys()) if k.startswith(prefix)}
    yield
    # Remove new keys
    after_keys = [k for k in list(sys.modules.keys()) if k.startswith(prefix)]
    for k in after_keys:
        if k not in before:
            sys.modules.pop(k, None)
    # Restore prior objects
    for k, v in before.items():
        if v is None:
            sys.modules.pop(k, None)
        else:
            sys.modules[k] = v


@pytest.fixture()
def TradeEngineClass():
    # TODO: update import path to where TradeEngine actually lives
    from hybrid_ai_trading.trade_engine import TradeEngine
    return TradeEngine
