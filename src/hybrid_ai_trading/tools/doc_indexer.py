import os, json, pathlib
from typing import List, Dict

def index_folder(folder: str, exts={".txt",".md",".yaml",".yml",".json"}):
    p = pathlib.Path(folder)
    out = []
    for f in p.rglob("*"):
        if f.suffix.lower() in exts and f.is_file():
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
                out.append({"path": str(f), "size": f.stat().st_size, "preview": text[:400]})
            except Exception:
                pass
    return out

if __name__ == "__main__":
    import sys
    folder = sys.argv[1] if len(sys.argv)>1 else "."
    print(json.dumps(index_folder(folder), indent=2))
