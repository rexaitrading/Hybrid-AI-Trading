"""
Kelly Config & Sizing Check
---------------------------
Utility script to verify:
1. That config.yaml can be loaded.
2. That Kelly sizing parameters exist under risk.kelly.
3. That KellySizer computes a valid position size for a sample scenario.
"""

import os
import sys
import yaml

# Ensure src/ is on sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_PATH = os.path.join(BASE_DIR, "..", "src")
if SRC_PATH not in sys.path:
    sys.path.append(SRC_PATH)

# ✅ Correct import path
from hybrid_ai_trading.risk.kelly_sizer import KellySizer


def load_config(path: str = "config/config.yaml") -> dict:
    """Load YAML config from given path."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {os.path.abspath(path)}")
    with open(path, "r") as f:
        return yaml.safe_load(f)


def check_kelly(config: dict, equity: float = 100_000, price: float = 60_000):
    """Run a Kelly sizing test with given config and sample values."""
    kelly_cfg = config.get("risk", {}).get("kelly", {})

    print("\n=== Kelly Config Check ===")
    if not kelly_cfg:
        print("⚠️  No Kelly config found under risk.kelly in config.yaml")
        return

    print("Kelly Config Loaded:")
    for k, v in kelly_cfg.items():
        print(f"  {k}: {v}")

    if not kelly_cfg.get("enabled", False):
        print("ℹ️  Kelly sizing is disabled in config.yaml")
        return

    # Instantiate KellySizer
    sizer = KellySizer(
        win_rate=kelly_cfg.get("win_rate", 0.55),
        payoff=kelly_cfg.get("payoff", 1.5),
        fraction=kelly_cfg.get("fraction", 0.5),
    )

    f_star = sizer.optimal_fraction()
    size = sizer.size_position(equity, price)

    print("\n=== Kelly Calculation ===")
    print(f"Account Equity     : ${equity:,.2f}")
    print(f"Asset Price        : ${price:,.2f}")
    print(f"Optimal Fraction f*: {f_star:.4f}")
    print(f"Position Size      : {size:.6f} units/contracts")


if __name__ == "__main__":
    try:
        cfg = load_config("config/config.yaml")
        check_kelly(cfg)
    except Exception as e:
        print(f"❌ Error: {e}")
