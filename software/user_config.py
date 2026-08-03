"""Persisted user settings (theme, brightness) saved to flash."""

import json

_PATH = "/user_config.json"


def save(theme, brightness, path=_PATH):
    """Write settings to flash. Never raises -- a failed save shouldn't crash the badge."""
    data = {"theme": theme, "brightness": brightness}
    try:
        with open(path, "w") as handle:
            handle.write(json.dumps(data))
    except OSError:
        pass


def load(path=_PATH):
    """Return the saved settings dict, or None if there's no valid save."""
    try:
        with open(path) as handle:
            text = handle.read()
    except OSError:
        return None
    try:
        return json.loads(text)
    except ValueError:
        return None
