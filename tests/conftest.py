from __future__ import annotations

import os
import sys
from pathlib import Path


def _detect_repo_root(start: Path) -> Path:
    p = start.resolve()
    for _ in range(12):
        if (p / "pyproject.toml").exists() or (p / ".git").exists():
            return p
        if p.parent == p:
            break
        p = p.parent
    return start.resolve()


REPO_ROOT = _detect_repo_root(Path(__file__).parent)

# Ensure imports resolve from THIS repo (C:\HAT), not any other checkout
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Hard-disable user site packages for test runs (prevents cross-env leakage)
os.environ.setdefault("PYTHONNOUSERSITE", "1")

print(f"[conftest] exe={sys.executable} importable=True root={REPO_ROOT}")