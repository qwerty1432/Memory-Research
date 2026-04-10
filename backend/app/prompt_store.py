"""
In-memory prompt config store with file-based persistence.

- get_config(): active config (in-memory override > on-disk file > hardcoded defaults)
- update_config(patch): deep-merge partial update into active config (in-memory only)
- save_config(): write active config to prompt_config.json
- reset_config(): discard in-memory override; revert to on-disk defaults
"""

import copy
import json
import os
import threading
from pathlib import Path
from typing import Any

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "prompt_config.json"

_lock = threading.Lock()
_override: dict | None = None


def _deep_merge(base: dict, patch: dict) -> dict:
    """Recursively merge *patch* into a deep copy of *base*."""
    result = copy.deepcopy(base)
    for key, value in patch.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _load_from_disk() -> dict:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"[prompt_store] warn: could not load {_CONFIG_PATH}: {exc}")
        return {}


def get_config() -> dict:
    with _lock:
        if _override is not None:
            return copy.deepcopy(_override)
    return _load_from_disk()


def update_config(patch: dict) -> dict:
    """Deep-merge *patch* into the active config. Returns the new full config."""
    with _lock:
        global _override
        base = _override if _override is not None else _load_from_disk()
        _override = _deep_merge(base, patch)
        return copy.deepcopy(_override)


def save_config() -> None:
    """Persist the active config to disk."""
    cfg = get_config()
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"[prompt_store] config saved to {_CONFIG_PATH}")


def reset_config() -> dict:
    """Discard in-memory override; revert to on-disk defaults."""
    global _override
    with _lock:
        _override = None
    cfg = _load_from_disk()
    print("[prompt_store] config reset to disk defaults")
    return cfg
