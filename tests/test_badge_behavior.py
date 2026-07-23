"""Behavior checks for long presses, short taps, and shake selection."""

import os
import sys
import time
import unittest

REPOSITORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPOSITORY, "software"))

# CPython equivalents for MicroPython's wrapping tick helpers.
time.ticks_ms = lambda: 1000
time.ticks_add = lambda value, delta: value + delta
time.ticks_diff = lambda first, second: first - second

import badge


class FakeKeys:
    def update(self, now_ms):
        return ()


class FakeHardware:
    def __init__(self):
        self.frame = [(0, 0, 0)] * 15
        self.keys = FakeKeys()
        self.accelerometer = None

    def show(self, frame):
        pass

    def off(self):
        pass


class FakeSensor:
    def __init__(self):
        self.value = (0.0, 0.0, 9.80665)

    def acceleration(self):
        return self.value


class BadgeBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.taps = []
        self.original_tap = badge.usb_keyboard.tap
        badge.usb_keyboard.tap = self.taps.append
        self.hardware = FakeHardware()
        self.badge = badge.Badge(self.hardware)

    def tearDown(self):
        badge.usb_keyboard.tap = self.original_tap

    def test_short_press_types_numpad_key(self):
        self.badge._press(2, 1000)
        self.badge._release(2)
        self.assertEqual([97], self.taps)

    def test_long_press_selects_theme_without_typing(self):
        self.badge._press(4, 1000)
        self.badge._handle_keys(1749)
        self.assertEqual(0, self.badge.theme)
        self.badge._handle_keys(1750)
        self.badge._release(4)
        self.assertEqual(4, self.badge.theme)
        self.assertEqual([], self.taps)

    def test_shake_advances_theme(self):
        sensor = FakeSensor()
        self.hardware.accelerometer = sensor
        self.badge._update_motion(2000)
        sensor.value = (30.0, 0.0, 9.80665)
        self.badge._update_motion(4000)
        self.assertEqual(1, self.badge.theme)


if __name__ == "__main__":
    unittest.main()
