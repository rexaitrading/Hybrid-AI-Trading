"""
Universe Definitions (Hybrid AI Quant Pro – Hedge-Fund Grade)
-------------------------------------------------------------
Defines the static trading universe across asset categories:
- Core_Stocks: diversified equities (tech, defensive, financials)
- Core_Crypto: core crypto majors
- Macro_Risk: ETFs for macro hedging & risk signals
- Leverage_Tools: leveraged ETFs for tactical strategies
- IPO_Watch: recent IPOs to monitor
"""

from typing import Dict, List

# --- Core Stocks (large-cap & diversified) ---
Core_Stocks: List[str] = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META",
    "JNJ", "PG", "KO", "JPM", "GS",
]

# --- Core Crypto Majors ---
Core_Crypto: List[str] = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT",
]

# --- Macro Risk Indicators (hedge ETFs & benchmarks) ---
Macro_Risk: List[str] = [
    "SPY", "QQQ", "DIA", "GLD", "TLT", "USO", "UUP", "VIXY",
]

# --- Leveraged ETFs (for tactical tools) ---
Leverage_Tools: List[str] = [
    "TQQQ", "SQQQ", "UPRO", "SPXU",
]

# --- IPO Watchlist ---
IPO_Watch: List[str] = ["ABNB", "ARM", "SNOW", "RIVN", "BIRK"]


def groups() -> Dict[str, List[str]]:
    """Return dictionary of all asset groups for pipelines."""
    return {
        "Core_Stocks": Core_Stocks,
        "Core_Crypto": Core_Crypto,
        "Macro_Risk": Macro_Risk,
        "Leverage_Tools": Leverage_Tools,
        "IPO_Watch": IPO_Watch,
    }


__all__ = [
    "Core_Stocks",
    "Core_Crypto",
    "Macro_Risk",
    "Leverage_Tools",
    "IPO_Watch",
    "groups",
]
