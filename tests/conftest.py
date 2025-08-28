import os
import pytest
from dotenv import load_dotenv

# Force load the correct .env file at project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")
load_dotenv(ENV_PATH)


@pytest.fixture(autouse=True)
def set_env():
    """
    Auto-use fixture that ensures .env values are available
    for all tests.
    """
    yield  # nothing to do here, just ensures env vars are set
