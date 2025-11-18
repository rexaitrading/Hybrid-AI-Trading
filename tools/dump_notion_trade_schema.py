import os
import json
import sys
import requests

def main() -> None:
    token = os.environ.get("NOTION_TOKEN")
    db_id = os.environ.get("NOTION_TRADE_ID")
    version = os.environ.get("NOTION_VERSION", "2025-09-03")

    if not token:
        print("ERROR: NOTION_TOKEN not set", file=sys.stderr)
        sys.exit(1)
    if not db_id:
        print("ERROR: NOTION_TRADE_ID not set", file=sys.stderr)
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": version,
        "Content-Type": "application/json",
    }

    url = f"https://api.notion.com/v1/databases/{db_id}"
    print(f"GET {url}")
    resp = requests.get(url, headers=headers)
    print("STATUS:", resp.status_code)
    try:
        data = resp.json()
    except Exception:
        print("RAW BODY:", resp.text)
        raise

    # Only print id, title, and property names/types for clarity
    out = {
        "id": data.get("id"),
        "title": data.get("title"),
        "properties": {},
    }

    props = data.get("properties", {})
    for name, meta in props.items():
        out["properties"][name] = {
            "id": meta.get("id"),
            "type": meta.get("type"),
        }

    print(json.dumps(out, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()