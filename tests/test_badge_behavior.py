"""Behavior checks for long presses, short taps, and liquid light motion."""

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
    def __init__(self):
        self.update_calls = 0

    def update(self, now_ms):
        self.update_calls += 1
        return ()


class FakeHardware:
    def __init__(self):
        self.frame = [(0, 0, 0)] * 15
        self.keys = FakeKeys()
        self.accelerometer = None
        self.brightness = 0.3

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
        self.saved_configs = []
        self.original_save = badge.user_config.save
        badge.user_config.save = lambda theme, brightness: self.saved_configs.append((theme, brightness))
        self.hardware = FakeHardware()
        self.badge = badge.Badge(self.hardware)

    def tearDown(self):
        badge.usb_keyboard.tap = self.original_tap
        badge.user_config.save = self.original_save

    def test_short_press_types_numpad_key(self):
        self.badge._press(2, 1000)
        self.badge._release(2)
        self.assertEqual([97], self.taps)

    def test_full_frame_services_keys_before_and_after_render(self):
        self.badge.update()
        self.assertEqual(2, self.hardware.keys.update_calls)

    def test_long_press_selects_theme_without_typing(self):
        self.badge._press(4, 1000)
        self.badge._handle_keys(1749)
        self.assertEqual(0, self.badge.theme)
        self.badge._handle_keys(1750)
        self.badge._release(4)
        self.assertEqual(4, self.badge.theme)
        self.assertEqual([], self.taps)

    def test_rotation_changes_pool_without_changing_theme(self):
        sensor = FakeSensor()
        self.hardware.accelerometer = sensor
        self.badge._update_motion(2000)
        sensor.value = (30.0, 0.0, 0.0)
        self.badge._update_motion(4000)
        self.assertEqual(0, self.badge.theme)
        self.assertLess(self.badge.pool_x, 0.0)
        self.assertGreater(self.badge.pool_strength, 0.0)

    def test_pool_points_new_direction_on_first_valid_rotation_sample(self):
        sensor = FakeSensor()
        self.hardware.accelerometer = sensor
        self.badge._update_motion(2000)
        sensor.value = (0.0, 9.80665, 0.0)

        self.badge._update_motion(2025)

        self.assertEqual(-1.0, self.badge.pool_y)
        self.assertGreater(self.badge.pool_strength, 0.0)

    def test_pool_smooths_between_existing_and_new_direction(self):
        sensor = FakeSensor()
        self.hardware.accelerometer = sensor
        self.badge.pool_x = 1.0
        self.badge.pool_angle = 0.0
        self.badge.pool_direction_ready = True
        sensor.value = (0.0, -9.80665, 0.0)

        self.badge._update_motion(2000)

        self.assertGreater(self.badge.pool_x, 0.0)
        self.assertLess(self.badge.pool_x, 1.0)
        self.assertGreater(self.badge.pool_y, 0.0)
        self.assertLess(self.badge.pool_y, 1.0)

    def test_pool_overshoots_then_settles_like_liquid(self):
        sensor = FakeSensor()
        self.hardware.accelerometer = sensor
        self.badge.pool_x = 1.0
        self.badge.pool_angle = 0.0
        self.badge.pool_direction_ready = True
        sensor.value = (0.0, -9.80665, 0.0)

        for frame in range(4):
            self.badge._update_motion(2000 + frame * 25)

        self.assertLess(self.badge.pool_x, 0.0)
        self.assertNotEqual(0.0, self.badge.pool_angular_velocity)

    def test_pool_direction_ignores_xy_magnitude_while_upright(self):
        sensor = FakeSensor()
        self.hardware.accelerometer = sensor
        sensor.value = (0.0, 9.80665, 0.0)
        self.badge._update_motion(2000)
        first_strength = self.badge.pool_strength

        sensor.value = (0.0, 2.0, 20.0)
        self.badge._update_motion(2025)

        self.assertAlmostEqual(0.0, self.badge.pool_x)
        self.assertLess(self.badge.pool_y, 0.0)
        self.assertGreater(self.badge.pool_strength, first_strength)

    def test_flat_z_overrides_xy_sensor_noise(self):
        sensor = FakeSensor()
        self.hardware.accelerometer = sensor
        sensor.value = (2.5, 1.0, 9.7)

        self.badge._update_motion(2000)

        self.assertEqual(0.0, self.badge.pool_strength)
        self.assertEqual(0.0, self.badge.pool_angular_velocity)
        self.assertFalse(self.badge.pool_direction_ready)

    def test_z_axis_smoothly_fades_pool_when_laid_flat(self):
        sensor = FakeSensor()
        self.hardware.accelerometer = sensor
        sensor.value = (0.0, 9.80665, 0.0)
        self.badge._update_motion(2000)
        upright_strength = self.badge.pool_strength

        sensor.value = (0.0, 0.0, 9.80665)
        for frame in range(12):
            self.badge._update_motion(2025 + frame * 25)

        self.assertGreater(upright_strength, 0.0)
        self.assertLess(self.badge.pool_strength, 0.05)

    def test_light_pool_brightens_downhill_and_dims_uphill(self):
        self.badge.frame[:] = [(100, 100, 100)] * 15
        self.badge.pool_x = 1.0
        self.badge.pool_y = 0.0
        self.badge.pool_strength = 1.0
        self.badge.animation_seconds = 0.0

        self.badge._apply_light_pool()

        self.assertGreater(sum(self.badge.frame[10]), sum(self.badge.frame[13]))
        self.assertGreater(sum(self.badge.frame[10]), 300)
        self.assertLess(sum(self.badge.frame[13]), 300)

    def test_long_press_theme_change_saves_user_config(self):
        self.badge._press(4, 1000)
        self.badge._handle_keys(1750)
        self.assertEqual([(4, 0.3)], self.saved_configs)

    def test_short_press_does_not_save_user_config(self):
        self.badge._press(2, 1000)
        self.badge._release(2)
        self.assertEqual([], self.saved_configs)


if __name__ == "__main__":
    unittest.main()
