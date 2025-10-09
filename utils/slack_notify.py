import json
import os
import urllib.request


def notify(text: str, blocks=None) -> bool:
    url = os.environ.get("QP_SLACK_WEBHOOK")
    if not url:
        return False
    payload = {"text": text}
    if blocks:
        payload["blocks"] = blocks
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            r.read()
        return True
    except Exception:
        return False
