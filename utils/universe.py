# ==============================
# universe.py
# Hybrid AI Trading Project
# ==============================

"""
Defines the trading universe of assets across categories:
- Core stocks
- Crypto majors
- Macro risk indicators
- IPO watchlist
"""

# --- Core Stocks (diversified large-cap & growth) ---
Core_Stocks = [
    # Tech & Growth
    "AAPL",   # Apple
    "MSFT",   # Microsoft
    "GOOGL",  # Alphabet
    "AMZN",   # Amazon
    "TSLA",   # Tesla
    "NVDA",   # Nvidia
    "META",   # Meta Platforms

    # Defensive & Dividend
    "JNJ",    # Johnson & Johnson
    "PG",     # Procter & Gamble
    "KO",     # Coca-Cola

    # Financials
    "JPM",    # JPMorgan Chase
    "GS",     # Goldman Sachs
]

# --- Core Crypto Majors ---
Core_Crypto = [
    "BTC/USDT",  # Bitcoin
    "ETH/USDT",  # Ethereum
    "SOL/USDT",  # Solana
    "BNB/USDT",  # Binance Coin
    "XRP/USDT",  # XRP
]

# --- Macro Risk Indicators ---
Macro_Risk = [
    "SPY",   # S&P 500 ETF
    "QQQ",   # Nasdaq 100 ETF
    "DIA",   # Dow Jones ETF
    "GLD",   # Gold ETF
    "TLT",   # 20yr Treasury Bond ETF
    "USO",   # Crude Oil ETF
    "UUP",   # US Dollar Index ETF
]

# --- IPO Watchlist (update quarterly) ---
IPO_Watch = [
    "ABNB",  # Airbnb
    "ARM",   # Arm Holdings
    "SNOW",  # Snowflake
    "RIVN",  # Rivian
    "BIRK",  # Birkenstock
]

# --- Universe Groups ---
def groups():
    """
    Returns a dictionary of asset groups for strategy modules.
    """
    return {
        "stocks": Core_Stocks,
        "crypto": Core_Crypto,
        "macro": Macro_Risk,
        "ipo": IPO_Watch,
    }
