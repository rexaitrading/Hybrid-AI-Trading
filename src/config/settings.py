import os
import yaml
from dotenv import load_dotenv

load_dotenv()

def load_config(path: str = "config/config.yaml") -> dict:
    """Load YAML config and resolve env variables."""
    with open(path, "r") as f:
        config = yaml.safe_load(f)

    # Resolve providers → actual env values
    providers = config.get("providers", {})
    for name, keys in providers.items():
        for k, env_name in keys.items():
            if isinstance(env_name, str) and env_name.isupper():
                providers[name][k] = os.getenv(env_name)
    return config

