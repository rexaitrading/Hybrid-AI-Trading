from __future__ import annotations
import os, sys, json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT not in sys.path: sys.path.insert(0, ROOT)

from typing import List, Dict, Any
from execution.exit_rules import check_and_exit
from utils.slack_notify import notify

if __name__ == "__main__":
    stop_pct = float(os.environ.get("QP_STOP_PCT", "0.02"))  # 2% stop
    take_pct = float(os.environ.get("QP_TAKE_PCT", "0.03"))  # 3% take-profit
    dry_run  = os.environ.get("QP_DRY_RUN", "1") != "0"      # share with entry runner

    actions = check_and_exit(stop_pct=stop_pct, take_pct=take_pct, dry_run=dry_run)
    print(json.dumps(actions, indent=2))
    if actions:
        notify(f"EXIT actions: {len(actions)}")  # optional Slack