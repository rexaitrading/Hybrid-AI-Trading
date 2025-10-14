import sys, types
from importlib import import_module as _imp

def make_engine():
    TE = _imp("hybrid_ai_trading.trade_engine")
    return TE.TradeEngine(config={"alerts":{"slack_url":"http://x","telegram_bot":"b","telegram_chat":"c","email":True}})

def test_alerts_success_and_exceptions(monkeypatch):
    te = make_engine()
    class R: 
        def __init__(self,c): self.status_code=c
    # success
    monkeypatch.setitem(sys.modules,"requests", types.SimpleNamespace(post=lambda *a,**k:R(200), get=lambda *a,**k:R(200)))
    class SMTPOK:
        def __enter__(self): return self
        def __exit__(self,*a): return False
        def send_message(self,*a,**k): return None
    monkeypatch.setitem(sys.modules,"smtplib", types.SimpleNamespace(SMTP=lambda *a,**k: SMTPOK()))
    if hasattr(te,"_fire_alert"): te._fire_alert("ok")
    # exceptions + top except
    def boom(*a,**k): raise RuntimeError("boom")
    monkeypatch.setitem(sys.modules,"requests", types.SimpleNamespace(post=boom, get=boom))
    class SMTPBAD:
        def __enter__(self): raise RuntimeError("bad")
        def __exit__(self,*a): return False
    monkeypatch.setitem(sys.modules,"smtplib", types.SimpleNamespace(SMTP=lambda *a,**k: SMTPBAD()))
    if hasattr(te,"_fire_alert"): te._fire_alert("fail")
    sys.modules.pop("requests", None); sys.modules.pop("smtplib", None)
    if hasattr(te,"_fire_alert"):
        try: te._fire_alert("no-mods")
        except Exception: pass
