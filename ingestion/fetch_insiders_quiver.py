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
    # Ã¨Â®â‚¬Ã¥Ââ€“Ã¤Â¸Å Ã¦Â¬Â¡Ã¦Å â€œÃ¥Ââ€“Ã¥Ë†Â°Ã£â‚¬Å’Ã¥â€œÂªÃ¤Â¸â‚¬Ã¥Â¤Â©Ã£â‚¬Â
    last_day = load_checkpoint(
        "earnings_day_ckpt", dt.date.today().strftime("%Y-%m-%d")
    )
    start = last_day
    end = (dt.date.fromisoformat(start) + relativedelta(days=7)).strftime("%Y-%m-%d")

    data = fetch_earnings(start, end)

    # day=Ã¤Â»Å Ã¥Â¤Â©Ã¯Â¼Ë†Ã§â€Â¨Ã¤Â¾â€ Ã¥Ë†â€ Ã¥Ââ‚¬Ã¯Â¼â€°
    day = dt.date.today().strftime("%Y-%m-%d")
    out_path = versioned_json_path(BASE_DIR, day, f"earnings_{start}_to_{end}")
    atomic_write_json(out_path, data)
    print("Ã¢Å“â€¦ saved:", out_path, "items:", len(data.get("earnings", [])))

    # Ã¦Å½Â¨Ã©â‚¬Â²Ã¦ÂªÂ¢Ã¦Å¸Â¥Ã©Â»Å¾Ã¯Â¼Ë†Ã¤Â¸â€¹Ã¦Â¬Â¡Ã¥Â¾Å¾Ã¦â€ºÂ´Ã¥Â¾Å’Ã©ÂÂ¢Ã©â€“â€¹Ã¥Â§â€¹Ã¯Â¼â€°
    save_checkpoint(
        "earnings_day_ckpt", (dt.date.fromisoformat(end)).strftime("%Y-%m-%d")
    )
