import yaml

p = "config/config.yaml"
with open(p, "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f) or {}
cfg["sweep_hours_back"] = int(cfg.get("sweep_hours_back", 24)) or 24
cfg["sweep_limit"] = int(cfg.get("sweep_limit", 100)) or 100
# bump to ensure enough volume for calibration
if cfg["sweep_hours_back"] < 48:
    cfg["sweep_hours_back"] = 48
if cfg["sweep_limit"] < 200:
    cfg["sweep_limit"] = 200
with open(p, "w", encoding="utf-8") as f:
    yaml.safe_dump(cfg, f, sort_keys=False)
print("sweep_hours_back:", cfg["sweep_hours_back"], "sweep_limit:", cfg["sweep_limit"])
