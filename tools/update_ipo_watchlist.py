from __future__ import annotations

import csv
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any


# Input: you or another tool populate this CSV from any IPO source/API.
# Expected columns (header row):
#   symbol, company_name, listing_date, exchange, country, sector,
#   price_range_low, price_range_high
IPO_CSV_PATH = Path("data") / "ipo_feed" / "ipo_candidates.csv"

# Output: JSONL consumed by Intel pipeline / Notion / dashboards.
IPO_JSONL_PATH = Path("logs") / "ipo_watchlist.jsonl"


@dataclass
class IpoEntry:
    symbol: str
    company_name: str
    listing_date: str
    exchange: str
    country: str
    sector: str
    price_range_low: float | None
    price_range_high: float | None

    origin_region: str           # "US", "HK", "INTL_OTHER"
    is_hk_origin: bool
    is_international: bool
    phase5_candidate: bool       # simple heuristic flag
    phase5_notes: str            # why/why not


def parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def classify_origin(country: str, company_name: str) -> tuple[str, bool, bool]:
    c = (country or "").strip().upper()
    name_upper = (company_name or "").upper()

    is_hk = (
        c in {"HK", "HONG KONG", "HONG-KONG", "HONGKONG"}
        or " HONG KONG" in name_upper
    )
    if c in {"US", "USA", "UNITED STATES", "UNITED STATES OF AMERICA"}:
        region = "US"
    elif is_hk:
        region = "HK"
    else:
        region = "INTL_OTHER"

    is_international = region != "US"
    return region, is_hk, is_international


def decide_phase5_candidate(entry: IpoEntry) -> tuple[bool, str]:
    """
    Very simple heuristic for now:

    - Exchange must be NASDAQ.
    - Sector in a watchlist (e.g. Tech / Comm / Consumer).
    - Listing date non-empty (you can refine with date windows later).
    """
    if entry.exchange.upper() != "NASDAQ":
        return False, "not_nasdaq"

    sector = (entry.sector or "").upper()
    sector_watch = {"TECHNOLOGY", "INFORMATION TECHNOLOGY", "COMMUNICATION SERVICES", "HEALTH CARE", "HEALTHCARE", "CONSUMER DISCRETIONARY"}

    if sector and sector not in sector_watch:
        return False, f"sector_not_in_watchlist:{entry.sector}"

    if not entry.listing_date:
        return False, "missing_listing_date"

    # If we reach here, treat as candidate for Phase-5 research.
    return True, "nasdaq_sector_watch"


def load_ipo_candidates(csv_path: Path) -> List[Dict[str, Any]]:
    if not csv_path.exists():
        print(f"[IPO] WARNING: IPO CSV not found: {csv_path}")
        return []

    rows: List[Dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    print(f"[IPO] Loaded {len(rows)} IPO rows from {csv_path}")
    return rows


def build_ipo_watchlist() -> None:
    raw_rows = load_ipo_candidates(IPO_CSV_PATH)
    if not raw_rows:
        print("[IPO] No IPO rows to process. Exiting.")
        return

    out_entries: List[Dict[str, Any]] = []

    for row in raw_rows:
        exchange = (row.get("exchange") or "").strip().upper()
        if exchange != "NASDAQ":
            continue

        symbol        = (row.get("symbol") or "").strip().upper()
        company_name  = (row.get("company_name") or "").strip()
        listing_date  = (row.get("listing_date") or "").strip()
        country       = (row.get("country") or "").strip()
        sector        = (row.get("sector") or "").strip()

        pr_low  = parse_float(row.get("price_range_low"))
        pr_high = parse_float(row.get("price_range_high"))

        origin_region, is_hk_origin, is_international = classify_origin(country, company_name)

        base_entry = IpoEntry(
            symbol=symbol,
            company_name=company_name,
            listing_date=listing_date,
            exchange=exchange,
            country=country,
            sector=sector,
            price_range_low=pr_low,
            price_range_high=pr_high,
            origin_region=origin_region,
            is_hk_origin=is_hk_origin,
            is_international=is_international,
            phase5_candidate=False,
            phase5_notes="",
        )

        phase5_flag, notes = decide_phase5_candidate(base_entry)
        base_entry.phase5_candidate = phase5_flag
        base_entry.phase5_notes = notes

        out_entries.append(asdict(base_entry))

    IPO_JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with IPO_JSONL_PATH.open("w", encoding="utf-8") as f:
        for entry in out_entries:
            f.write(json.dumps(entry))
            f.write("\n")

    print(f"[IPO] Wrote {len(out_entries)} IPO watch rows to {IPO_JSONL_PATH}")


def main() -> None:
    build_ipo_watchlist()


if __name__ == "__main__":
    main()