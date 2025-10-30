from hybrid_ai_trading.execution.smart_router import SmartOrderRouter


def R(brokers, cfg=None):
    return SmartOrderRouter(brokers, cfg or {})


# 59–60: rank_brokers() dict-comp + sort
def test_rank_brokers_lines_59_60():
    r = R({"alpaca": object(), "binance": object(), "polygon": object()})
    ranked = r.rank_brokers()
    assert isinstance(ranked, list) and len(ranked) == 3


# 97–98: if not client: continue
def test_missing_client_lines_97_98(monkeypatch):
    r = R({"ghost": None, "ok": object()}, {"execution": {"max_order_retries": 1}})
    # ensure next broker is used and flow continues
    monkeypatch.setattr(
        r.latency_monitor,
        "measure",
        lambda f: {"latency": 0.001, "result": {"status": "ok"}},
    )
    out = r.route_order("SYM", "BUY", 1, 1.0)
    assert out["status"] == "filled" and out["broker"] == "ok"


# 122: top-level error envelope (NOT the normal result envelope)
def test_top_level_error_line_122(monkeypatch):
    r = R({"only": object()})
    monkeypatch.setattr(
        r.latency_monitor,
        "measure",
        lambda f: {"status": "error", "reason": "broken", "latency": 0.001},
    )
    out = r.route_order("SYM", "BUY", 1, 1.0)
    assert out == {"status": "blocked", "reason": "broken"}


# 142–146: ok->filled AND pending return lines
def test_return_paths_ok_and_pending_lines_142_146(monkeypatch):
    r_ok = R({"only": object()})
    monkeypatch.setattr(
        r_ok.latency_monitor,
        "measure",
        lambda f: {"latency": 0.001, "result": {"status": "ok"}},
    )
    out_ok = r_ok.route_order("SYM", "BUY", 1, 1.0)
    assert out_ok["status"] == "filled"

    r_p = R({"only": object()})
    monkeypatch.setattr(
        r_p.latency_monitor,
        "measure",
        lambda f: {"latency": 0.001, "result": {"status": "pending"}},
    )
    out_p = r_p.route_order("SYM", "BUY", 1, 1.0)
    assert out_p["status"] == "pending"


# 154–156: blocked and rejected both break inner loop; router must continue to next broker
def test_blocked_and_rejected_break_then_continue_lines_154_156(monkeypatch):
    calls = {"i": 0}
    r = R(
        {"b1": object(), "b2": object(), "b3": object()},
        {"execution": {"max_order_retries": 1}},
    )

    def seq_measure(_):
        calls["i"] += 1
        if calls["i"] == 1:
            return {"latency": 0.001, "result": {"status": "blocked", "reason": "x"}}
        if calls["i"] == 2:
            return {"latency": 0.001, "result": {"status": "rejected", "reason": "y"}}
        return {"latency": 0.001, "result": {"status": "ok"}}

    monkeypatch.setattr(r.latency_monitor, "measure", seq_measure)
    out = r.route_order("SYM", "BUY", 1, 1.0)
    assert out["status"] == "filled"


# 192->124: prove both final paths: default and last_error
def test_final_paths_last_error_and_default(monkeypatch):
    # last_error path: unknown non-dict result first, then None -> returns last_error
    r1 = R({"a": object(), "b": object()}, {"execution": {"max_order_retries": 1}})
    calls = {"i": 0}

    def seq1(_):
        calls["i"] += 1
        if calls["i"] == 1:
            return {"latency": 0.001, "result": 0}  # non-dict -> unknown_broker_result
        return {"latency": 0.001, "result": None}

    monkeypatch.setattr(r1.latency_monitor, "measure", seq1)
    out1 = r1.route_order("SYM", "BUY", 1, 1.0)
    assert out1["status"] == "blocked" and out1["reason"] in {
        "unknown_broker_result",
        "unknown",
    }

    # default path: no last_error ever set -> all_brokers_failed
    r2 = R({"a": object(), "b": object()}, {"execution": {"max_order_retries": 1}})
    monkeypatch.setattr(
        r2.latency_monitor, "measure", lambda f: {"latency": 0.001, "result": None}
    )
    out2 = r2.route_order("SYM", "BUY", 1, 1.0)
    assert out2 == {"status": "blocked", "reason": "all_brokers_failed"}
