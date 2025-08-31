import sys
import os
import argparse
from src.config.settings import load_config
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

# Load config
cfg = load_config()

print("✅ Config loaded successfully!\n")

# Show full config (debugging)
print("Full config dict:", cfg, "\n")

# Print specific keys
print("Project:", cfg.get("project", "Not defined"))
print("Timezone:", cfg.get("timezone", "Not defined"))

# Define required structure
required_structure = {
    "project": None,
    "timezone": None,
    "trading_window": ["start", "end"],
    "risk": ["target_daily_return", "max_daily_loss", "max_position_risk", "max_leverage"],
    "costs": [
        "commission_per_share", "min_commission", "slippage_per_share",
        "margin_interest_rate", "trading_days_per_year"
    ],
    "providers": {
        "polygon": ["api_key_env"],
        "alpaca": ["key_id_env", "secret_key_env"],
        "coinapi": ["api_key_env"],
        "benzinga": ["api_key_env"]
    },
    "universe": ["Core_Stocks", "Macro_Risk", "Crypto_Signal", "Leverage_Tools", "IPO_Watch"],
    "features": [
        "enable_black_swan_guard", "enable_leverage_control",
        "enable_emotional_filter", "enable_multi_ai_signals", "enable_portfolio_guard"
    ],
}

errors = []

def validate_section(section, expected, path=""):
    """Recursively validate sections of the config."""
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

# Run structure validation
print("\n🔍 Validation check:")
validate_section(cfg, required_structure)

# --- Environment variable check ---
print("\n🔑 Environment variable check:")

# Extract provider env var names from config dynamically
provider_envs = []
for provider, keys in cfg.get("providers", {}).items():
    for key_name, env_var in keys.items():
        provider_envs.append(env_var)

# Add optional extras (if you want non-config vars checked too)
extra_envs = ["IBKR_ACCOUNT", "BINANCE_API_KEY", "BINANCE_API_SECRET"]
provider_envs.extend(extra_envs)

for env_var in provider_envs:
    value = os.getenv(env_var)
    if value:
        print(f"{env_var} present ✅, preview: ******{value[-6:]}")
    else:
        msg = f"{env_var} MISSING ❌"
        print(msg)
        errors.append(msg)

# Parse args
parser = argparse.ArgumentParser()
parser.add_argument("--strict", action="store_true", help="Exit with error if validation fails")
args = parser.parse_args()

# Final result
if errors:
    print(f"\n❌ Config/Environment validation failed with {len(errors)} error(s).")
    if args.strict:
        sys.exit(1)
else:
    print("\n✅ Config & Environment validation passed!")
    sys.exit(0)
