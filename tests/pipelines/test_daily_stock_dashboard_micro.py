import hybrid_ai_trading.pipelines.daily_stock_dashboard as dash


def _make_breakout_bars():
    # Prior highs around 60, last close 100 -> guaranteed BREAKOUT UP
    return [{"c": 50.0, "h": 60.0, "l": 40.0} for _ in range(29)] + [
        {"c": 100.0, "h": 101.0, "l": 90.0}
    ]


def test_grade_stock_B_branch(monkeypatch):
    # Slightly > 1.5 to avoid float rounding: rr = 0.0182 / 0.012 ≈ 1.5167 -> "B"
    bars = _make_breakout_bars()
    monkeypatch.setattr(dash, "STOP_PCT", 0.012)
    monkeypatch.setattr(dash, "TARGET_PCT", 0.0182)
    res = dash.grade_stock("AAPL", bars)
    assert res and res["signal"] == "BREAKOUT UP" and res["grade"] == "B"


def test_grade_stock_C_branch(monkeypatch):
    # rr ≈ 1.133... -> "C"
    bars = _make_breakout_bars()
    monkeypatch.setattr(dash, "STOP_PCT", 0.015)
    monkeypatch.setattr(dash, "TARGET_PCT", 0.017)
    res = dash.grade_stock("AAPL", bars)
    assert res and res["signal"] == "BREAKOUT UP" and res["grade"] == "C"


def test_grade_stock_PASS_branch(monkeypatch):
    # rr = 0.010 / 0.020 = 0.5 -> "PASS"
    bars = _make_breakout_bars()
    monkeypatch.setattr(dash, "STOP_PCT", 0.020)
    monkeypatch.setattr(dash, "TARGET_PCT", 0.010)
    res = dash.grade_stock("AAPL", bars)
    assert res and res["signal"] == "BREAKOUT UP" and res["grade"] == "PASS"
