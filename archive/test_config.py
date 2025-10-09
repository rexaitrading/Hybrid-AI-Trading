"""
Config Validation Script (Hybrid AI Quant Pro v2.0 – Hedge Fund Grade)
----------------------------------------------------------------------
Validates:
- Project config structure
- Presence of required keys
- Presence of required environment variables

Usage:
    python archive/scripts/test_config.py [--strict]

Notes:
- Designed as a standalone validation tool, not as a pytest test.
- Safe for CI pipelines and local debugging.
"""

import argparse
import os
import sys
from typing import Any, Dict, List

from dotenv import load_dotenv
from src.config.settings import load_config

# ----------------------------------------------------------------------
# Globals
# ----------------------------------------------------------------------
errors: List[str] = []

# ----------------------------------------------------------------------
# Required config structure
# ----------------------------------------------------------------------
REQUIRED_STRUCTURE: Dict[str, Any] = {
    "project": None,
    "timezone": None,
    "trading_window": ["start", "end"],
    "risk": [
        "target_daily_return",
        "max_daily_loss",
        "max_position_risk",
        "max_leverage",
    ],
    "costs": [
        "commission_per_share",
        "min_commission",
        "slippage_per_share",
        "margin_interest_rate",
        "trading_days_per_year",
    ],
    "providers": {
        "polygon": ["api_key_env"],
        "alpaca": ["key_id_env", "secret_key_env"],
        "coinapi": ["api_key_env"],
        "benzinga": ["api_key_env"],
    },
    "universe": [
        "Core_Stocks",
        "Macro_Risk",
        "Crypto_Signal",
        "Leverage_Tools",
        "IPO_Watch",
    ],
    "features": [
        "enable_black_swan_guard",
        "enable_leverage_control",
        "enable_emotional_filter",
        "enable_multi_ai_signals",
        "enable_portfolio_guard",
    ],
}

# ----------------------------------------------------------------------
# Validation helpers
# ----------------------------------------------------------------------
def validate_section(section: Dict[str, Any], expected: Any, path: str = "") -> None:
    """Recursively validate sections of the config dict."""
    if isinstance(expected, dict):
        for key, subkeys in expected.items():
            if key not in section:
                msg = f"❌ Missing section: {path}{key}"
                print(msg)
                errors.append(msg)
            else:
                validate_section(section[key], subkeys, path + key + ".")
    elif isinstance(expected, list):
        for key in expected:
            if key not in section:
                msg = f"❌ Missing key: {path}{key}"
                print(msg)
                errors.append(msg)
            else:
                print(f"✅ Found key: {path}{key}")
    else:
        if expected is None:
            if section is None:
                msg = f"❌ Missing key: {path}"
                print(msg)
                errors.append(msg)
            else:
                print(f"✅ Found key: {path}")


# ----------------------------------------------------------------------
# Main runner
# ----------------------------------------------------------------------
def main() -> None:
    """Run validation checks on config + environment."""
    # Load .env
    load_dotenv()

    # Load config
    cfg = load_config()
    print("✅ Config loaded successfully!\n")
    print("Full config dict:", cfg, "\n")

    # Basic info
    print("Project:", cfg.get("project", "Not defined"))
    print("Timezone:", cfg.get("timezone", "Not defined"))

    # Structure validation
    print("\n🔍 Validation check:")
    validate_section(cfg, REQUIRED_STRUCTURE)

    # Env var validation
    print("\n🔑 Environment variable check:")
    provider_envs: List[str] = []
    for provider, keys in cfg.get("providers", {}).items():
        for _, env_var in keys.items():
            provider_envs.append(env_var)

    # Extra manual env vars
    provider_envs.extend(["IBKR_ACCOUNT", "BINANCE_API_KEY", "BINANCE_API_SECRET"])

    for env_var in provider_envs:
        value = os.getenv(env_var)
        if value:
            print(f"{env_var} present ✅, preview: ******{value[-6:]}")
        else:
            msg = f"{env_var} MISSING ❌"
            print(msg)
            errors.append(msg)

    # Argparse
    parser = argparse.ArgumentParser(
        description="Validate HybridAITrading config and environment"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with error if validation fails",
    )
    args = parser.parse_args()

    # Final result
    if errors:
        print(f"\n❌ Config/Environment validation failed with {len(errors)} error(s).")
        if args.strict:
            sys.exit(1)
    else:
        print("\n✅ Config & Environment validation passed!")
        sys.exit(0)


# ----------------------------------------------------------------------
# Entrypoint
# ----------------------------------------------------------------------
if __name__ == "__main__":
    main()
