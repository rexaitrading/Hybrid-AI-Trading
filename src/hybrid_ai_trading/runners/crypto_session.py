from datetime import datetime, time as dtime, timezone

ASIA_START_UTC = dtime(0, 0)
ASIA_END_UTC   = dtime(8, 0)

def is_asia_session_utc(now_utc=None) -> bool:
    now = now_utc or datetime.now(timezone.utc).time()
    return ASIA_START_UTC <= now < ASIA_END_UTC
