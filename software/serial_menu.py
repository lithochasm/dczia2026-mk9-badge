"""Typed command console over the badge's existing USB-CDC serial stream.

The console runs alongside the animation/key-scan loop rather than at the
MicroPython REPL, so it needs non-blocking, allocation-light reads. Ctrl-C
still drops to the real REPL and kills the running script; that interrupt is
intercepted by MicroPython below the stream this module reads from, so it
needs no special handling here.
"""

import time

from config import THEME_NAMES
import usb_keyboard

_MAX_CHARS_PER_UPDATE = 32
_MAX_LINE_LENGTH = 64
_BACKSPACE = "\x08"
_DEL = "\x7f"

_HELP_TEXT = (
    "Commands:\r\n"
    "  help                 show this listing\r\n"
    "  status               theme, brightness, sensors, USB-HID, uptime\r\n"
    "  theme [n|name]       show themes, or set by number (1-9) or name\r\n"
    "  brightness [0-100]   show or set LED brightness percent\r\n"
    "  accel                one-shot accelerometer reading\r\n"
    "  reset                reboot the badge\r\n"
    "  bootloader           enter BOOTSEL/UF2 mode for reflashing\r\n"
)


class _SerialStream:
    """Non-blocking single-character access to sys.stdin/stdout."""

    def __init__(self):
        import select
        import sys

        self._sys = sys
        self._poll = select.poll()
        self._poll.register(sys.stdin, select.POLLIN)

    def read_ready(self):
        return bool(self._poll.poll(0))

    def read_char(self):
        return self._sys.stdin.read(1)

    def write(self, text):
        self._sys.stdout.write(text)


def make_default_stream():
    """Build the production serial transport, or None if unavailable."""
    try:
        return _SerialStream()
    except Exception:
        return None


def _match_theme(text):
    if text.isdigit():
        number = int(text)
        if 1 <= number <= len(THEME_NAMES):
            return number - 1
        return None
    lowered = text.lower()
    for index, name in enumerate(THEME_NAMES):
        if name.lower() == lowered:
            return index
    return None


def _cmd_help(menu, args, now_ms):
    menu._write(_HELP_TEXT)


def _cmd_status(menu, args, now_ms):
    badge = menu.badge
    hardware = menu.hardware
    menu._write_line("theme:", badge.theme + 1, badge.theme_name)
    menu._write_line("brightness:", int(hardware.brightness * 100 + 0.5), "%")
    if hardware.accelerometer is not None:
        menu._write_line("accelerometer: ready")
    elif hardware.accelerometer_error is not None:
        menu._write_line("accelerometer: error", hardware.accelerometer_error)
    else:
        menu._write_line("accelerometer: not available")
    menu._write_line("SAO bus:", "ready" if hardware.sao_i2c is not None else "unavailable")
    menu._write_line("USB keyboard:", "ready" if usb_keyboard.ready() else "unavailable")
    uptime_ms = time.ticks_diff(now_ms, badge.start_ms)
    menu._write_line("uptime:", uptime_ms // 1000, "s")


def _cmd_theme(menu, args, now_ms):
    if not args:
        menu._write_line("current theme:", menu.badge.theme + 1, menu.badge.theme_name)
        for index, name in enumerate(THEME_NAMES):
            menu._write_line(" ", index + 1, name)
        return
    text = " ".join(args)
    index = _match_theme(text)
    if index is None:
        menu._write_line("unknown theme:", text)
        return
    menu.badge._select_theme(index, now_ms, index)
    menu._write_line("theme ->", THEME_NAMES[index])


def _cmd_brightness(menu, args, now_ms):
    if not args:
        menu._write_line("brightness:", int(menu.hardware.brightness * 100 + 0.5), "%")
        return
    try:
        percent = float(args[0])
    except ValueError:
        menu._write_line("usage: brightness <0-100>")
        return
    percent = max(0.0, min(100.0, percent))
    menu.hardware.set_brightness(percent / 100.0)
    menu._write_line("brightness ->", int(percent + 0.5), "%")


def _cmd_accel(menu, args, now_ms):
    sensor = menu.hardware.accelerometer
    if sensor is None:
        menu._write_line("accelerometer not available")
        return
    try:
        x, y, z = sensor.acceleration()
    except Exception as error:
        menu._write_line("accelerometer read failed:", error)
        return
    menu._write_line("accel m/s2: x={:.2f} y={:.2f} z={:.2f}".format(x, y, z))


def _machine_reset():
    import machine

    machine.reset()


def _machine_bootloader():
    import machine

    machine.bootloader()


def _cmd_reset(menu, args, now_ms):
    menu._write_line("resetting...")
    _machine_reset()


def _cmd_bootloader(menu, args, now_ms):
    menu._write_line("entering bootloader (UF2) mode...")
    _machine_bootloader()


_COMMANDS = {
    "help": _cmd_help,
    "status": _cmd_status,
    "theme": _cmd_theme,
    "brightness": _cmd_brightness,
    "accel": _cmd_accel,
    "reset": _cmd_reset,
    "bootloader": _cmd_bootloader,
}


class SerialMenu:
    """Typed command console; a no-op when constructed without a stream."""

    def __init__(self, badge, hardware, stream=None):
        self.badge = badge
        self.hardware = hardware
        self._stream = stream
        self._line = ""
        self._greeted = False
        self._last_was_cr = False

    def update(self, now_ms):
        stream = self._stream
        if stream is None:
            return
        for _ in range(_MAX_CHARS_PER_UPDATE):
            if not stream.read_ready():
                break
            self._handle_char(stream.read_char(), now_ms)

    def _handle_char(self, char, now_ms):
        if not self._greeted:
            self._greeted = True
            self._write(_HELP_TEXT)
            self._write_prompt()

        # A terminal's Enter key often arrives as a "\r\n" pair; treat the
        # second character as part of the same keystroke instead of firing
        # dispatch twice (and don't require the pairing for bare "\n" or "\r").
        if char == "\n" and self._last_was_cr:
            self._last_was_cr = False
            return
        self._last_was_cr = char == "\r"

        if char in ("\r", "\n"):
            self._write("\r\n")
            self._dispatch(self._line, now_ms)
            self._line = ""
            self._write_prompt()
        elif char in (_BACKSPACE, _DEL):
            if self._line:
                self._line = self._line[:-1]
                self._write("\b \b")
        elif " " <= char <= "~":
            if len(self._line) < _MAX_LINE_LENGTH:
                self._line += char
                self._write(char)

    def _dispatch(self, line, now_ms):
        line = line.strip()
        if not line:
            return
        parts = line.split()
        handler = _COMMANDS.get(parts[0].lower())
        if handler is None:
            self._write_line("unknown command:", parts[0], "(try 'help')")
            return
        try:
            handler(self, parts[1:], now_ms)
        except Exception as error:
            self._write_line("command failed:", error)

    def _write(self, text):
        self._stream.write(text)

    def _write_line(self, *parts):
        self._write(" ".join(str(part) for part in parts))
        self._write("\r\n")

    def _write_prompt(self):
        self._write("mk9> ")
