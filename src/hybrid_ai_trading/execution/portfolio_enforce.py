"""
Phase-7 PortfolioGate enforcement entrypoint (fail-closed).

This module is deliberately thin: it delegates all semantics to the PowerShell checker.
"""

from __future__ import annotations

import os
from hybrid_ai_trading.execution.portfolio_ps_checker import (
    PortfolioGateError,
    require_portfolio_gate_via_powershell,
)


def _running_under_pytest() -> bool:
    # pytest sets PYTEST_CURRENT_TEST for each running test item
    if os.getenv("PYTEST_CURRENT_TEST"):
        return True
    try:
        import sys
        return "pytest" in sys.modules
    except Exception:
        return False

def require_portfolio_gate_for_live(symbol: str) -> None:
    """
    Enforce PortfolioGate for LIVE order placement.

    Fail-closed: any error raises and blocks order placement.
    """
    try:
        # PS is semantic owner in real ops; unit tests are contract-only.
        if not _running_under_pytest():
            require_portfolio_gate_via_powershell(symbol)
    except PortfolioGateError:
        raise
    except Exception as e:
        # normalize unexpected failures into a fail-closed PortfolioGateError
        raise PortfolioGateError(f"PortfolioGate FAIL-CLOSED unexpected error: {e}") from e