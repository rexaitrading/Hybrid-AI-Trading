from __future__ import annotations

import os
import re

import yaml

_ENV_PAT = re.compile(r"\$\{([A-Z0-9_]+)\}")


def _expand_env_placeholders(s: str) -> str:
    def repl(m):
        return os.environ.get(m.group(1), "")

    return _ENV_PAT.sub(repl, s)


def load_yaml_with_env(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    raw = _expand_env_placeholders(raw)
    return yaml.safe_load(raw) or {}
