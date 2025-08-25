# utils/config.py
import yaml
import os

def load_config(path="config.yaml"):
    """讀取 config.yaml 設定"""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)