"""
Security Utilities (Hybrid AI Quant Pro)
----------------------------------------
- Mask API keys/secrets in logs (show only first 4 + last 3 chars).
"""

def mask_key(key: str | None) -> str:
    """Return a masked version of a secret key for safe logging."""
    if not key:
        return "None"
    if len(key) <= 7:
        return "*" * len(key)
    return f"{key[:4]}***{key[-3:]}"
