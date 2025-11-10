thonfrom __future__ import annotations

import os
from pathlib import Path
from typing import Dict

import yaml

def load_settings(path: Path) -> Dict:
    """
    Load YAML settings file with safe defaults.
    """
    if not path.exists():
        raise FileNotFoundError(f"Settings file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Settings at {path} must contain a YAML mapping at the root.")
    return data

def load_credentials(path: Path) -> Dict:
    """
    Minimal .env-style loader. Lines of form KEY=VALUE are parsed.
    Ignores comments and blank lines.
    """
    creds: Dict[str, str] = {}
    if not path.exists():
        return creds

    with path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            creds[key] = value

    # Optionally mirror into environment for downstream libraries
    for k, v in creds.items():
        os.environ.setdefault(k, v)

    return creds