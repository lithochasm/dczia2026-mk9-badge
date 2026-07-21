"""Smoke-test every renderer with lightweight CircuitPython hardware fakes."""

import os
import sys
import time
import types
import unittest


REPOSITORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPOSITORY, "software"))


if "rainbowio" not in sys.modules:
    fake_rainbowio = types.ModuleType("rainbowio")

    def _packed_wheel(hue):
        # The exact palette is not under test; the packed return type is.
        hue = int(hue) & 0xFF
        return (hue << 16) | ((255 - hue) << 8) | ((hue * 3) & 0xFF)

    fake_rainbowio.colorwheel = _packed_wheel
    sys.modules["rainbowio"] = fake_rainbowio


class FakePixels:

    def __init__(self, count):
        self.values = [(0, 0, 0)] * count
        self.show_count = 0

    def __getitem__(self, index):
        return self.values[index]

    def __setitem__(self, index, value):
        self.values[index] = value

    def fill(self, value):
        for index in range(len(self.values)):
            self.values[index] = value

    def show(self):
        self.show_count += 1


class FakeEvents:

    def __init__(self):
        self.pending = []

    def get(self):
        if not self.pending:
            return None
        return self.pending.pop(0)


class FakeSensor:
    acceleration = (0.0, 0.0, 9.81)


POSITIONS = (
    (0.0, 0.0), (0.0, 1.0), (0.0, 2.0),
    (1.0, 0.0), (1.0, 1.0), (1.0, 2.0),
    (2.0, 0.0), (2.0, 1.0), (2.0, 2.0),
    (-0.7, 2.7), (1.0, 3.2), (2.7, 2.7),
    (2.7, -0.7), (1.0, -1.2), (-0.7, -0.7),
)

fake_setup = types.ModuleType("setup")
fake_setup.NUM_PIXELS = 15
fake_setup.NUM_KEY_LEDS = 9
fake_setup.BACKLIGHT_START = 9
fake_setup.LED_POSITIONS = POSITIONS
fake_setup.pixels = FakePixels(15)
fake_setup.keys = types.SimpleNamespace(events=FakeEvents())
fake_setup.sensor = FakeSensor()
fake_setup.ACCEL_AVAILABLE = True
sys.modules["setup"] = fake_setup

fake_supervisor = types.ModuleType("supervisor")
fake_supervisor.runtime = types.SimpleNamespace(usb_connected=False)
sys.modules["supervisor"] = fake_supervisor

import state_badge  # noqa: E402  (hardware modules must be stubbed first)


class BadgeStateTests(unittest.TestCase):

    def setUp(self):
        fake_setup.keys.events.pending = []
        fake_setup.pixels.fill((0, 0, 0))
        self.badge = state_badge.BadgeState()
        self.badge.enter(None)

    def _force_frame(self):
        self.badge.last_frame = 0.0
        self.badge.update(None)

    def assert_valid_frame(self):
        for color in fake_setup.pixels.values:
            self.assertIsInstance(color, tuple)
            self.assertEqual(3, len(color))
            for channel in color:
                self.assertIsInstance(channel, int)
                self.assertGreaterEqual(channel, 0)
                self.assertLessEqual(channel, 255)

    def test_every_background_renders_valid_rgb(self):
        for pattern in range(5):
            self.badge.pattern = pattern
            self._force_frame()
            self.assert_valid_frame()

    def test_press_is_handled_before_next_animation_frame(self):
        event = types.SimpleNamespace(key_number=4, pressed=True, released=False)
        fake_setup.keys.events.pending.append(event)
        self.badge.last_frame = time.monotonic()

        self.badge.update(None)

        self.assertTrue(self.badge.held[4])
        self.assertEqual(1, len(self.badge.ripples))

    def test_event_queue_is_drained_in_one_update(self):
        for key in (0, 4, 8):
            fake_setup.keys.events.pending.append(
                types.SimpleNamespace(key_number=key, pressed=True,
                                      released=False))

        self.badge.update(None)

        self.assertEqual([True, False, False, False, True,
                          False, False, False, True], self.badge.held)
        self.assertEqual(3, len(self.badge.ripples))

    def test_high_pass_shake_cycles_pattern(self):
        self.badge.motion_ready = True
        self.badge.last_shake = -10.0
        fake_setup.sensor.acceleration = (32.0, 0.0, 9.81)
        original = self.badge.pattern

        self.badge._update_motion(time.monotonic())

        self.assertEqual((original + 1) % 5, self.badge.pattern)
        fake_setup.sensor.acceleration = (0.0, 0.0, 9.81)


if __name__ == "__main__":
    unittest.main()
