"""Host-side tests for portable RGB arithmetic."""

import os
import sys
import unittest

REPOSITORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPOSITORY, "software"))

import color_tools


class ColorToolsTests(unittest.TestCase):
    def test_wheel_wraps_and_returns_rgb(self):
        self.assertEqual(color_tools.wheel(0), color_tools.wheel(256))
        self.assertEqual((255, 0, 0), color_tools.wheel(0))
        self.assertEqual((0, 255, 0), color_tools.wheel(85))

    def test_scale_clamps_level(self):
        self.assertEqual((0, 0, 0), color_tools.scale((10, 20, 30), -1.0))
        self.assertEqual((10, 20, 30), color_tools.scale((10, 20, 30), 2.0))

    def test_multiply_can_brighten_and_saturate(self):
        self.assertEqual((150, 225, 255), color_tools.multiply((100, 150, 220), 1.5))

    def test_blend_interpolates(self):
        self.assertEqual(
            (127, 0, 127),
            color_tools.blend((255, 0, 0), (0, 0, 255), 0.5),
        )

    def test_add_saturates_channels(self):
        self.assertEqual(
            (255, 70, 110),
            color_tools.add((250, 20, 10), (20, 100, 200), 0.5),
        )

    def test_palette_loops(self):
        colors = ((255, 0, 0), (0, 0, 255))
        self.assertEqual(color_tools.palette(colors, 0.0), color_tools.palette(colors, 1.0))


if __name__ == "__main__":
    unittest.main()
