"""
Hybrid AI Quant Pro â€“ Configuration
-----------------------------------
Centralized configuration utilities:
- settings: load and validate YAML configs with dynamic upgrades
"""

from hybrid_ai_trading.config.settings import CONFIG, get_config_value, load_config

__all__ = ["CONFIG", "load_config", "get_config_value"]
