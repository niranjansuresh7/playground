"""Loading and checking config.json, plus the app's remembered settings."""

import ipaddress
import json
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = PROJECT_DIR / "config.json"
APP_STATE = PROJECT_DIR / "app_state.json"


def load_config(path=DEFAULT_CONFIG):
    """Read config.json, trimming stray spaces that sneak in when pasting values."""
    path = Path(path)
    if not path.exists():
        return {}
    config = json.loads(path.read_text())
    return {k: v.strip() if isinstance(v, str) else v for k, v in config.items()}


def bulb_config_problems(config):
    """Return a list of human-readable problems; empty means the bulb details look fine."""
    problems = []
    if not config.get("device_id") or config["device_id"].startswith("PASTE_"):
        problems.append("device_id is missing")
    if not config.get("local_key") or config["local_key"].startswith("PASTE_"):
        problems.append("local_key is missing")
    elif len(config["local_key"]) != 16:
        problems.append(f"local_key should be 16 characters but has {len(config['local_key'])}")
    try:
        ipaddress.IPv4Address(config.get("ip", ""))
    except ValueError:
        problems.append(f"ip '{config.get('ip')}' is not a valid address (expected like 192.168.1.12)")
    return problems


def load_state(path=APP_STATE):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return {}


def save_state(state, path=APP_STATE):
    try:
        Path(path).write_text(json.dumps(state, indent=2))
    except OSError:
        pass
