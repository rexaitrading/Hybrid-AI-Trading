from typing import Any, Dict

from hybrid_ai_trading.execution.execution_engine import ExecutionEngine
from hybrid_ai_trading.runners.nvda_phase5_live_runner import build_live_config


def _make_phase5_engine(
    dry_run: bool = True,
    phase5_enabled: bool = True,
) -> ExecutionEngine:
    """
    Helper to build an ExecutionEngine with Phase-5 no-averaging config.

    Uses the same live-style config as nvda_phase5_live_runner.build_live_config(),
    then tweaks the Phase-5 flags for the specific test.
    """
    cfg: Dict[str, Any] = build_live_config()

    # Ensure dry_run + Phase-5 flags line up with the test parameters
    cfg["dry_run"] = dry_run
    cfg["phase5_no_averaging_down_enabled"] = phase5_enabled
    if isinstance(cfg.get("phase5"), dict):
        cfg["phase5"]["no_averaging_down_enabled"] = phase5_enabled

    engine = ExecutionEngine(config=cfg)

    # Ensure RiskManager sees the Phase-5 flag as well
    rm = getattr(engine, "risk_manager", None)
    if rm is not None:
        try:
            setattr(rm, "phase5_no_averaging_down_enabled", phase5_enabled)
        except Exception:
            pass

    return engine


def test_phase5_no_averaging_engine_guard_blocks_second_buy() -> None:
    """
    Phase-5 engine-level guard:
    - First BUY for NVDA is allowed (filled).
    - Second BUY for NVDA in the same process is rejected with the engine guard reason.
    """
    engine = _make_phase5_engine(dry_run=True, phase5_enabled=True)

    # First BUY should go through.
    res1 = engine.place_order("NVDA", "BUY", 1.0, 1.0)
    assert res1["status"] == "filled"
    assert res1["symbol"] == "NVDA"
    assert res1["side"] == "BUY"

    # Second BUY should be blocked by the engine-level no-averaging-down guard.
    res2 = engine.place_order("NVDA", "BUY", 1.0, 1.0)
    assert res2["status"] == "rejected"
    assert res2["reason"] == "no_averaging_down_phase5_engine_guard"


def test_phase5_no_averaging_engine_guard_respects_disabled_flag() -> None:
    """
    When Phase-5 no-averaging is disabled in config, the engine guard should not block.
    Both BUYs should be allowed (filled).
    """
    engine = _make_phase5_engine(dry_run=True, phase5_enabled=False)

    res1 = engine.place_order("NVDA", "BUY", 1.0, 1.0)
    assert res1["status"] == "filled"

    res2 = engine.place_order("NVDA", "BUY", 1.0, 1.0)
    assert res2["status"] == "filled"