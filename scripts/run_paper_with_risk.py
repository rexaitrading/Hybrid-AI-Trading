import sys, types, pathlib
from types import SimpleNamespace
from hybrid_ai_trading.runners.paper_config import parse_args
from hybrid_ai_trading.runners import paper_trader as PT

def _patched_load_config(path: str):
    # call the original
    data = _orig_load(path)
    try:
        # inject a real RiskManager (tweak max_notional/params as you like)
        from hybrid_ai_trading.risk.risk_manager import RiskManager
        rm = RiskManager(max_notional=1_000_000)
        if isinstance(data, dict):
            data["risk_mgr"] = rm
    except Exception as e:
        # stay resilient; fall back to original data
        pass
    return data or {}

if __name__ == "__main__":
    _orig_load = PT.load_config
    PT.load_config = _patched_load_config  # monkeypatch

    # parse argv into args namespace (just like runner)
    args = parse_args(sys.argv[1:])
    sys.exit(PT.run_paper_session(args))
