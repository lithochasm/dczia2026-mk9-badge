"""Persisted user settings (theme, brightness, party BPM) saved to flash."""

import json

_PATH = "/user_config.json"


def save(theme, brightness, party_bpm, path=_PATH):
    """Write settings to flash. Never raises -- a failed save shouldn't crash the badge.

    Always writes a complete snapshot of all three settings (this replaces
    the whole file rather than patching it), so every caller must pass its
    own current value for the fields it isn't changing, or they'll be lost.
    """
    data = {"theme": theme, "brightness": brightness, "party_bpm": party_bpm}
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
