import os
import socket
import sys

host = os.getenv("IB_HOST", "127.0.0.1")
port = int(os.getenv("IB_PORT", "0"))
acct = os.getenv("IB_ACCOUNT", "")
envf = ".env"
print(f"Pre-flight: {envf} host={host} port={port} account={acct}")
# Port reachability
s = socket.socket()
s.settimeout(1.5)
try:
    s.connect((host, port))
    print("Ã¢Å“â€¦ Port reachable")
    s.close()
except Exception as e:
    print(f"Ã¢ÂÅ’ Port check failed: {e}")
    sys.exit(1)
if not acct:
    print("Ã¢Å¡Â Ã¯Â¸Â IB_ACCOUNT missing (ok in dev; set before live).")
print("Pre-flight OK.")
