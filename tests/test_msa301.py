"""Verify MSA301 register setup and signed 14-bit decoding."""

import os
import sys
import unittest

REPOSITORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPOSITORY, "software"))

from msa301 import MSA301, STANDARD_GRAVITY, decode_axis


class FakeI2C:
    def __init__(self):
        self.registers = bytearray(256)
        self.registers[0x01] = 0x13

    def readfrom_mem(self, address, register, length):
        return bytes(self.registers[register:register + length])

    def writeto_mem(self, address, register, data):
        self.registers[register:register + len(data)] = data


class MSA301Tests(unittest.TestCase):
    def test_signed_axis_decode(self):
        self.assertEqual(2048, decode_axis(0x00, 0x20))
        self.assertEqual(-2048, decode_axis(0x00, 0xE0))

    def test_configures_14_bit_four_g_mode(self):
        bus = FakeI2C()
        MSA301(bus)
        self.assertEqual(0x07, bus.registers[0x10] & 0xEF)
        self.assertEqual(0x0E, bus.registers[0x11] & 0xDE)
        self.assertEqual(0x01, bus.registers[0x0F] & 0x0F)

    def test_acceleration_is_metres_per_second_squared(self):
        bus = FakeI2C()
        sensor = MSA301(bus)
        bus.registers[0x02:0x08] = bytes((0x00, 0x20, 0x00, 0xE0, 0x00, 0x00))
        x, y, z = sensor.acceleration()
        self.assertAlmostEqual(STANDARD_GRAVITY, x, places=4)
        self.assertAlmostEqual(-STANDARD_GRAVITY, y, places=4)
        self.assertEqual(0.0, z)

    def test_rejects_wrong_part(self):
        bus = FakeI2C()
        bus.registers[0x01] = 0
        with self.assertRaises(OSError):
            MSA301(bus)


if __name__ == "__main__":
    unittest.main()
