import datetime as dt
import os

import requests
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv

from utils.io_state import (
    atomic_write_json,
    json_path,
    load_checkpoint,
    save_checkpoint,
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
    # è®€å–ä¸Šæ¬¡æŠ“åˆ°çš„æ—¥æœŸï¼Œé è¨­å¾€å‰ä¸€å¤©
    start = load_checkpoint("earnings_day_ckpt", dt.date.today().strftime("%Y-%m-%d"))
    end = (dt.date.fromisoformat(start) + relativedelta(days=7)).strftime("%Y-%m-%d")

    data = fetch_earnings(start, end)

    day = dt.date.today().strftime("%Y-%m-%d")
    out_path = json_path(BASE_DIR, day, f"earnings_{start}_to_{end}")
    atomic_write_json(out_path, data, indent=2)
    print("âœ… Saved:", out_path, "items:", len(data.get("earnings", [])))

    # æ›´æ–° checkpoint
    save_checkpoint("earnings_day_ckpt", dt.date.fromisoformat(end).strftime("%Y-%m-%d"))
