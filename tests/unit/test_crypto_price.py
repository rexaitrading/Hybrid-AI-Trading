from hybrid_ai_trading.utils.providers import load_providers, get_price

def test_get_price_crypto_returns_number():
    cfg = load_providers("config/providers.yaml")
    out = get_price("BTCUSD", cfg)
    assert isinstance(out, dict)
    assert out.get("source") == "coinapi"
    assert isinstance(out.get("price"), (int, float))
