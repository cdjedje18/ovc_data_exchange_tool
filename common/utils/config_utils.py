import json
import os

CONFIG_FILE_PATH = "config.json"


def _ensure_file_exists(path: str):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    if not os.path.exists(path):
        with open(path, "w", encoding="utf8") as f:
            json.dump({}, f, ensure_ascii=False, indent=4)


def load_config(path: str = CONFIG_FILE_PATH) -> dict:
    """Load configuration from disk; return empty dict if no file exists."""
    if not os.path.exists(path):
        return {}

    with open(path, "r", encoding="utf8") as f:
        try:
            return json.load(f) or {}
        except json.JSONDecodeError:
            # Corrupt content, fallback to empty
            return {}


def save_config(data: dict, path: str = CONFIG_FILE_PATH) -> dict:
    """Save configuration to disk (creates file if missing)."""
    if not isinstance(data, dict):
        raise TypeError("data must be a dictionary")

    _ensure_file_exists(path)
    with open(path, "w", encoding="utf8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    return data


def _deep_update(orig: dict, updates: dict) -> dict:
    """Recursively update nested dicts."""
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(orig.get(key), dict):
            orig[key] = _deep_update(orig.get(key, {}), value)
        else:
            orig[key] = value
    return orig


def update_config(updates: dict, path: str = CONFIG_FILE_PATH) -> dict:
    """Update existing config with provided values, creating file as needed."""
    if not isinstance(updates, dict):
        raise TypeError("updates must be a dictionary")

    config = load_config(path)
    if not isinstance(config, dict):
        config = {}

    merged = _deep_update(config, updates)
    save_config(merged, path)
    return merged


def get_config(path: str = CONFIG_FILE_PATH) -> dict:
    """Alias for load_config for compatibility and readability."""
    return load_config(path)
