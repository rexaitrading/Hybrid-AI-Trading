from __future__ import annotations

from datetime import datetime

from hybrid_ai_trading.tools.notion_csv_logger import log_trade


def log_closed_trade(
    *,
    symbol: str,
    setup: str,
    context_tags: list[str],
    entry_time: datetime,
    exit_time: datetime,
    entry: float,
    exit: float,
    qty: int,
    fees: float = 0.0,
    slippage: float = 0.0,
    r_multiple: float = 0.0,
    notes: str = "",
    replay_id: str = "",
) -> None:
    """
    Log a completed trade to logs/theory_trades.csv (UTF-8 no BOM) for Notion import.
    Context is comma-joined for Notion multi-select friendliness.
    """
    context = ",".join(context_tags or [])
    pnl = (exit - entry) * qty - fees - slippage

    log_trade(
        path="logs/theory_trades.csv",
        Date=entry_time.date().isoformat(),
        Ticker=symbol,
        Setup=setup,
        Context=context,
        EntryTime=entry_time.isoformat(timespec="minutes"),
        ExitTime=exit_time.isoformat(timespec="minutes"),
        Entry=entry,
        Exit=exit,
        Qty=qty,
        Fees=fees,
        Slippage=slippage,
        RM=r_multiple,
        PnL=round(pnl, 2),
        Notes=notes,
        ReplayID=replay_id,
    )
