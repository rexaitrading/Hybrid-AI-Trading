"""
Hybrid AI Quant Pro – Configuration
-----------------------------------
Centralized configuration utilities:
- settings: load and validate YAML configs with dynamic upgrades
"""

from hybrid_ai_trading.config.settings import CONFIG, load_config, get_config_value

__all__ = ["CONFIG", "load_config", "get_config_value"]
