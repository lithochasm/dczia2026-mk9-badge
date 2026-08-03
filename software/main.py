"""MicroPython entry point for the DCZia MK9 badge."""

from badge import Badge
from hardware import Hardware
from serial_menu import make_default_stream
import usb_keyboard

hardware = Hardware()
badge = Badge(hardware, make_default_stream())

print("MK9 MicroPython firmware")
print("accelerometer:", "ready" if hardware.accelerometer else "not detected")
if hardware.accelerometer_error:
    print("accelerometer detail:", hardware.accelerometer_error)
print("USB keyboard:", "configured" if usb_keyboard.error() is None else "unavailable")
print("SAO bus:", "ready" if hardware.sao_i2c else "unavailable")
print("Serial console: type 'help' then Enter for commands")

badge.run()
