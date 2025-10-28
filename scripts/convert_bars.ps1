param(
  [Parameter(Mandatory=$true)][string]$In,
  [Parameter(Mandatory=$true)][string]$Out
)
$ext = [IO.Path]::GetExtension($In).ToLowerInvariant()
# use python for robust parsing without extra deps here
$code = @"
import sys, os, pandas as pd
inp, outp = sys.argv[1], sys.argv[2]
ext = os.path.splitext(inp)[1].lower()
if ext in ('.parquet','.pq','.pqt'):
    df = pd.read_parquet(inp)
else:
    df = pd.read_csv(inp)
df.columns = [c.strip().lower() for c in df.columns]
# map common variants
ts_cols = [c for c in df.columns if c in ('timestamp','time','datetime','date')]
if not ts_cols: raise SystemExit('No timestamp column')
ts = ts_cols[0]
rename = {}
for k in ('open','high','low','close','volume'):
    if k not in df.columns:
        # try alt names
        for alt in (k, k[0], f'{k[0]}_price', f'{k}_price'):
            if alt in df.columns: rename[alt] = k; break
df = df.rename(columns=rename)
need = {'open','high','low','close','volume'}
if not need.issubset(df.columns): raise SystemExit(f'Missing columns after normalize: {need - set(df.columns)}')
df = df[[ts,'open','high','low','close','volume']].rename(columns={ts:'timestamp'})
df.to_csv(outp, index=False)
print('Wrote', outp)
"@
$py = ".\.venv\Scripts\python.exe"
& $py - <<#PY# $code #PY# $In $Out
