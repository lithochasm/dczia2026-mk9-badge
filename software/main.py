"""MicroPython entry point for the DCZia MK9 badge."""

from badge import Badge
from hardware import Hardware
import usb_keyboard

hardware = Hardware()
badge = Badge(hardware)

print("MK9 MicroPython firmware")
print("accelerometer:", "ready" if hardware.accelerometer else "not detected")
if hardware.accelerometer_error:
    print("accelerometer detail:", hardware.accelerometer_error)
print("USB keyboard:", "configured" if usb_keyboard.error() is None else "unavailable")
print("SAO bus:", "ready" if hardware.sao_i2c else "unavailable")

badge.run()
