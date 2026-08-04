"""MicroPython entry point for the DCZia MK9 badge."""

from badge import Badge
from config import THEME_NAMES
from hardware import Hardware
from serial_menu import make_default_stream
import usb_keyboard
import user_config

hardware = Hardware()
badge = Badge(hardware, make_default_stream())

saved_config = user_config.load()
if saved_config:
    brightness = saved_config.get("brightness")
    if isinstance(brightness, (int, float)):
        hardware.set_brightness(brightness)
    theme = saved_config.get("theme")
    if isinstance(theme, int) and 0 <= theme < len(THEME_NAMES):
        badge.theme = theme
    party_bpm = saved_config.get("party_bpm")
    if isinstance(party_bpm, (int, float)) and party_bpm > 0:
        badge.party_bpm = party_bpm

print("MK9 MicroPython firmware")
print("accelerometer:", "ready" if hardware.accelerometer else "not detected")
if hardware.accelerometer_error:
    print("accelerometer detail:", hardware.accelerometer_error)
print("USB keyboard:", "configured" if usb_keyboard.error() is None else "unavailable")
print("SAO bus:", "ready" if hardware.sao_i2c else "unavailable")
print("User config:", "loaded" if saved_config else "defaults")
print("Serial console: type 'help' then Enter for commands")

badge.run()
