# utils/universe.py
from utils.config import load_config

_cfg = load_config() # 讀 config.yaml
U = _cfg.get("universe", {}) # 只取 universe 區塊

# 個別清單（冇就回傳空清單）
Core_Stocks = U.get("Core_Stocks", [])
Crypto_Signal = U.get("Crypto_Signal", [])
Macro_Risk = U.get("Macro_Risk", [])
Leverage_Tools = U.get("Leverage_Tools", [])
IPO_Watch = U.get("IPO_Watch", [])

def groups() -> dict:
    """一次過取回所有清單"""
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