import yaml

with open("config.yaml", encoding="utf-8") as f:
    data = yaml.safe_load(f)

print("YAML OK ✅")
print(data) # 顯示讀到嘅內容
