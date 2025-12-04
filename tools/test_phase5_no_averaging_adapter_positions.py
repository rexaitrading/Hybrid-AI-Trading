"""
Test the Phase-5 no-averaging-down adapter on a real-ish RiskManager.

We simulate:
- long position in NVDA (qty=1.0)
- call phase5_no_averaging_down_for_symbol("NVDA", side="BUY") -> should block
- call phase5_no_averaging_down_for_symbol("NVDA", side="SELL") -> should allow
"""

from __future__ import annotations

from hybrid_ai_trading.risk.risk_manager import RiskManager


def main() -> None:
    rm = RiskManager()
    # Simulate positions dict used by adapter helper
    rm.positions = {"NVDA": 1.0}

    print("=== Phase-5 no-averaging adapter position test ===")
    print("Initial rm.positions:", rm.positions)

    # 1) Pyramiding attempt: long + BUY -> expect block
    allow1, reason1 = rm.phase5_no_averaging_down_for_symbol("NVDA", side="BUY", entry_ts="TEST_TS")
    print("\n[1] long + BUY (pyramiding)")
    print("  allow:", allow1, "reason:", reason1)

    # 2) Closing/flip attempt: long + SELL -> expect allow
    allow2, reason2 = rm.phase5_no_averaging_down_for_symbol("NVDA", side="SELL", entry_ts="TEST_TS")
    print("\n[2] long + SELL (close/flip)")
    print("  allow:", allow2, "reason:", reason2)


if __name__ == "__main__":
    main()

def test_phase5_no_averaging_adapter_positions() -> None:
    """
    Pytest wrapper that exercises main() once. This ensures the
    Phase-5 no-averaging adapter/positions test script can run
    end-to-end without raising exceptions.
    """
    main()