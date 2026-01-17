from __future__ import annotations

from pathlib import Path

# A1 contract: the ONLY runtime file allowed to directly submit to IB is the chokepoint.
# Tests may contain placeOrder strings in controlled contexts; allowlist explicitly.
ALLOWED_FILES = {
    "src/hybrid_ai_trading/broker/ib_safe.py",
    "tests/integration/test_ib_paper_smoke.py",
    "tests/smoke/test_ib_bracket.py",
    "tests/test_no_direct_ib_placeorder.py",
}

# Exclude non-runtime surfaces and Windows-problematic dirs/files.
EXCLUDE_DIR_PARTS = {
    "logs",
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "pytest_tmp",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
    ".tox",
    "archive",
    ".ipynb_checkpoints",
    "scripts/_quarantine",
}

def _is_excluded(path: Path) -> bool:
    rel = path.as_posix()
    for part in EXCLUDE_DIR_PARTS:
        if f"/{part}/" in f"/{rel}/":
            return True
    return False

def test_no_new_direct_ib_placeorder_call_sites():
    root = Path(__file__).resolve().parents[1]
    paths = [p for p in root.rglob("*.py") if p.is_file() and not _is_excluded(p)]

    offenders_ib = []
    offenders_dot = []

    for p in paths:
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except (OSError, PermissionError):
            # Skip unreadable Windows paths (e.g., archive/.ipynb_checkpoints) and locked files.
            continue

        rel = p.relative_to(root).as_posix()

        if "ib.placeOrder(" in txt and rel not in ALLOWED_FILES:
            offenders_ib.append(rel)

        # Covers IBApi subclass usage like self.placeOrder(...)
        if ".placeOrder(" in txt and rel not in ALLOWED_FILES:
            offenders_dot.append(rel)

    assert not offenders_ib, (
        "New direct ib.placeOrder call sites detected (must route via IB chokepoint): "
        + ", ".join(sorted(offenders_ib))
    )
    assert not offenders_dot, (
        "New direct .placeOrder call sites detected (must route via IB chokepoint): "
        + ", ".join(sorted(offenders_dot))
    )
