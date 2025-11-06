from __future__ import annotations

import os
import re
from typing import Any, Dict

try:
    import yaml  # pyyaml optional for tests; guard import
except Exception:
    yaml = None

_env_pat = re.compile(r"\$\{([A-Z0-9_]+)\}")


def _expand_env(value: str) -> str:
    def repl(m):
        return os.environ.get(m.group(1), "")

    return _env_pat.sub(repl, value)


def load_providers(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
        raw = _expand_env(raw)
        if yaml:
            data = yaml.safe_load(raw) or {}
        else:
            # ultra-minimal YAML: treat as empty if PyYAML missing
            data = {}
        return data
    except Exception:
        return {}


def get_price(symbol: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    providers = (cfg or {}).get("providers", {}) or {}
    poly_key = (providers.get("polygon", {}) or {}).get("key") or os.environ.get(
        "POLYGON_KEY"
    )
    if not poly_key:
        return {"symbol": symbol, "price": None, "reason": "missing_polygon_key"}
    return {"symbol": symbol, "price": None, "reason": "stubbed"}
