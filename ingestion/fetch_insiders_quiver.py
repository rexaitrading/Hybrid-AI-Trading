import os, json, datetime as dt
from dateutil.relativedelta import relativedelta
import requests
from dotenv import load_dotenv
from utils.io_state import versioned_json_path, atomic_write_json, load_checkpoint, save_checkpoint

load_dotenv()
API_KEY = os.getenv("BENZINGA_API_KEY")
BASE_DIR = os.path.join("data", "earnings_calendar")

def fetch_earnings(start: str, end: str):
    url = "https://api.benzinga.com/api/v2.1/calendar/earnings"
    params = {"token": API_KEY,
            "parameters[date_from]": start,
            "parameters[date_to]": end,
            "pagesize": 1000}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

if __name__ == "__main__":
    # 讀取上次抓取到「哪一天」
    last_day = load_checkpoint("earnings_day_ckpt", dt.date.today().strftime("%Y-%m-%d"))
    start = last_day
    end = (dt.date.fromisoformat(start) + relativedelta(days=7)).strftime("%Y-%m-%d")

    data = fetch_earnings(start, end)

    # day=今天（用來分區）
    day = dt.date.today().strftime("%Y-%m-%d")
    out_path = versioned_json_path(BASE_DIR, day, f"earnings_{start}_to_{end}")
    atomic_write_json(out_path, data)
    print("✅ saved:", out_path, "items:", len(data.get("earnings", [])))

    # 推進檢查點（下次從更後面開始）
    save_checkpoint("earnings_day_ckpt", (dt.date.fromisoformat(end)).strftime("%Y-%m-%d"))