import os, time, json, base64, sys, requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric import utils as asn1utils

api_key = os.environ.get("COINBASE_ADV_KEY_NAME")
pem     = os.environ.get("COINBASE_ADV_PRIVATE_KEY")
if not api_key or not pem:
    print("Missing COINBASE_ADV_KEY_NAME/COINBASE_ADV_PRIVATE_KEY", file=sys.stderr); sys.exit(1)

priv = serialization.load_pem_private_key(pem.encode('utf-8'), password=None)
if not isinstance(priv, ec.EllipticCurvePrivateKey) or priv.curve.name not in ('secp256r1','prime256v1'):
    print("Private key is not EC P-256 (ES256 required)", file=sys.stderr); sys.exit(2)

def b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b'=').decode('ascii')

method, path = "GET", "/v2/user"
now = int(time.time())

# Header must include kid (key name)
header = {"alg":"ES256","typ":"JWT","kid": api_key}

# Claims must include aud for Wallet
claims = {
    "iss": api_key,
    "sub": api_key,
    "aud": "retail_rest_api",
    "nbf": now - 5,
    "iat": now,
    "exp": now + 110,
    "uri": f"{method} {path}"
}

seg1 = b64url(json.dumps(header,separators=(',',':')).encode())
seg2 = b64url(json.dumps(claims,separators=(',',':')).encode())
to_sign = f"{seg1}.{seg2}".encode()

sig_der = priv.sign(to_sign, ec.ECDSA(hashes.SHA256()))
r, s = asn1utils.decode_dss_signature(sig_der)
size = priv.curve.key_size // 8
sig_raw = r.to_bytes(size,'big') + s.to_bytes(size,'big')
seg3 = b64url(sig_raw)

jwt = f"{seg1}.{seg2}.{seg3}"

r = requests.get("https://api.coinbase.com"+path,
                 headers={"Authorization":"Bearer "+jwt},
                 timeout=20)
print("STATUS", r.status_code)
print("BODY", r.text[:600])
