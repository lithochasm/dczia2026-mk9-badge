"""Smoke-test every theme and the startup cross-fade."""

import os
import sys
import unittest

REPOSITORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPOSITORY, "software"))

from config import NUM_PIXELS, PARTY_BPM, PARTY_MODE_THEME, STARTUP_MS, THEME_NAMES
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
    def test_all_ten_themes_are_valid_and_distinct(self):
        signatures = set()
        for theme in range(10):
            frame = [(0, 0, 0)] * NUM_PIXELS
            render_theme(frame, theme, 1.234, 0.22, -0.31, [0.0] * NUM_PIXELS)
            assert_valid_frame(self, frame)
            signatures.add(tuple(frame))
        self.assertEqual(10, len(signatures))

    def test_party_mode_lives_at_theme_index_zero(self):
        # So key 1's long-press selects it -- this is the whole point of
        # having PARTY_MODE_THEME be a derived index rather than a constant.
        self.assertEqual(0, PARTY_MODE_THEME)
        self.assertEqual("Party Mode", THEME_NAMES[0])

    def test_prism_renders_at_its_own_theme_names_index(self):
        # Prism moved to make room for Party Mode at index 0. Confirm the
        # rendering logic actually followed the name, not just the label:
        # Prism's brightness floor keeps every pixel above pure black, which
        # only Party Mode's blackout window can produce.
        prism_index = THEME_NAMES.index("Prism")
        for seconds in (0.0, 0.5, 1.0, 2.0, 5.0):
            frame = [(0, 0, 0)] * NUM_PIXELS
            render_theme(frame, prism_index, seconds)
            self.assertTrue(all(color != (0, 0, 0) for color in frame))

    def test_party_mode_is_deterministic_for_the_same_seconds(self):
        first = [(0, 0, 0)] * NUM_PIXELS
        second = [(0, 0, 0)] * NUM_PIXELS
        render_theme(first, PARTY_MODE_THEME, 12.5)
        render_theme(second, PARTY_MODE_THEME, 12.5)
        self.assertEqual(first, second)

    def test_party_mode_uses_all_pixels_over_a_few_pulses(self):
        # A pulse fires every other 175 BPM beat, so the pulse period is
        # double the raw beat period.
        seen_lit = set()
        pulse_seconds = 60.0 / 175.0 * 2
        for pulse in range(12):
            frame = [(0, 0, 0)] * NUM_PIXELS
            render_theme(frame, PARTY_MODE_THEME, pulse * pulse_seconds)
            assert_valid_frame(self, frame)
            for led, color in enumerate(frame):
                if color != (0, 0, 0):
                    seen_lit.add(led)
        self.assertEqual(NUM_PIXELS, len(seen_lit))

    def test_party_mode_pattern_holds_within_the_lit_part_of_a_pulse(self):
        # Offset well clear of the pulse/duty boundaries (rather than exact
        # multiples of the pulse period) so float rounding can't flip which
        # integer pulse -- or which side of the duty cycle -- a timestamp
        # lands on. Duty cycle is 0.55, so 0.1 and 0.3 are both "lit".
        pulse_seconds = 60.0 / 175.0 * 2
        base = 3 * pulse_seconds
        start = [(0, 0, 0)] * NUM_PIXELS
        still_lit = [(0, 0, 0)] * NUM_PIXELS
        next_pulse = [(0, 0, 0)] * NUM_PIXELS
        render_theme(start, PARTY_MODE_THEME, base + pulse_seconds * 0.1)
        render_theme(still_lit, PARTY_MODE_THEME, base + pulse_seconds * 0.3)
        render_theme(next_pulse, PARTY_MODE_THEME, base + pulse_seconds * 1.1)
        self.assertEqual(start, still_lit)
        self.assertNotEqual(start, next_pulse)

    def test_party_mode_blacks_out_during_tail_of_each_pulse(self):
        pulse_seconds = 60.0 / 175.0 * 2
        base = 3 * pulse_seconds
        frame = [(9, 9, 9)] * NUM_PIXELS
        render_theme(frame, PARTY_MODE_THEME, base + pulse_seconds * 0.8)
        self.assertEqual([(0, 0, 0)] * NUM_PIXELS, frame)

    def test_party_mode_pattern_changes_half_as_often_as_raw_beats(self):
        # Sampling at the start of every raw 175 BPM beat, the rendered
        # pattern should only actually change every other sample.
        beat_seconds = 60.0 / 175.0
        distinct = set()
        for beat in range(8):
            frame = [(0, 0, 0)] * NUM_PIXELS
            render_theme(frame, PARTY_MODE_THEME, beat * beat_seconds + beat_seconds * 0.01)
            distinct.add(tuple(frame))
        # 8 raw-beat samples, changing only every other one -> at most 4
        # distinct patterns (could be fewer if a lit/blackout pair repeats).
        self.assertLessEqual(len(distinct), 4)

    def test_party_mode_default_bpm_matches_config_value(self):
        implicit = [(0, 0, 0)] * NUM_PIXELS
        explicit = [(0, 0, 0)] * NUM_PIXELS
        render_theme(implicit, PARTY_MODE_THEME, 1.0)
        render_theme(explicit, PARTY_MODE_THEME, 1.0, party_bpm=PARTY_BPM)
        self.assertEqual(implicit, explicit)

    def test_party_mode_custom_bpm_changes_the_pattern(self):
        default_bpm = [(0, 0, 0)] * NUM_PIXELS
        double_bpm = [(0, 0, 0)] * NUM_PIXELS
        render_theme(default_bpm, PARTY_MODE_THEME, 1.0)
        render_theme(double_bpm, PARTY_MODE_THEME, 1.0, party_bpm=PARTY_BPM * 2)
        self.assertNotEqual(default_bpm, double_bpm)

    def test_render_startup_forwards_party_bpm_to_render_theme(self):
        custom_bpm = 350.0
        startup = [(0, 0, 0)] * NUM_PIXELS
        expected = [(0, 0, 0)] * NUM_PIXELS
        render_startup(startup, STARTUP_MS, theme=PARTY_MODE_THEME, party_bpm=custom_bpm)
        render_theme(expected, PARTY_MODE_THEME, STARTUP_MS / 1000.0, party_bpm=custom_bpm)
        self.assertEqual(expected, startup)

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
