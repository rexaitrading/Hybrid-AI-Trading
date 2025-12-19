from __future__ import annotations

# Placeholder module to satisfy legacy import paths during coverage sweeps.
# Real TWAP execution is provided by hybrid_ai_trading.algos.* wrappers.

class TWAPExecutor:
    def __init__(self, *args, **kwargs) -> None:
        raise RuntimeError("TWAPExecutor is not implemented in this build (stub).")


# Back-compat alias (some older code may import TwapExecutor)
TwapExecutor = TWAPExecutor