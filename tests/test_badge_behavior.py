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


class FakeKeyEvent:
    def __init__(self, key, pressed):
        self.key = key
        self.pressed = pressed


class FakeKeys:
    def __init__(self):
        self.update_calls = 0
        self.pending_events = []

    def update(self, now_ms):
        self.update_calls += 1
        events = self.pending_events
        self.pending_events = []
        return events


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
        badge.user_config.save = lambda theme, brightness, party_bpm: self.saved_configs.append(
            (theme, brightness, party_bpm)
        )
        self.hardware = FakeHardware()
        self.badge = badge.Badge(self.hardware)

    def tearDown(self):
        badge.usb_keyboard.tap = self.original_tap
        badge.user_config.save = self.original_save

    def test_party_bpm_defaults_to_config_value(self):
        self.assertEqual(badge.PARTY_BPM, self.badge.party_bpm)

    def test_short_press_types_numpad_key(self):
        self.badge._press(2, 1000)
        self.badge._release(2)
        self.assertEqual([97], self.taps)

    def test_hid_tap_suppressed_while_party_mode_active(self):
        self.badge.theme = badge.PARTY_MODE_THEME
        self.badge._press(2, 1000)
        self.badge._release(2)
        self.assertEqual([], self.taps)

    def test_hid_tap_resumes_after_leaving_party_mode(self):
        self.badge.theme = badge.PARTY_MODE_THEME
        self.badge._press(2, 1000)
        self.badge._release(2)
        self.badge.theme = badge.DEFAULT_THEME
        self.badge._press(2, 1000)
        self.badge._release(2)
        self.assertEqual([97], self.taps)

    def test_long_press_theme_select_still_works_during_party_mode(self):
        self.badge.theme = badge.PARTY_MODE_THEME
        self.badge._press(4, 1000)
        self.badge._handle_keys(1750)
        self.badge._release(4)
        self.assertEqual(4, self.badge.theme)
        self.assertEqual([], self.taps)

    def test_key7_short_press_decreases_party_bpm(self):
        self.badge.theme = badge.PARTY_MODE_THEME
        before = self.badge.party_bpm
        self.badge._press(badge.PARTY_BPM_DOWN_KEY, 1000)
        self.badge._release(badge.PARTY_BPM_DOWN_KEY)
        self.assertEqual(before - badge.PARTY_BPM_STEP, self.badge.party_bpm)

    def test_key8_short_press_increases_party_bpm(self):
        self.badge.theme = badge.PARTY_MODE_THEME
        before = self.badge.party_bpm
        self.badge._press(badge.PARTY_BPM_UP_KEY, 1000)
        self.badge._release(badge.PARTY_BPM_UP_KEY)
        self.assertEqual(before + badge.PARTY_BPM_STEP, self.badge.party_bpm)

    def test_bpm_keys_send_no_hid_tap_during_party_mode(self):
        self.badge.theme = badge.PARTY_MODE_THEME
        self.badge._press(badge.PARTY_BPM_DOWN_KEY, 1000)
        self.badge._release(badge.PARTY_BPM_DOWN_KEY)
        self.badge._press(badge.PARTY_BPM_UP_KEY, 1000)
        self.badge._release(badge.PARTY_BPM_UP_KEY)
        self.assertEqual([], self.taps)

    def test_bpm_keys_behave_as_normal_numpad_keys_outside_party_mode(self):
        before = self.badge.party_bpm
        self.badge._press(badge.PARTY_BPM_DOWN_KEY, 1000)
        self.badge._release(badge.PARTY_BPM_DOWN_KEY)
        self.assertEqual(before, self.badge.party_bpm)
        self.assertEqual([89], self.taps)

    def test_party_bpm_clamps_at_upper_bound(self):
        self.badge.theme = badge.PARTY_MODE_THEME
        self.badge.party_bpm = badge.PARTY_BPM_MAX - 1
        self.badge._press(badge.PARTY_BPM_UP_KEY, 1000)
        self.badge._release(badge.PARTY_BPM_UP_KEY)
        self.assertEqual(badge.PARTY_BPM_MAX, self.badge.party_bpm)

    def test_party_bpm_clamps_at_lower_bound(self):
        self.badge.theme = badge.PARTY_MODE_THEME
        self.badge.party_bpm = badge.PARTY_BPM_MIN + 1
        self.badge._press(badge.PARTY_BPM_DOWN_KEY, 1000)
        self.badge._release(badge.PARTY_BPM_DOWN_KEY)
        self.assertEqual(badge.PARTY_BPM_MIN, self.badge.party_bpm)

    def test_bpm_key_press_saves_user_config(self):
        self.badge.theme = badge.PARTY_MODE_THEME
        self.badge._press(badge.PARTY_BPM_UP_KEY, 1000)
        self.badge._release(badge.PARTY_BPM_UP_KEY)
        self.assertEqual(
            [(badge.PARTY_MODE_THEME, self.hardware.brightness, self.badge.party_bpm)],
            self.saved_configs,
        )

    def test_long_press_on_bpm_key_still_selects_theme_during_party_mode(self):
        self.badge.theme = badge.PARTY_MODE_THEME
        before = self.badge.party_bpm
        self.badge._press(badge.PARTY_BPM_DOWN_KEY, 1000)
        self.badge._handle_keys(1750)
        self.badge._release(badge.PARTY_BPM_DOWN_KEY)
        self.assertEqual(badge.PARTY_BPM_DOWN_KEY, self.badge.theme)
        self.assertEqual(before, self.badge.party_bpm)
        self.assertEqual([], self.taps)

    def test_full_frame_services_keys_before_and_after_render(self):
        self.badge.update()
        self.assertEqual(2, self.hardware.keys.update_calls)

    def test_long_press_selects_theme_without_typing(self):
        self.badge._press(4, 1000)
        self.badge._handle_keys(1749)
        self.assertEqual(badge.DEFAULT_THEME, self.badge.theme)
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
        self.assertEqual(badge.DEFAULT_THEME, self.badge.theme)
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
        self.assertEqual([(4, 0.3, self.badge.party_bpm)], self.saved_configs)

    def test_short_press_does_not_save_user_config(self):
        self.badge._press(2, 1000)
        self.badge._release(2)
        self.assertEqual([], self.saved_configs)

    def test_key_events_ignored_while_game_active(self):
        self.badge.serial_menu._active_game = object()
        self.hardware.keys.pending_events = [FakeKeyEvent(2, True)]
        self.badge._handle_keys(1000)
        self.assertFalse(self.badge.held[2])

    def test_key_release_suppresses_hid_tap_while_game_active(self):
        self.badge.serial_menu._active_game = object()
        self.hardware.keys.pending_events = [FakeKeyEvent(2, True)]
        self.badge._handle_keys(1000)
        self.hardware.keys.pending_events = [FakeKeyEvent(2, False)]
        self.badge._handle_keys(1000)
        self.assertEqual([], self.taps)

    def test_long_press_theme_select_suppressed_while_game_active(self):
        self.badge.serial_menu._active_game = object()
        self.hardware.keys.pending_events = [FakeKeyEvent(4, True)]
        self.badge._handle_keys(1000)
        self.badge._handle_keys(1750)
        self.assertEqual(badge.DEFAULT_THEME, self.badge.theme)

    def test_keys_still_drained_every_call_while_game_active(self):
        self.badge.serial_menu._active_game = object()
        self.badge._handle_keys(1000)
        self.assertEqual(1, self.hardware.keys.update_calls)

    def test_update_preserves_frame_and_skips_render_while_game_active(self):
        self.badge.serial_menu._active_game = object()
        sentinel = [(9, 9, 9)] * 15
        self.badge.frame[:] = sentinel
        self.badge.update()
        self.assertEqual(sentinel, self.badge.frame)


if __name__ == "__main__":
    unittest.main()
