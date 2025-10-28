from typing import Dict, Any
from hybrid_ai_trading.utils.providers import load_providers, get_price

def latest_price(symbol: str, cfg_path: str = "config/providers.yaml") -> Dict[str, Any]:
    cfg = load_providers(cfg_path)
    return get_price(symbol, cfg)
