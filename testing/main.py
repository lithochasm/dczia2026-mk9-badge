"""MicroPython visual hardware test for LEDs, keys, and accelerometer."""

import time

from color_tools import wheel
from hardware import Hardware

hardware = Hardware()
frame = [(0, 0, 0)] * 15
held = [False] * 9
started = time.ticks_ms()
last_report = started

print("MK9 hardware test")
print("Press each key: its LED should turn white.")
print("Tilt: the matching edge should turn white.")
print("accelerometer:", "ready" if hardware.accelerometer else "NOT DETECTED")
if hardware.accelerometer_error:
    print("detail:", hardware.accelerometer_error)

try:
    while True:
        now = time.ticks_ms()
        elapsed = time.ticks_diff(now, started)

        for event in hardware.keys.update(now):
            held[event.key] = event.pressed
            print("key", event.key + 1, "down" if event.pressed else "up")

        # Moving RGB bands prove every color channel and every LED.
        for led in range(15):
            frame[led] = wheel(elapsed * 0.055 + led * 21, 0.72)
        for key in range(9):
            if held[key]:
                frame[key] = (255, 255, 255)

        if hardware.accelerometer:
            try:
                ax, ay, az = hardware.accelerometer.acceleration()
                if abs(ax) > 1.2 or abs(ay) > 1.2:
                    if abs(ax) >= abs(ay):
                        frame[10 if ax > 0 else 13] = (255, 255, 255)
                    else:
                        targets = (11, 12) if ay > 0 else (9, 14)
                        for led in targets:
                            frame[led] = (255, 255, 255)
                if time.ticks_diff(now, last_report) >= 500:
                    print("accel m/s2: x={:.2f} y={:.2f} z={:.2f}".format(ax, ay, az))
                    last_report = now
            except Exception as error:
                print("accelerometer read failed:", error)
        else:
            # Red edge blink makes a missing sensor obvious without a console.
            if (elapsed // 350) & 1:
                for led in range(9, 15):
                    frame[led] = (255, 0, 0)

        hardware.show(frame)
        time.sleep_ms(10)
finally:
    hardware.off()
