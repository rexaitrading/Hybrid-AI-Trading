"""
Bootstrap Validation Tests (Hybrid AI Quant Pro – AAA Polished)
===============================================================
- Ensures all critical modules from conftest.py are importable.
- Fails early in CI if any enforced module is missing or broken.
"""

import os
import sys
import importlib
import importlib.util
import pytest

CRITICAL_MODULES = []

# --- Step 1: Try normal pytest-managed conftest ----------------------
try:
    from conftest import CRITICAL_MODULES as CM
    CRITICAL_MODULES = list(CM)
except Exception:
    # --- Step 2: Fallback → load conftest.py manually ----------------
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "tests", "conftest.py")
    if os.path.exists(path):
        spec = importlib.util.spec_from_file_location("tests.conftest", path)
        conf = importlib.util.module_from_spec(spec)
        sys.modules["tests.conftest"] = conf
        spec.loader.exec_module(conf)  # type: ignore
        if hasattr(conf, "CRITICAL_MODULES"):
            CRITICAL_MODULES = list(conf.CRITICAL_MODULES)

# --- Test function with skipif guard -------------------------------
@pytest.mark.skipif(
    not CRITICAL_MODULES,
    reason="⚠️ No CRITICAL_MODULES found in conftest.py — nothing to validate.",
)
@pytest.mark.parametrize("module", CRITICAL_MODULES or ["__dummy__"])
def test_critical_modules_importable(module):
    """Every critical module must import successfully."""
    if module == "__dummy__":
        pytest.skip("⚠️ Placeholder skip — no modules to validate")
    mod = importlib.import_module(module)
    assert mod is not None, f"Failed to import {module}"
