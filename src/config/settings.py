import yaml
import os

def load_config():
    base_dir = os.path.dirname(__file__)   # points to src/config/
    path = os.path.join(base_dir, "config.yaml")

    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    # utf-8-sig removes BOM if present
    with open(path, "r", encoding="utf-8-sig") as f:
        config = yaml.safe_load(f)

    return config
