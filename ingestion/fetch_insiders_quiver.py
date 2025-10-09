import datetime as dt
import os

import requests
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv

from utils.io_state import (
    atomic_write_json,
    load_checkpoint,
    save_checkpoint,
    versioned_json_path,
)

load_dotenv()
API_KEY = os.getenv("BENZINGA_API_KEY")
BASE_DIR = os.path.join("data", "earnings_calendar")


def fetch_earnings(start: str, end: str):
    url = "https://api.benzinga.com/api/v2.1/calendar/earnings"
    params = {
        "token": API_KEY,
        "parameters[date_from]": start,
        "parameters[date_to]": end,
        "pagesize": 1000,
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


if __name__ == "__main__":
    # è®€å–ä¸Šæ¬¡æŠ“å–åˆ°ã€Œå“ªä¸€å¤©ã€
    last_day = load_checkpoint(
        "earnings_day_ckpt", dt.date.today().strftime("%Y-%m-%d")
    )
    start = last_day
    end = (dt.date.fromisoformat(start) + relativedelta(days=7)).strftime("%Y-%m-%d")

    data = fetch_earnings(start, end)

    # day=ä»Šå¤©ï¼ˆç”¨ä¾†åˆ†å€ï¼‰
    day = dt.date.today().strftime("%Y-%m-%d")
    out_path = versioned_json_path(BASE_DIR, day, f"earnings_{start}_to_{end}")
    atomic_write_json(out_path, data)
    print("âœ… saved:", out_path, "items:", len(data.get("earnings", [])))

    # æŽ¨é€²æª¢æŸ¥é»žï¼ˆä¸‹æ¬¡å¾žæ›´å¾Œé¢é–‹å§‹ï¼‰
    save_checkpoint(
        "earnings_day_ckpt", (dt.date.fromisoformat(end)).strftime("%Y-%m-%d")
    )
