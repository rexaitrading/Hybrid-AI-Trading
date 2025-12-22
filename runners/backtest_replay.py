# -*- coding: utf-8 -*-
from __future__ import annotations

"""
Repo-root CLI entrypoint for Phase-1 replay.
Delegates to src/hybrid_ai_trading/runners/backtest_replay.py
"""

from hybrid_ai_trading.runners.backtest_replay import main

if __name__ == "__main__":
    main()
