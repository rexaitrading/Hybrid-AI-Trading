import os,sys,requests,importlib
api_key=os.environ.get("COINBASE_ADV_KEY_NAME"); api_secret=os.environ.get("COINBASE_ADV_PRIVATE_KEY")
if not api_key or not api_secret: print("Missing env"); sys.exit(1)
jwt_gen = importlib.import_module("coinbase.rest.jwt_generator")
method="GET"; path="/v2/user"
jwt_uri = jwt_gen.format_jwt_uri(method, path)
tok = jwt_gen.build_rest_jwt(jwt_uri, api_key, api_secret)
r = requests.get("https://api.coinbase.com"+path, headers={"Authorization":"Bearer "+tok}, timeout=20)
print("STATUS", r.status_code); print("BODY", r.text[:600])
