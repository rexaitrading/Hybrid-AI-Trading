import json
import logging

from hybrid_ai_trading.risk.kelly_sizer import KellySizer, _safe_fmt


def test_init_defaults_and_custom(caplog):
    caplog.set_level(logging.INFO)
    ks1 = KellySizer()
    ks2 = KellySizer(0.6, 2.0, 0.5, 0.8)
    assert isinstance(ks1, KellySizer) and isinstance(ks2, KellySizer)
    assert "KellySizer initialized" in caplog.text


def test_kelly_fraction_normal_and_clamped(caplog):
    caplog.set_level(logging.DEBUG)
    ks = KellySizer(0.6, 2.0, 0.5, 1.0)
    f = ks.kelly_fraction()
    assert 0.0 <= f <= 1.0
    assert "Kelly fraction" in caplog.text

    # risk veto forces zero
    assert ks.kelly_fraction(risk_veto=True) == 0.0

    # clamping when fraction > 1
    ks.fraction = 10.0
    f2 = ks.kelly_fraction()
    assert f2 <= 1.0

    # regime_factor <= 0 should zero the scaled result
    ks.regime_factor = -1.0
    assert ks.kelly_fraction() == 0.0


def test_kelly_fraction_invalid_and_exception(monkeypatch, caplog):
    caplog.set_level(logging.WARNING)
    ks = KellySizer(win_rate=-0.1, payoff=0.0)  # invalid inputs
    assert ks.kelly_fraction() == 0.0
    assert "Invalid Kelly inputs" in caplog.text

    # exception path (force arithmetic/type error)
    ks2 = KellySizer(0.6, 2.0, 1.0)
    monkeypatch.setattr(ks2, "win_rate", "bad")
    caplog.set_level(logging.ERROR)
    assert ks2.kelly_fraction() == 0.0
    assert "Kelly sizing failed" in caplog.text


def test_size_position_valid_and_logging(caplog):
    caplog.set_level(logging.INFO)
    ks = KellySizer(0.6, 2.0, 0.5, 1.0)
    size = ks.size_position(10000, 100)
    assert isinstance(size, float)
    assert size > 0.0
    assert "Kelly sizing decision" in caplog.text


def test_size_position_invalid_inputs_and_veto(caplog):
    caplog.set_level(logging.WARNING)
    ks = KellySizer(0.6, 2.0, 0.5)
    # equity invalid
    assert ks.size_position(0, 100) == 0.0
    assert "Invalid equity/price" in caplog.text

    caplog.clear()
    # price invalid
    assert ks.size_position(1000, 0) == 0.0
    assert "Invalid equity/price" in caplog.text

    # veto -> fraction zero -> 0 size
    assert ks.size_position(10000, 100, risk_veto=True) == 0.0


def test_size_position_exception(monkeypatch, caplog):
    ks = KellySizer(0.6, 2.0, 0.5)

    def bad_fraction(*_, **__):
        raise Exception("boom")

    monkeypatch.setattr(ks, "kelly_fraction", bad_fraction)
    caplog.set_level(logging.ERROR)
    assert ks.size_position(1000, 100) == 0.0
    assert "Kelly sizing failed" in caplog.text


def test_batch_size_multiple_symbols():
    ks = KellySizer(0.6, 2.0, 0.5)
    prices = {"AAPL": 100.0, "TSLA": 200.0}
    out = ks.batch_size(10000.0, prices)
    assert set(out.keys()) == {"AAPL", "TSLA"}
    assert all(isinstance(v, float) for v in out.values())


def test_update_params_and_repr(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    ks = KellySizer()
    ks.update_params(0.7, 2.5, 0.5, 0.9)
    r = repr(ks)
    assert "KellySizer" in r
    assert "updated" in caplog.text or "KellySizer updated" in caplog.text

    # save params (success)
    path = tmp_path / "kelly.json"
    ks.save_params(str(path))
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    for k in ("win_rate", "payoff", "fraction", "regime_factor"):
        assert k in data


def test_save_params_failure(monkeypatch, tmp_path, caplog):
    caplog.set_level(logging.ERROR)

    def bad_open(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr("builtins.open", bad_open)
    ks = KellySizer()
    ks.save_params(str(tmp_path / "fail.json"))
    assert "Failed to save KellySizer params" in caplog.text


def test_safe_fmt_success_and_failure():
    assert _safe_fmt(1.234) == "1.23"

    class Bad:
        pass

    s = _safe_fmt(Bad())
    assert "Bad" in s
