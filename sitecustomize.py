# Auto-add ./src to sys.path for any Python process launched at or below repo root.
import sys, pathlib
try:
    # Walk up until we find a "src" folder (max 6 levels for safety)
    p = pathlib.Path(__file__).resolve()
    for _ in range(6):
        if (p / "src").exists():
            src = (p / "src").resolve()
            s = str(src)
            if s not in sys.path:
                sys.path.insert(0, s)
            break
        if p.parent == p:
            break
        p = p.parent
except Exception:
    # Be quiet in sitecustomize
    pass
