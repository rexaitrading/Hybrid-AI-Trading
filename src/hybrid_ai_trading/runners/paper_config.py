# -*- coding: utf-8 -*-
from __future__ import annotations
import os, re, argparse
from typing import Any, Dict, List

try:
    import yaml
except Exception:
    yaml = None

# ---------------------------------------------------------------------------
# Env-variable expansion inside YAML
# ---------------------------------------------------------------------------
_ENV_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

def _expand_env(s: str) -> str:
    def _rep(m):
        key = m.group(1)
        return os.environ.get(key, "")
    return _ENV_RE.sub(_rep, s)

def _expand_env_in_obj(x):
    if isinstance(x, str):
        return _expand_env(x)
    if isinstance(x, list):
        return [_expand_env_in_obj(v) for v in x]
    if isinstance(x, dict):
        return {k: _expand_env_in_obj(v) for k, v in x.items()}
    return x

# ---------------------------------------------------------------------------
# YAML loader with env expansion
# ---------------------------------------------------------------------------
def load_config(path: str) -> Dict[str, Any]:
    if not yaml:
        raise RuntimeError("PyYAML not available; run 'pip install pyyaml'")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return _expand_env_in_obj(data)

# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser("Hybrid AI Quant Pro Paper Runner")
    ap.add_argument("--config", default="config/paper_runner.yaml", help="Path to YAML config.")
    ap.add_argument("--once", action="store_true", help="Run one pass then exit")
    ap.add_argument("--universe", default="", help="Comma list to override symbols")
    ap.add_argument("--mdt", type=int, default=3, help="1=live,2=frozen,3=delayed,4=delayed-frozen")
    ap.add_argument("--client-id", type=int, default=int(os.getenv("IB_CLIENT_ID", "3021")))
    ap.add_argument("--log-file", default="logs/runner_paper.jsonl")
    ap.add_argument("--dry-drill", action="store_true",
                    help="Run preflight can’t-fill drill even if market is closed (paper only).")
    return ap

def parse_args(argv: List[str] | None = None):
    return build_parser().parse_args(argv)