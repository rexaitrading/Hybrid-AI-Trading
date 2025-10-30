# -*- coding: utf-8 -*-
import argparse
import json
import os

import requests

from hybrid_ai_trading.utils.metrics import simple_counts


def main():
    ap = argparse.ArgumentParser("Metrics Report")
    ap.add_argument("--log", default="logs/runner_paper.jsonl")
    ap.add_argument("--slack-webhook", default=os.getenv("SLACK_WEBHOOK", ""))
    args = ap.parse_args()

    aapl, msft = simple_counts(args.log)
    report = {"log": args.log, "counts": {"AAPL": aapl, "MSFT": msft}}
    print(json.dumps(report, indent=2))
    if args.slack_webhook:
        try:
            requests.post(
                args.slack_webhook, json={"text": f"[Metrics] {report}"}, timeout=5
            )
            print("Slack: ok")
        except Exception as e:
            print("Slack: failed:", e)


if __name__ == "__main__":
    main()
