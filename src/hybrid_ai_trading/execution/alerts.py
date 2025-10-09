from __future__ import annotations
import os, time
from typing import Dict, Any, Optional

try:
    import requests  # type: ignore
except Exception:
    requests = None  # type: ignore


class Alerts:
    """
    Lightweight alerts for Slack + Telegram.
    Configure via env (set one or both):
      ALERT_SLACK_WEBHOOK=https://hooks.slack.com/services/XXX/YYY/ZZZ
      ALERT_TG_TOKEN=123456:ABCDEF...
      ALERT_TG_CHAT_ID=-100123456789
    If none configured, methods are no-ops.
    """

    def __init__(self, throttle_sec: float = 0.0) -> None:
        self.slack = os.getenv("ALERT_SLACK_WEBHOOK") or ""
        self.tg_token = os.getenv("ALERT_TG_TOKEN") or ""
        self.tg_chat = os.getenv("ALERT_TG_CHAT_ID") or ""
        self.throttle_sec = float(throttle_sec or 0.0)
        self._last_sent = 0.0

    # ---------- public ----------
    def notify(self, kind: str, payload: Dict[str, Any]) -> None:
        if not (self.slack or (self.tg_token and self.tg_chat)):
            return  # nothing configured
        now = time.time()
        if self.throttle_sec > 0 and (now - self._last_sent) < self.throttle_sec:
            return
        self._last_sent = now

        text = self._format(kind, payload)
        try:
            self._send_slack(text)
        except Exception:
            pass
        try:
            self._send_telegram(text)
        except Exception:
            pass

    # ---------- helpers ----------
    @staticmethod
    def _format(kind: str, p: Dict[str, Any]) -> str:
        # compact ASCII one-liner for chats
        fields = []
        order = ("strategy","exchange","broker","symbol","side","qty","px","status","reason","pnl","bar_ts")
        for k in order:
            v = p.get(k, None)
            if v is not None:
                fields.append(f"{k}={v}")
        return f"[{kind.upper()}] " + " ".join(fields)

    def _send_slack(self, text: str) -> None:
        if not self.slack or requests is None:
            return
        try:
            requests.post(self.slack, json={"text": text}, timeout=5)
        except Exception:
            pass

    def _send_telegram(self, text: str) -> None:
        if not (self.tg_token and self.tg_chat) or requests is None:
            return
        try:
            url = f"https://api.telegram.org/bot{self.tg_token}/sendMessage"
            data = {"chat_id": self.tg_chat, "text": text, "disable_web_page_preview": True}
            requests.post(url, data=data, timeout=5)
        except Exception:
            pass