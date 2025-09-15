"""
Unit Tests: SmartOrderRouter (Hybrid AI Quant Pro v3.9 – 100% Coverage)
=======================================================================
Covers every branch of smart_router.py.
"""

import pytest
import time
import logging
from hybrid_ai_trading.execution.smart_router import SmartOrderRouter


# --- Dummy Broker Clients ---------------------------------------------
class DummyClient:
    def __init__(self, behavior="filled"):
        self.behavior = behavior

    def submit_order(self, *a, **k):
        if self.behavior == "error":
            raise Exception("submit fail")
        if self.behavior == "slow":
            time.sleep(0.02)
            return {"status": "filled"}  # latency warning path
        if self.behavior == "dict_no_status":
            return {"reason": "forced veto"}
        if self.behavior == "dict_unknown":
            return {"status": "nonsense", "reason": "custom veto"}
        if self.behavior == "dict_empty":
            return {}
        if self.behavior == "nonsense":
            return 12345
        if self.behavior == "error_dict":
            return {"status": "error", "reason": "explicit error"}
        return {"status": self.behavior, "broker": "dummy"}


# --- Fixtures ---------------------------------------------------------
@pytest.fixture
def brokers():
    return {
        "alpaca": DummyClient("filled"),
        "binance": DummyClient("pending"),
        "polygon": DummyClient("blocked"),
    }


@pytest.fixture
def router(brokers):
    return SmartOrderRouter(
        brokers,
        config={
            "alerts": {"latency_threshold_ms": 1},
            "execution": {
                "max_order_retries": 2,
                "timeout_sec": 0.01,
                "max_latency_breaches": 2,
            },
        },
    )


# --- Tests: scoring / ranking / choose_route --------------------------
def test_score_and_rank_brokers(router):
    scores = {b: router.score_broker(b) for b in router.brokers}
    assert all(isinstance(v, float) for v in scores.values())
    ranked = router.rank_brokers()
    assert set(ranked) == set(router.brokers)


def test_choose_route_crypto_equity_and_fallback(brokers):
    r = SmartOrderRouter(brokers)
    assert r.choose_route("BTC/USDT") == "binance"
    assert r.choose_route("SPY") == "polygon"
    assert r.choose_route("XYZ") == "alpaca"  # Test fallback to alpaca
    r2 = SmartOrderRouter({"other": DummyClient()})
    assert r2.choose_route("XYZ") == "other"
    r = SmartOrderRouter(brokers)
    assert r.choose_route("BTC/USDT") == "binance"
    assert r.choose_route("SPY") == "polygon"
    r2 = SmartOrderRouter({"other": DummyClient()})
    assert r2.choose_route("XYZ") == "other"


# --- Tests: timeout wrapper -------------------------------------------
def test_timeout_wrapper_success_and_exception(router):
    assert router._timeout_wrapper(lambda: 42) == 42
    result = router._timeout_wrapper(lambda: (_ for _ in ()).throw(Exception("boom")))
    assert result["status"] == "blocked"
    # Test successful execution without exceptions
    assert router._timeout_wrapper(lambda: "success") == "success"
    assert router._timeout_wrapper(lambda: 42) == 42
    result = router._timeout_wrapper(lambda: (_ for _ in ()).throw(Exception("boom")))
    assert result["status"] == "blocked"


def test_timeout_wrapper_timeout(router):
    def slow(): time.sleep(0.02)
    with pytest.raises(TimeoutError):
        router._timeout_wrapper(slow, timeout=0.001)


# --- Tests: route_order success / failure paths -----------------------
def test_route_order_success_variants():
    r = SmartOrderRouter({"alpaca": DummyClient("filled")})
    assert r.route_order("AAPL", "BUY", 1, 100)["status"] == "filled"

    r = SmartOrderRouter({"alpaca": DummyClient("pending")})
    assert r.route_order("AAPL", "BUY", 1, 100)["status"] == "pending"

    r = SmartOrderRouter({"alpaca": DummyClient("rejected")})
    assert r.route_order("AAPL", "BUY", 1, 100)["status"] == "blocked"

    r = SmartOrderRouter({"alpaca": DummyClient("blocked")})
    assert r.route_order("AAPL", "BUY", 1, 100)["status"] == "blocked"


def test_route_order_dict_variants(caplog):
    r = SmartOrderRouter({"odd": DummyClient("dict_no_status")})
    res = r.route_order("AAPL", "BUY", 1, 100)
    assert res["status"] == "blocked"

    r = SmartOrderRouter({"odd": DummyClient("dict_unknown")})
    caplog.set_level(logging.WARNING, logger="hybrid_ai_trading.execution.smart_router")
    res = r.route_order("AAPL", "BUY", 1, 100)
    assert res["status"] == "blocked"
    assert any("custom veto" in rec.message for rec in caplog.records)

    r = SmartOrderRouter({"odd": DummyClient("dict_empty")})
    caplog.set_level(logging.WARNING, logger="hybrid_ai_trading.execution.smart_router")
    res = r.route_order("AAPL", "BUY", 1, 100)
    assert res["status"] == "blocked"
    assert any("Unknown broker veto" in rec.message for rec in caplog.records)

    r = SmartOrderRouter({"odd": DummyClient("error_dict")})
    res = r.route_order("AAPL", "BUY", 1, 100)
    assert res["status"] == "blocked"
    assert res["reason"] in {"All brokers failed", "explicit error"}


def test_route_order_non_dict_result():
    r = SmartOrderRouter({"odd": DummyClient("nonsense")})
    res = r.route_order("AAPL", "BUY", 1, 100)
    assert res["status"] == "blocked"
    assert res["reason"] == "All brokers failed"


def test_route_order_exception_and_failover(caplog):
    brokers = {
        "alpaca": DummyClient("error"),
        "binance": DummyClient("error"),
        "polygon": DummyClient("error"),
    }
    r = SmartOrderRouter(brokers)
    caplog.set_level(logging.ERROR, logger="hybrid_ai_trading.execution.smart_router")
    res = r.route_order("AAPL", "BUY", 1, 100)
    assert res["status"] == "blocked"
    assert res["reason"] == "All brokers failed"
    assert any("All brokers failed" in rec.message for rec in caplog.records)
    # Test all brokers fail due to exceptions
    brokers = {
        "alpaca": DummyClient("error"),
        "binance": DummyClient("error"),
        "polygon": DummyClient("error"),
    }
    r = SmartOrderRouter(brokers)
    res = r.route_order("AAPL", "BUY", 1, 100)
    assert res["status"] == "blocked"
    assert res["reason"] == "All brokers failed"
    brokers = {
        "alpaca": DummyClient("error"),
        "binance": DummyClient("error"),
        "polygon": DummyClient("error"),
    }
    r = SmartOrderRouter(brokers)
    caplog.set_level(logging.ERROR, logger="hybrid_ai_trading.execution.smart_router")
    res = r.route_order("AAPL", "BUY", 1, 100)
    assert res["status"] == "blocked"
    assert res["reason"] == "All brokers failed"
    assert any("All brokers failed" in rec.message for rec in caplog.records)


# --- Tests: latency warnings / escalation -----------------------------
def test_latency_warning_direct_return_dict():
    class SlowDictClient:
        def submit_order(self, *a, **k):
            time.sleep(0.02)
            return {"status": "odd", "reason": "dict from warning"}

    r = SmartOrderRouter(
        {"alpaca": SlowDictClient()},
        config={"alerts": {"latency_threshold_ms": 1}, "execution": {"max_latency_breaches": 10}},
    )
    res = r.route_order("AAPL", "BUY", 1, 100)
    assert res["status"] == "warning"
    assert isinstance(res["result"], dict)
    assert res["result"]["reason"] == "dict from warning"


def test_latency_warning_direct_return_non_dict():
    class SlowNonDictClient:
        def submit_order(self, *a, **k):
            time.sleep(0.02)
            return 999

    r = SmartOrderRouter(
        {"alpaca": SlowNonDictClient()},
        config={"alerts": {"latency_threshold_ms": 1}, "execution": {"max_latency_breaches": 10}},
    )
    res = r.route_order("AAPL", "BUY", 1, 100)
    assert res["status"] == "warning"
    assert res["result"] == 999


def test_latency_warning_and_escalation_to_halt():
    r = SmartOrderRouter(
        {"alpaca": DummyClient("slow")},
        config={"alerts": {"latency_threshold_ms": 1}, "execution": {"max_latency_breaches": 1}},
    )
    res = r.route_order("AAPL", "BUY", 1, 100)
    assert res["status"] == "blocked"
    assert "Latency breaches" in res["reason"]


# --- Tests: reset_session + alert -------------------------------------
def test_reset_session_and_alert(router, caplog):
    router.latency_breaches = 5
    router.reset_session()
    assert router.latency_breaches == 0

    caplog.set_level(logging.ERROR, logger="hybrid_ai_trading.execution.smart_router")
    router._send_alert("explicit alert")
    assert any("explicit alert" in rec.message for rec in caplog.records)


def test_direct_send_alert(router, caplog):
    caplog.set_level(logging.ERROR, logger="hybrid_ai_trading.execution.smart_router")
    router._send_alert("manual alert")
    assert any("manual alert" in rec.message for rec in caplog.records)


def test_send_alert_alone(router, caplog):
    caplog.set_level(logging.ERROR, logger="hybrid_ai_trading.execution.smart_router")
    router._send_alert("standalone alert")
    assert any("standalone alert" in rec.message for rec in caplog.records)


def test_alert_is_logged_and_message_returned(router, caplog):
    """Explicitly cover the _send_alert branch (lines 163–165)."""
    caplog.set_level(logging.ERROR, logger="hybrid_ai_trading.execution.smart_router")
    msg = "final coverage alert"
    router._send_alert(msg)
    assert any(msg in rec.message for rec in caplog.records)
