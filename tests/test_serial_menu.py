"""Typed serial console: dispatch, editing, and command behavior."""

import os
import sys
import time
import unittest

REPOSITORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPOSITORY, "software"))

# CPython equivalents for MicroPython's wrapping tick helpers.
time.ticks_diff = lambda first, second: first - second

import serial_menu
from config import THEME_NAMES
from serial_menu import SerialMenu


class FakeStream:
    def __init__(self):
        self._pending = []
        self.written = []

    def feed(self, text):
        self._pending.extend(text)

    def read_ready(self):
        return bool(self._pending)

    def read_char(self):
        return self._pending.pop(0)

    def write(self, text):
        self.written.append(text)

    def output(self):
        return "".join(self.written)


class FakeBadge:
    def __init__(self):
        self.theme = 0
        self.start_ms = 0
        self.select_calls = []

    @property
    def theme_name(self):
        return THEME_NAMES[self.theme]

    def _select_theme(self, theme, now_ms, origin):
        self.theme = theme % len(THEME_NAMES)
        self.select_calls.append((theme, now_ms, origin))


class FakeHardware:
    def __init__(self):
        self.brightness = 0.30
        self.accelerometer = None
        self.accelerometer_error = None
        self.sao_i2c = None
        self.set_brightness_calls = []

    def set_brightness(self, level):
        self.set_brightness_calls.append(level)
        self.brightness = level


class FakeSensor:
    def __init__(self, value=(0.0, 0.0, 9.80665)):
        self.value = value

    def acceleration(self):
        return self.value


class RaisingSensor:
    def acceleration(self):
        raise OSError("bus error")


def make_menu():
    stream = FakeStream()
    badge = FakeBadge()
    hardware = FakeHardware()
    menu = SerialMenu(badge, hardware, stream)
    return menu, stream, badge, hardware


class SerialMenuTests(unittest.TestCase):
    def setUp(self):
        self.original_ready = serial_menu.usb_keyboard.ready
        serial_menu.usb_keyboard.ready = lambda: True
        self.saved_configs = []
        self.original_save = serial_menu.user_config.save
        serial_menu.user_config.save = lambda theme, brightness: self.saved_configs.append((theme, brightness))

    def tearDown(self):
        serial_menu.usb_keyboard.ready = self.original_ready
        serial_menu.user_config.save = self.original_save

    def test_disabled_when_stream_is_none(self):
        badge = FakeBadge()
        hardware = FakeHardware()
        menu = SerialMenu(badge, hardware, None)
        menu.update(1000)
        menu.update(2000)

    def test_idle_update_does_nothing_when_nothing_pending(self):
        menu, stream, _, _ = make_menu()
        menu.update(1000)
        self.assertEqual([], stream.written)

    def test_first_character_shows_help_banner_once(self):
        menu, stream, _, _ = make_menu()
        stream.feed("status\n")
        menu.update(1000)
        self.assertEqual(1, stream.output().count("Commands:"))
        stream.feed("status\n")
        menu.update(1000)
        self.assertEqual(1, stream.output().count("Commands:"))

    def test_echoes_typed_characters(self):
        menu, stream, _, _ = make_menu()
        stream.feed("st")
        menu.update(1000)
        self.assertIn("st", stream.output())

    def test_backspace_edits_line_before_dispatch(self):
        menu, stream, _, hardware = make_menu()
        stream.feed("statx" + serial_menu._DEL + "us\n")
        menu.update(1000)
        self.assertIn("brightness:", stream.output())

    def test_crlf_enter_dispatches_only_once(self):
        menu, stream, badge, _ = make_menu()
        stream.feed("theme 3\r\n")
        menu.update(1000)
        self.assertEqual([(2, 1000, 2)], badge.select_calls)

    def test_bare_cr_alone_still_dispatches(self):
        menu, stream, badge, _ = make_menu()
        stream.feed("theme 3\r")
        menu.update(1000)
        self.assertEqual([(2, 1000, 2)], badge.select_calls)

    def test_unknown_command_reports_error(self):
        menu, stream, _, _ = make_menu()
        stream.feed("bogus\n")
        menu.update(1000)
        self.assertIn("unknown command:", stream.output())
        self.assertIn("bogus", stream.output())

    def test_help_lists_all_seven_commands(self):
        menu, stream, _, _ = make_menu()
        stream.feed("help\n")
        menu.update(1000)
        for name in ("help", "status", "theme", "brightness", "accel", "reset", "bootloader"):
            self.assertIn(name, stream.output())

    def test_status_reports_theme_brightness_and_sensors(self):
        menu, stream, badge, hardware = make_menu()
        badge.theme = 2
        hardware.brightness = 0.5
        hardware.accelerometer = FakeSensor()
        hardware.sao_i2c = object()
        stream.feed("status\n")
        menu.update(1000)
        output = stream.output()
        self.assertIn("Deep Ocean", output)
        self.assertIn("50", output)
        self.assertIn("ready", output)

    def test_theme_set_by_1_based_number(self):
        menu, stream, badge, _ = make_menu()
        stream.feed("theme 3\n")
        menu.update(1000)
        self.assertEqual(2, badge.theme)
        self.assertEqual([(2, 1000, 2)], badge.select_calls)

    def test_theme_set_by_name_case_insensitive(self):
        menu, stream, badge, _ = make_menu()
        stream.feed("theme deep ocean\n")
        menu.update(1000)
        self.assertEqual(THEME_NAMES.index("Deep Ocean"), badge.theme)

    def test_theme_number_out_of_range_rejected(self):
        menu, stream, badge, _ = make_menu()
        stream.feed("theme 99\n")
        menu.update(1000)
        self.assertEqual(0, badge.theme)
        self.assertIn("unknown theme:", stream.output())

    def test_theme_unknown_name_rejected(self):
        menu, stream, badge, _ = make_menu()
        stream.feed("theme not-a-theme\n")
        menu.update(1000)
        self.assertEqual(0, badge.theme)
        self.assertIn("unknown theme:", stream.output())

    def test_theme_no_args_lists_all_themes(self):
        menu, stream, _, _ = make_menu()
        stream.feed("theme\n")
        menu.update(1000)
        output = stream.output()
        for name in THEME_NAMES:
            self.assertIn(name, output)

    def test_brightness_get_reports_current_percent(self):
        menu, stream, _, hardware = make_menu()
        hardware.brightness = 0.3
        stream.feed("brightness\n")
        menu.update(1000)
        self.assertIn("30", stream.output())

    def test_brightness_set_clamps_high_and_low(self):
        menu, stream, _, hardware = make_menu()
        stream.feed("brightness 500\n")
        menu.update(1000)
        self.assertEqual(1.0, hardware.set_brightness_calls[-1])

        stream.feed("brightness -20\n")
        menu.update(1000)
        self.assertEqual(0.0, hardware.set_brightness_calls[-1])

    def test_brightness_set_saves_user_config(self):
        menu, stream, badge, _ = make_menu()
        badge.theme = 3
        stream.feed("brightness 60\n")
        menu.update(1000)
        self.assertEqual([(3, 0.6)], self.saved_configs)

    def test_brightness_get_does_not_save_user_config(self):
        menu, stream, _, _ = make_menu()
        stream.feed("brightness\n")
        menu.update(1000)
        self.assertEqual([], self.saved_configs)

    def test_brightness_rejects_non_numeric_argument(self):
        menu, stream, _, hardware = make_menu()
        stream.feed("brightness abc\n")
        menu.update(1000)
        self.assertEqual([], hardware.set_brightness_calls)
        self.assertIn("usage:", stream.output())

    def test_accel_reports_reading_when_present(self):
        menu, stream, _, hardware = make_menu()
        hardware.accelerometer = FakeSensor((1.0, 2.0, 3.0))
        stream.feed("accel\n")
        menu.update(1000)
        output = stream.output()
        self.assertIn("1.00", output)
        self.assertIn("2.00", output)
        self.assertIn("3.00", output)

    def test_accel_reports_unavailable_when_missing(self):
        menu, stream, _, hardware = make_menu()
        hardware.accelerometer = None
        stream.feed("accel\n")
        menu.update(1000)
        self.assertIn("not available", stream.output())

    def test_accel_handles_sensor_exception_without_crashing(self):
        menu, stream, _, hardware = make_menu()
        hardware.accelerometer = RaisingSensor()
        stream.feed("accel\n")
        menu.update(1000)
        self.assertIn("failed", stream.output())

    def test_reset_invokes_machine_reset_hook(self):
        calls = []
        original = serial_menu._machine_reset
        serial_menu._machine_reset = lambda: calls.append(True)
        try:
            menu, stream, _, _ = make_menu()
            stream.feed("reset\n")
            menu.update(1000)
        finally:
            serial_menu._machine_reset = original
        self.assertEqual([True], calls)

    def test_bootloader_invokes_machine_bootloader_hook(self):
        calls = []
        original = serial_menu._machine_bootloader
        serial_menu._machine_bootloader = lambda: calls.append(True)
        try:
            menu, stream, _, _ = make_menu()
            stream.feed("bootloader\n")
            menu.update(1000)
        finally:
            serial_menu._machine_bootloader = original
        self.assertEqual([True], calls)

    def test_garbage_binary_input_does_not_crash(self):
        menu, stream, _, _ = make_menu()
        stream.feed("\x00\x01\x02\x1b[A\n")
        menu.update(1000)
        stream.feed("help\n")
        menu.update(1000)
        self.assertIn("Commands:", stream.output())

    def test_line_length_is_bounded(self):
        menu, stream, badge, _ = make_menu()
        stream.feed("a" * 200 + "\n")
        for _ in range(10):
            menu.update(1000)
        self.assertEqual("", menu._line)

    def test_max_chars_per_update_bounds_a_single_call(self):
        menu, stream, _, _ = make_menu()
        stream.feed("a" * (serial_menu._MAX_CHARS_PER_UPDATE + 10))
        menu.update(1000)
        self.assertTrue(stream._pending)
        menu.update(1000)
        self.assertFalse(stream._pending)


if __name__ == "__main__":
    unittest.main()
