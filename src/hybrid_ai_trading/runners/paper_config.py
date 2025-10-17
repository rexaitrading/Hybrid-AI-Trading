# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse
import os

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser("Paper Runner MVP")
    ap.add_argument("--config", default="config/paper_runner.yaml")
    ap.add_argument("--once", action="store_true", help="Run one pass then exit")
    ap.add_argument("--universe", default="", help="Comma list to override symbols")
    ap.add_argument("--mdt", type=int, default=3, help="1=live,2=frozen,3=delayed,4=delayed-frozen")
    ap.add_argument("--client-id", type=int, default=int(os.getenv("IB_CLIENT_ID", "3021")))
    ap.add_argument("--log-file", default="logs/runner_paper.jsonl")
    ap.add_argument("--dry-drill", action="store_true",
                    help="Run preflight can’t-fill drill even if market is closed (paper only).")
    return ap

def parse_args(argv=None):
    return build_parser().parse_args(argv)