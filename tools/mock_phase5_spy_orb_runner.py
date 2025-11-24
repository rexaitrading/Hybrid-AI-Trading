"""
Mock Phase-5 SPY gating runner (using shared helpers).

- Loads Phase-5 decisions for SPY from logs/spy_phase5_decisions.json
  via tools.phase5_gating_helpers.
- Prints PHASE5 BLOCKED lines only for blocked trades.
- Prints a summary line at the end.
"""

from hybrid_ai_trading.tools.phase5_gating_helpers import load_decisions_for_symbol


def main() -> None:
    symbol = "SPY"
    decisions = load_decisions_for_symbol(symbol)

    total = len(decisions)
    blocked = 0

    for dec in decisions:
        if not dec.allow_flag:
            blocked += 1
            print(f"PHASE5 BLOCKED: {symbol} at {dec.entry_ts}")

    print(
        f"Summary: symbol={symbol} total_trades={total} blocked={blocked} "
        f"allowed={total - blocked}"
    )


if __name__ == "__main__":
    main()
