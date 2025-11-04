import os
from pathlib import Path

import pytest

# Default unit tests to FAKE broker; scrub IB env to avoid live connects
os.environ.setdefault("BROKER_BACKEND", "fake")
for k in ("IB_HOST", "IB_PORT", "IB_CLIENT_ID", "IB_TIMEOUT"):
    os.environ.pop(k, None)


def pytest_addoption(parser):
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="run tests marked as integration (needs IBG)",
    )
    parser.addoption(
        "--include-legacy",
        action="store_true",
        default=False,
        help="collect legacy tests that import _engine_factory",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: mark tests as integration (needs IBG)"
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-integration"):
        skip_it = pytest.mark.skip(reason="need --run-integration to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_it)


def pytest_ignore_collect(collection_path: Path, config):
    # skip legacy files unless explicitly requested
    legacy = {
        "test_trade_engine_master_full.py",
        "test_trade_engine_residual_sniper.py",
        "test_trade_engine_sweeper.py",
        "test_trade_engine_targeted_cases.py",
    }
    parts = collection_path.parts
    if ("archive" in parts or "scripts" in parts) and not config.getoption(
        "--include-legacy"
    ):
        return True
    if collection_path.name in legacy and not config.getoption("--include-legacy"):
        return True
    return False
