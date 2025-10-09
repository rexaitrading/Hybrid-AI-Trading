"""
Conftest (Hybrid AI Quant Pro – Hedge-Fund Grade)
-------------------------------------------------
Responsibilities:
- Ensure environment variables from .env are loaded
- Provide global fixtures
- Declare CRITICAL_MODULES for bootstrap smoke test
"""

import os

import pytest
from dotenv import load_dotenv

# ----------------------------------------------------------------------
# Load environment variables
# ----------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")
load_dotenv(ENV_PATH)

# ----------------------------------------------------------------------
# Critical modules to validate via test_bootstrap.py
# ----------------------------------------------------------------------
CRITICAL_MODULES = [
    "hybrid_ai_trading.config.settings",
    "hybrid_ai_trading.data.clients.alpaca_client",
    "hybrid_ai_trading.data.clients.benzinga_client",
    "hybrid_ai_trading.data.clients.coinapi_client",
    "hybrid_ai_trading.data.clients.polygon_client",
    "hybrid_ai_trading.risk.risk_manager",
    "hybrid_ai_trading.signals.breakout_v1",
]


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture(autouse=True)
def set_env():
    """
    Auto-use fixture that ensures .env values are available
    for all tests.
    """
    yield  # Nothing to do, just ensures env vars are loaded
