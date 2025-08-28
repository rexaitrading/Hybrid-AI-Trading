# utils/universe.py
from src.config.settings import load_config

_cfg = load_config() # è®€ config.yaml
U = _cfg.get("universe", {}) # åªå– universe å€å¡Š

# å€‹åˆ¥æ¸…å–®ï¼ˆå†‡å°±å›žå‚³ç©ºæ¸…å–®ï¼‰
Core_Stocks = U.get("Core_Stocks", [])
Crypto_Signal = U.get("Crypto_Signal", [])
Macro_Risk = U.get("Macro_Risk", [])
Leverage_Tools = U.get("Leverage_Tools", [])
IPO_Watch = U.get("IPO_Watch", [])

def groups() -> dict:
    """ä¸€æ¬¡éŽå–å›žæ‰€æœ‰æ¸…å–®"""
    return {
        "Core_Stocks": Core_Stocks,
        "Crypto_Signal": Crypto_Signal,
        "Macro_Risk": Macro_Risk,
        "Leverage_Tools": Leverage_Tools,
        "IPO_Watch": IPO_Watch,
    }

__all__ = [
    "Core_Stocks", 
    "Crypto_Signal", 
    "Macro_Risk",
    "Leverage_Tools", 
    "IPO_Watch", 
    "groups"
]
