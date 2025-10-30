# -*- coding: utf-8 -*-
from __future__ import annotations

import os

import requests

RISK_HUB_URL = os.getenv("RISK_HUB_URL", "http://127.0.0.1:8787")


def check_decision(
    base_url: str,
    symbol: str,
    qty: float,
    notional: float,
    side: str = "BUY",
    timeout: float = 2.5,
):
    """POST to /decision_check; return dict with ok/reason or unreachable."""
    url = f"{base_url.rstrip('/')}/decision_check"
    payload = {
        "symbol": symbol,
        "qty": float(qty or 0),
        "notional": float(notional or 0),
        "side": side,
    }
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        out = r.json()
        out.setdefault("from", "risk_hub")
        return out
    except Exception as e:
        return {
            "ok": False,
            "reason": "unreachable",
            "error": str(e),
            "from": "risk_hub",
            "url": url,
        }
