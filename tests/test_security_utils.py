"""
Unit Tests: Security Utilities (Hybrid AI Quant Pro – 100% Coverage)
--------------------------------------------------------------------
Covers:
- mask_key(None) → "None"
- mask_key("") → "None"
- mask_key(short key ≤ 7) → fully masked
- mask_key(long key > 7) → first 4 + last 3 visible
"""

import pytest
from hybrid_ai_trading.utils.security import mask_key


def test_mask_key_none_and_empty():
    assert mask_key(None) == "None"
    assert mask_key("") == "None"


def test_mask_key_short():
    # length ≤ 7 → full masking
    assert mask_key("short") == "*****"
    assert mask_key("1234567") == "*******"


def test_mask_key_long():
    # length > 7 → first 4 + last 3 visible
    key = "ABCDEFGHIJKLMNOP"
    masked = mask_key(key)
    assert masked.startswith("ABCD")
    assert masked.endswith("NOP")
    assert "***" in masked
