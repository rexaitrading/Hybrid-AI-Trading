"""
Unit Tests: Security Utilities (Hybrid AI Quant Pro v11.2 – Hedge-Fund Grade, 100% Coverage)
============================================================================================
Covers all branches of mask_key():
- None key
- Empty string
- Short key (<8 chars)
- Exactly 8 chars
- Long key (>8 chars, star count)
"""

import pytest
from hybrid_ai_trading.utils.security import mask_key


def test_mask_key_none_and_empty():
    assert mask_key(None) == "None"
    assert mask_key("") == "None"


def test_mask_key_short_keys():
    # Shorter than 8 → unchanged
    assert mask_key("ABC123") == "ABC123"
    assert mask_key("1234567") == "1234567"


def test_mask_key_exactly_8_chars():
    # Exactly 8 → first 4 + **** + last 4
    assert mask_key("ABCDEFGH") == "ABCD****EFGH"
    assert mask_key("12345678") == "1234****5678"


def test_mask_key_longer_than_8_chars():
    # >8 → stars = len(key) - 8
    key = "SUPERSECRETKEY123456789"
    result = mask_key(key)
    assert result.startswith("SUPE")
    assert result.endswith("6789")
    stars = len(key) - 8
    assert result == "SUPE" + "*" * stars + "6789"


def test_mask_key_minimal_long_case():
    """Check smallest >8 case (9 chars) → 1 star in the middle."""
    key = "ABCDEFGHI"
    result = mask_key(key)
    assert result == "ABCD*FGHI"  # exactly one star


def test_mask_key_boundary_cases():
    """Check edge boundaries explicitly."""
    key7 = "1234567"   # 7 chars → unchanged
    assert mask_key(key7) == key7

    key8 = "12345678"  # 8 chars → formatted
    assert mask_key(key8) == "1234****5678"

    key9 = "123456789"  # 9 chars → 1 star
    assert mask_key(key9) == "1234*6789"
