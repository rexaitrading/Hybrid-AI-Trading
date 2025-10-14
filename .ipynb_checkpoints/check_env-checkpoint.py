import os

from dotenv import load_dotenv

load_dotenv()
k = os.getenv("COINAPI_KEY")
print("COINAPI_KEY present:", bool(k))
print("Value preview:", (k[:8] + "…") if k else None)
