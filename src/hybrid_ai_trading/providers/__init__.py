import importlib as _imp


def get_price(symbol, cfg):
    return _imp.import_module("hybrid_ai_trading.providers.price").get_price(
        symbol, cfg
    )


def load_providers(path):
    return _imp.import_module("hybrid_ai_trading.providers.price").load_providers(path)


__all__ = ["get_price", "load_providers"]
