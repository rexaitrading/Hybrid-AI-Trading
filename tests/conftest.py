# Ensures src/ is on sys.path during tests (CI/local), independent of CWD or runner shell
import sys, pathlib, importlib, os
ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if SRC.exists():
    s = str(SRC)
    if s not in sys.path:
        sys.path.insert(0, s)
try:
    importlib.import_module("hybrid_ai_trading")
except Exception as e:
    sys.stderr.write(f"[conftest] warning: could not import `hybrid_ai_trading`: {e}\n")
