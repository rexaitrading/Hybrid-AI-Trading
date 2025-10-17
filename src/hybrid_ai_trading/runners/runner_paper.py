# -*- coding: utf-8 -*-
import os, sys, pathlib
# Bootstrap when run as a script (so absolute imports work)
if __package__ in (None, ""):
    _here = pathlib.Path(__file__).resolve()
    # add the parent dir that contains 'hybrid_ai_trading' to sys.path
    for p in _here.parents:
        if (p / "hybrid_ai_trading").exists():
            if str(p) not in sys.path:
                sys.path.insert(0, str(p))
            break

from hybrid_ai_trading.runners.paper_config import parse_args
from hybrid_ai_trading.runners.paper_trader import run_paper_session

def main(argv=None) -> int:
    args = parse_args(argv)
    return run_paper_session(args)

if __name__ == "__main__":
    raise SystemExit(main())
