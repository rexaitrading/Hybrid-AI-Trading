import os, time, json, base64, sys, requests
from typing import Optional
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric import utils as asn1utils

API_KEY = os.environ.get("COINBASE_ADV_KEY_NAME")
PEM     = os.environ.get("COINBASE_ADV_PRIVATE_KEY")
if not API_KEY or not PEM:
    print("FATAL: Missing COINBASE_ADV_KEY_NAME / COINBASE_ADV_PRIVATE_KEY", file=sys.stderr); sys.exit(1)

def key_id_from_name(name:str)->Optional[str]:
    try:
        parts=name.split('/')
        i=parts.index('apiKeys'); return parts[i+1]
    except Exception:
        return None

KEY_ID = key_id_from_name(API_KEY)

# Load EC P-256
try:
    priv = serialization.load_pem_private_key(PEM.encode(), password=None)
except Exception as e:
    print("FATAL: cannot load PEM:", repr(e), file=sys.stderr); sys.exit(2)
if not isinstance(priv, ec.EllipticCurvePrivateKey) or priv.curve.name not in ('secp256r1','prime256v1'):
    print("FATAL: private key is not EC P-256 (ES256 required)", file=sys.stderr); sys.exit(3)

def b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b'=').decode()

METHOD="GET"; PATH="/v2/user"
KIDS = [API_KEY] + ([KEY_ID] if KEY_ID else []) + [None]
AUDS = ["retail_rest_api","api.coinbase.com","retail_api","retail"]
URIS = [f"{METHOD} {PATH}", PATH]

def build_jwt(kid, aud, uri):
    now=int(time.time())
    header={"alg":"ES256","typ":"JWT"}
    if kid: header["kid"]=kid
    claims={"iss":API_KEY,"sub":API_KEY,"aud":aud,"nbf":now-5,"iat":now,"exp":now+110,"uri":uri}
    seg1=b64url(json.dumps(header,separators=(',',':')).encode())
    seg2=b64url(json.dumps(claims,separators=(',',':')).encode())
    to_sign=f"{seg1}.{seg2}".encode()
    sig_der=priv.sign(to_sign, ec.ECDSA(hashes.SHA256()))
    r,s=asn1utils.decode_dss_signature(sig_der)
    size=priv.curve.key_size//8
    seg3=b64url(r.to_bytes(size,'big')+s.to_bytes(size,'big'))
    return f"{seg1}.{seg2}.{seg3}"

results=[]
for kid in KIDS:
    for aud in AUDS:
        for uri in URIS:
            try:
                jwt=build_jwt(kid,aud,uri)
                r=requests.get("https://api.coinbase.com"+PATH,
                               headers={"Authorization":"Bearer "+jwt},
                               timeout=20)
                ok=200<=r.status_code<300
                rec={"kid":kid or "<none>","aud":aud,"uri":uri,"status":r.status_code,"ok":ok,"body":r.text[:200]}
                results.append(rec)
                if ok:
                    print("=== SUCCESS VARIANT ===")
                    print(json.dumps(rec,indent=2))
                    sys.exit(0)
            except Exception as e:
                results.append({"kid":kid or "<none>","aud":aud,"uri":uri,"status":None,"ok":False,"err":repr(e)})

print("=== NO SUCCESS; TOP CANDIDATES ===")
# show best few for inspection
def score(e):
    if e["status"] is None: return 0
    if e["status"]==401: return 1
    if e["status"]==403: return 2
    return -e["status"]
for row in sorted(results, key=score, reverse=True)[:8]:
    print(json.dumps(row,indent=2))
sys.exit(10)
