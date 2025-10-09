import csv
import pathlib
from collections import defaultdict
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal


def d(x):  # 2-decimal rounding
    return float(Decimal(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def parse_date(ts):
    # ts like 2025-10-03T18:54:00 -> date part
    try:
        return ts.split("T", 1)[0]
    except:
        return ""


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    orders_path = pathlib.Path("logs") / "orders.csv"
    rep_dir = pathlib.Path("logs") / "reports"
    rep_dir.mkdir(parents=True, exist_ok=True)
    out_md = rep_dir / f"{today}_report.md"

    if not orders_path.exists():
        out_md.write_text(
            f"# Daily Report {today}\n\nNo orders.csv yet.\n", encoding="utf-8"
        )
        print(f"[REPORT] {out_md} (no data)")
        return

    rows = []
    with orders_path.open("r", encoding="utf-8", errors="ignore") as f:
        rd = csv.DictReader(f)
        for r in rd:
            if parse_date(r.get("ts", "")) == today:
                rows.append(r)

    if not rows:
        out_md.write_text(
            f"# Daily Report {today}\n\nNo rows for today.\n", encoding="utf-8"
        )
        print(f"[REPORT] {out_md} (empty day)")
        return

    # Aggregations
    by_status = defaultdict(int)
    by_symbol = defaultdict(
        lambda: {
            "orders": 0,
            "filled": 0,
            "cancelled": 0,
            "abort": 0,
            "submitted": 0,
            "buy_qty": 0.0,
            "sell_qty": 0.0,
            "buy_notional": 0.0,
            "sell_notional": 0.0,
            "realized_pnl": 0.0,
        }
    )
    total_orders = 0

    for r in rows:
        total_orders += 1
        sym = (r.get("symbol") or "").upper()
        side = (r.get("side") or "").upper()
        qty = float(r.get("qty") or 0)
        status = (r.get("status") or "").upper()
        limit = (
            float(r.get("limit") or 0) if (r.get("limit") or "").strip() != "" else None
        )
        avg = (
            float(r.get("avgFill") or 0)
            if (r.get("avgFill") or "").strip() != ""
            else None
        )

        by_status[status] += 1
        S = by_symbol[sym]
        S["orders"] += 1
        if status == "FILLED":
            S["filled"] += 1
            # cash flow for naive realized PnL (flat end assumption)
            if side == "BUY":
                S["buy_qty"] += qty
                if avg:
                    S["buy_notional"] += qty * avg
            elif side == "SELL":
                S["sell_qty"] += qty
                if avg:
                    S["sell_notional"] += qty * avg
        elif status == "CANCELLED":
            S["cancelled"] += 1
        elif status == "ABORT":
            S["abort"] += 1
        elif status == "SUBMITTED":
            S["submitted"] += 1

    # compute naive realized PnL (if net flat for symbol)
    for sym, S in by_symbol.items():
        q_buy, q_sell = S["buy_qty"], S["sell_qty"]
        if (
            abs(q_buy - q_sell) < 1e-9
            and q_buy > 0
            and S["buy_notional"]
            and S["sell_notional"]
        ):
            S["realized_pnl"] = d(S["sell_notional"] - S["buy_notional"])
        else:
            S["realized_pnl"] = 0.0  # keep simple; open PnL ignored

    # Suggestions
    suggestions = []
    for sym, S in by_symbol.items():
        if S["orders"] == 0:
            continue
        fillable = S["filled"] + S["cancelled"]
        fill_rate = (S["filled"] / fillable) * 100 if fillable > 0 else 0.0

        # if lots of ABORT -> after-hours attempts
        if S["abort"] >= 2:
            suggestions.append(
                f"- **{sym}**: Many ABORTs → after-hours. Keep `ABORT_IF_NO_QUOTE=true` (good)."
            )

        # if low fill rate → suggest +1 bps for tomorrow
        if fillable >= 3 and fill_rate < 60:
            bump = 1 if sym in ("MSFT", "NVDA") else 1
            suggestions.append(
                f"- **{sym}**: Fill rate {fill_rate:.0f}% (<60%). Try **+{bump} bps** slippage tomorrow."
            )

        # if 100% IOC cancels during RTH (no ABORTs) → bump bps too
        if S["cancelled"] >= 3 and S["abort"] == 0 and S["filled"] == 0:
            suggestions.append(
                f"- **{sym}**: All IOC cancelled. Increase slippage bps slightly or wait for liquidity windows."
            )

    # Build Markdown
    md = []
    md.append(f"# Daily Report — {today}")
    md.append("")
    md.append("## Summary")
    md.append(
        f"- Total orders: **{total_orders}**  |  Filled: **{by_status['FILLED']}**  |  Cancelled: **{by_status['CANCELLED']}**  |  Submitted(resting): **{by_status['SUBMITTED']}**  |  Abort: **{by_status['ABORT']}**"
    )
    md.append("")
    md.append("## Per-Symbol")
    for sym, S in sorted(by_symbol.items()):
        fillable = S["filled"] + S["cancelled"]
        fill_rate = (S["filled"] / fillable) * 100 if fillable > 0 else 0.0
        md.append(
            f"**{sym}** — orders {S['orders']}, filled {S['filled']}, cancelled {S['cancelled']}, abort {S['abort']}, fill-rate {fill_rate:.0f}%  |  realized PnL: **${S['realized_pnl']:.2f}**"
        )
    md.append("")
    md.append("## Suggestions for Tomorrow")
    if suggestions:
        md.extend(suggestions)
    else:
        md.append("- Looks good. Keep current bps and IOC settings.")
    md.append("")
    md.append(
        "> Note: PnL is a simple realized estimate using order avg fills. Open PnL not included."
    )

    out_md.write_text("\n".join(md), encoding="utf-8")
    print(f"[REPORT] {out_md}")


if __name__ == "__main__":
    main()
