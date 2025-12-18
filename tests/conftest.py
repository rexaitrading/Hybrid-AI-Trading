from __future__ import annotations

import os

def _mask_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        return "NOT_SET"
    tail = v[-4:] if len(v) >= 4 else v
    return f"SET(****{tail})"

# NOTE: never print full secrets
print("OPENAI_API_KEY: " + _mask_env("OPENAI_API_KEY"))
print("COINAPI_KEY: " + _mask_env("COINAPI_KEY"))
print("BROKER_API_KEY: " + _mask_env("BROKER_API_KEY"))