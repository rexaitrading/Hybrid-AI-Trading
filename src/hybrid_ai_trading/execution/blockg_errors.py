from __future__ import annotations


class BlockGNotReady(RuntimeError):
    """Fail-closed Block-G gate exception (shared across contract + enforcement)."""
    pass
