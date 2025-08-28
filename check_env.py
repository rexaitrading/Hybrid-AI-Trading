import os
from dotenv import load_dotenv

# è¼‰å…¥ .env
load_dotenv()

# ä½ æƒ³æª¢æŸ¥çš„å…¨éƒ¨ key
keys = [
    "bd4e0dc3-8de0-44e2-8894-c6e3d491f8a3",
    "dg9YCsmMS3FIAwsf1OkjnBX2xvelb3fX",
    "PK66817E4JPYYI9BFVCR",
    "Nc7j4BramB0SXWTsHd3UcieLfelxLdWIEorkRboV**",
    "bz.SOVFSXG7PUMSN57OBMVWLLRMU7XJNNZJ",
    "110638",
    "247542"]

for key in keys:
    value = os.getenv(key)
    if value:
        print(f"{key} present: True, preview: {value[:8]}...")
    else:
        print(f"{key} MISSING âŒ")

