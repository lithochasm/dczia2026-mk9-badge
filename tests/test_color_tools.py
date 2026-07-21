"""Host-side tests for the CircuitPython-independent RGB arithmetic."""

import os
import sys
import types
import unittest


SEEN_HUES = []


def _fake_colorwheel(hue):
    SEEN_HUES.append(hue)
    return 0x804020


fake_rainbowio = types.ModuleType("rainbowio")
fake_rainbowio.colorwheel = _fake_colorwheel
sys.modules["rainbowio"] = fake_rainbowio

REPOSITORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPOSITORY, "software"))

import color_tools  # noqa: E402  (rainbowio must be stubbed first)


class ColorToolsTests(unittest.TestCase):

    def test_unpack_uses_rrggbb_order(self):
        self.assertEqual((0x12, 0x34, 0x56), color_tools.unpack(0x123456))

    def test_wheel_returns_a_scaled_tuple(self):
        self.assertEqual((64, 32, 16), color_tools.wheel(511, 0.5))
        self.assertEqual(255, SEEN_HUES[-1])

    def test_scale_clamps_level(self):
        self.assertEqual((0, 0, 0), color_tools.scale((10, 20, 30), -1.0))
        self.assertEqual((10, 20, 30), color_tools.scale((10, 20, 30), 2.0))

    def test_blend_clamps_and_interpolates(self):
        self.assertEqual((127, 0, 127),
                         color_tools.blend((255, 0, 0), (0, 0, 255), 0.5))
        self.assertEqual((255, 0, 0),
                         color_tools.blend((255, 0, 0), (0, 0, 255), -1.0))

    def test_add_saturates_channels(self):
        self.assertEqual((255, 70, 110),
                         color_tools.add((250, 20, 10), (20, 100, 200), 0.5))


if __name__ == "__main__":
    unittest.main()
