# -*- coding: utf-8 -*-
from __future__ import annotations

import os


class Client:
    def __init__(self, key: str = "", base: str = ""):
        self.key = key or ""
        self.base = base or ""

    def last_quote(self, symbol: str):
        if not self.key or not self.base:
            return {
                "symbol": symbol,
                "price": None,
                "source": "stub",
                "reason": "no_key_or_base",
            }
        # real HTTP call would go here; keep stub-safe
        return {
            "symbol": symbol,
            "price": None,
            "source": "stub",
            "reason": "not_implemented",
        }
