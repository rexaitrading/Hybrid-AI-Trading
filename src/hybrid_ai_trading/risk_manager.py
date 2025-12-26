# -*- coding: utf-8 -*-
"""
Compatibility shim.

This project’s real RiskManager lives at:
  hybrid_ai_trading.risk.risk_manager

This file previously contained accidental PowerShell content and broke Phase-4 compileall.
"""
from __future__ import annotations

from hybrid_ai_trading.risk.risk_manager import RiskManager  # re-export

__all__ = ["RiskManager"]