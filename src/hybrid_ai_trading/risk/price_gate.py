from typing import Any, Dict

from hybrid_ai_trading.utils.providers import get_price, load_providers


def latest_price(
    symbol: str, cfg_path: str = "config/providers.yaml"
) -> Dict[str, Any]:
    cfg = load_providers(cfg_path)
    return get_price(symbol, cfg)
