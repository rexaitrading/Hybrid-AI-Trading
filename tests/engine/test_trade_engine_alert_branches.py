import types, pytest
from hybrid_ai_trading.trade_engine import TradeEngine

@pytest.fixture()
def alert_eng():
    # install alert env var names in config
    cfg = {"alerts":{
        "slack_webhook_env":"SLACK_URL",
        "telegram_bot_env":"TG_BOT",
        "telegram_chat_id_env":"TG_CHAT",
        "email_env":"ALERT_EMAIL"
    }}
    return TradeEngine(config=cfg)

def test_alert_errors(monkeypatch, alert_eng):
    # Return tokens from os.getenv; then throw in each transport
    monkeypatch.setattr("os.getenv", lambda k, d=None: {"SLACK_URL":"x","TG_BOT":"b","TG_CHAT":"c","ALERT_EMAIL":"u@x"} .get(k, d), raising=False)
    monkeypatch.setattr("requests.post", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("slack down")), raising=False)
    monkeypatch.setattr("requests.get",  lambda *a, **k: (_ for _ in ()).throw(RuntimeError("tg down")),    raising=False)
    class BadSMTP:
        def __init__(self, *a, **k): pass
        def __enter__(self): raise RuntimeError("smtp down")
        def __exit__(self, *a): pass
    monkeypatch.setattr("smtplib.SMTP", BadSMTP, raising=False)
    r = alert_eng.alert("hi")
    assert r.get("slack")=="error" and r.get("telegram")=="error" and r.get("email")=="error"

def test_alert_success(monkeypatch, alert_eng):
    # Success codes without network I/O
    monkeypatch.setattr("os.getenv", lambda k, d=None: {"SLACK_URL":"x","TG_BOT":"b","TG_CHAT":"c","ALERT_EMAIL":"u@x"} .get(k, d), raising=False)
    class Resp:
        def __init__(self, code): self.status_code = code
    monkeypatch.setattr("requests.post", lambda *a, **k: Resp(200), raising=False)
    monkeypatch.setattr("requests.get",  lambda *a, **k: Resp(200), raising=False)
    class OkSMTP:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self,*a): pass
        def send_message(self, *a, **k): pass
    monkeypatch.setattr("smtplib.SMTP", OkSMTP, raising=False)
    r = alert_eng.alert("hi")
    assert r["slack"]==200 and r["telegram"]==200 and r["email"]=="sent"
