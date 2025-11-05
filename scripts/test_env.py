"""
Env Key Audit Tool (Hybrid AI Quant Pro â€“ Secure)
-------------------------------------------------
Usage:
    $env:PYTHONPATH="src"
    python scripts/test_env.py
"""

import os

from dotenv import load_dotenv


def mask(val: str, show: int = 6) -> str:
    """Safely mask secrets for display."""
    if not val:
        return "MISSING"
    return val[:show] + "****"


def check_env(keys, disabled=None):
    """Check and print masked values for a list of env keys."""
    for k in keys:
        if disabled and k in disabled:
            print(f"{k:20} -> DISABLED (Canada)")
        else:
            v = os.getenv(k)
            print(f"{k:20} -> {mask(v)}")


if __name__ == "__main__":
    # Always override stale session/system vars with .env values
    load_dotenv(override=True)

    print("\n=== ðŸ”‘ Provider Keys Audit ===\n")

    # Kraken (crypto live)
    check_env(["KRAKEN_API_KEY", "KRAKEN_PRIVATE_KEY"])

    # Binance (disabled in Canada)
    check_env(
        ["BINANCE_API_KEY", "BINANCE_API_SECRET"],
        disabled={"BINANCE_API_KEY", "BINANCE_API_SECRET"},
    )

    # Polygon + Alpaca (equities)
    check_env(
        [
            "POLYGON_API_KEY",
            "ALPACA_KEY",
            "ALPACA_SECRET",
            "PAPER_ACCOUNT",
            "PAPER_NEW_KEY",
            "PAPER_NEW_SECRET",
        ]
    )

    # Alt-data providers
    check_env(
        [
            "BENZINGA_API_KEY",
            "CRYPTCOMPARE_KEY",
            "COINAPI_KEY",
            "CMEGROUP_TOKEN",
            "CMEGROUP_ACCESS_CODE",
        ]
    )

    # OpenAI for NLP/sentiment/ops
    check_env(["OPENAI_API_KEY"])

    print(
        "\nâœ… Audit complete â€“ verify all active providers are masked, Binance marked as DISABLED.\n"
    )
