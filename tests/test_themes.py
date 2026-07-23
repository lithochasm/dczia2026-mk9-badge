"""Smoke-test every theme and the startup cross-fade."""

import os
import sys
import unittest

REPOSITORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPOSITORY, "software"))

from config import NUM_PIXELS, STARTUP_MS
from themes import render_startup, render_theme


def assert_valid_frame(testcase, frame):
    testcase.assertEqual(NUM_PIXELS, len(frame))
    for color in frame:
        testcase.assertEqual(3, len(color))
        for channel in color:
            testcase.assertIsInstance(channel, int)
            testcase.assertGreaterEqual(channel, 0)
            testcase.assertLessEqual(channel, 255)


class ThemeTests(unittest.TestCase):
    def test_all_nine_themes_are_valid_and_distinct(self):
        signatures = set()
        for theme in range(9):
            frame = [(0, 0, 0)] * NUM_PIXELS
            render_theme(frame, theme, 1.234, 0.22, -0.31, [0.0] * NUM_PIXELS)
            assert_valid_frame(self, frame)
            signatures.add(tuple(frame))
        self.assertEqual(9, len(signatures))

    def test_startup_fades_from_black(self):
        frame = [(1, 1, 1)] * NUM_PIXELS
        render_startup(frame, 0)
        self.assertEqual([(0, 0, 0)] * NUM_PIXELS, frame)
        render_startup(frame, STARTUP_MS // 2)
        assert_valid_frame(self, frame)
        self.assertTrue(any(color != (0, 0, 0) for color in frame))

    def test_startup_ends_on_selected_theme(self):
        startup = [(0, 0, 0)] * NUM_PIXELS
        expected = [(0, 0, 0)] * NUM_PIXELS
        render_startup(startup, STARTUP_MS, theme=6)
        render_theme(expected, 6, STARTUP_MS / 1000.0)
        self.assertEqual(expected, startup)


if __name__ == "__main__":
    unittest.main()
