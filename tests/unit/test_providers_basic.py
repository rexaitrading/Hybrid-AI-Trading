from hybrid_ai_trading.utils.providers import load_providers, get_price

def test_load_providers_and_get_price_stub(tmp_path, monkeypatch):
    # create a minimal providers.yaml that references env var (left unset)
    p = tmp_path / "providers.yaml"
    p.write_text("providers:\n  polygon:\n    key: ${POLYGON_KEY}\n", encoding="utf-8")
    cfg = load_providers(str(p))

    # No POLYGON_KEY in env -> should fallback with a reason
    out = get_price("AAPL", cfg)
    assert isinstance(out, dict)
    assert out["symbol"] == "AAPL"
    assert "source" in out
