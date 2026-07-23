"""Optional USB numpad support using MicroPython's runtime USB API."""

import time

_keyboard = None
_usb_error = None
_queue = []
_release_due = 0
_key_is_down = False


def init_usb():
    """Create a serial-REPL + keyboard composite USB device from boot.py."""
    global _keyboard, _usb_error
    if _keyboard is not None:
        return True
    try:
        import usb.device
        from usb.device.keyboard import KeyboardInterface

        _keyboard = KeyboardInterface()
        usb.device.get().init(
            _keyboard,
            builtin_driver=True,
            manufacturer_str="DCZia",
            product_str="MK9 Badge",
        )
        return True
    except Exception as error:
        _keyboard = None
        _usb_error = error
        return False


def error():
    return _usb_error


def ready():
    try:
        return _keyboard is not None and _keyboard.is_open()
    except Exception:
        return False


def tap(keycode):
    """Queue a short HID key tap; disconnected hosts simply miss the tap."""
    if ready() and len(_queue) < 12:
        _queue.append(keycode)


def update(now_ms):
    """Advance queued press/release reports without blocking LED animation."""
    global _key_is_down, _release_due
    if _keyboard is None:
        return

    if _key_is_down:
        if time.ticks_diff(now_ms, _release_due) >= 0:
            try:
                if _keyboard.send_keys((), timeout_ms=0):
                    _key_is_down = False
            except Exception:
                _key_is_down = False
        return

    if not _queue:
        return
    if not ready():
        del _queue[:]
        return

    try:
        if _keyboard.send_keys((_queue[0],), timeout_ms=0):
            del _queue[0]
            _key_is_down = True
            _release_due = time.ticks_add(now_ms, 18)
    except Exception:
        del _queue[:]


def release_all():
    global _key_is_down
    del _queue[:]
    if _keyboard is not None:
        try:
            _keyboard.send_keys(())
        except Exception:
            pass
    _key_is_down = False
