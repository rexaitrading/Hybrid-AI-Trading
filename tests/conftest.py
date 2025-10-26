# conftest: ensure repo/src is importable in any CI working dir / interpreter
import os, sys, pathlib, importlib.util
ROOT = pathlib.Path(__file__).resolve().parents[1]  # project root (tests/..)
CANDIDATES = [ROOT / "src", ROOT]
for p in CANDIDATES:
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)
spec = importlib.util.find_spec("hybrid_ai_trading")
sys.stderr.write(f"[conftest] exe={sys.executable} importable={bool(spec)} root={ROOT}\\n")
if spec is None:
    # leave path injected; test files also prepend a tiny shim as last resort
    pass

