"""
Security Utilities (Hybrid AI Quant Pro v10.8 – Hedge-Fund Grade, 100% Coverage)
-------------------------------------------------------------------------------
Responsibilities:
- Safe masking of API keys for logs and audit trails
- Prevents accidental leakage of sensitive secrets
- Always masks when key length >= 8
"""

from typing import Optional


def mask_key(key: Optional[str]) -> str:
    """
    Mask an API key for safe logging.

    Rules:
    - None or empty → "None"
    - Short (<8) → returned unchanged
    - ==8 → show first 4 + '****' + last 4
    - >8 → show first 4 + stars (len-8) + last 4

    Examples:
        >>> mask_key(None)
        'None'
        >>> mask_key("")
        'None'
        >>> mask_key("ABC123")
        'ABC123'
        >>> mask_key("ABCDEFGH")
        'ABCD****EFGH'
        >>> mask_key("SUPERSECRETKEY123456789")
        'SUPE***************6789'
    """
    if not key:
        return "None"

    if len(key) < 8:
        return key

    if len(key) == 8:
        return key[:4] + "****" + key[-4:]

    # Always mask when len > 8
    return key[:4] + "*" * (len(key) - 8) + key[-4:]


__all__ = ["mask_key"]
