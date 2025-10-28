# PYTEST_IMPORT_SHIM: ensure repo src/ is importable regardless of CWD/interpreter
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
s = str(SRC)
if s not in sys.path:
    sys.path.insert(0, s)

from hybrid_ai_trading.runners.paper_trader import _normalize_result


def test_normalize_result_from_list():
    li = [{"symbol": "AAPL", "decision": {}}, {"symbol": "MSFT", "decision": {}}]
    out = _normalize_result(li)
    assert isinstance(out, dict) and "items" in out and len(out["items"]) == 2


def test_normalize_result_from_dict():
    di = {"summary": {"rows": 1}, "items": [{"symbol": "AAPL", "decision": {}}]}
    out = _normalize_result(di)
    assert out is di
