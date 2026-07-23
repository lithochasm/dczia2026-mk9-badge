"""Verify debounce behavior and physical key numbering."""

import os
import sys
import unittest

REPOSITORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPOSITORY, "software"))

from config import DEBOUNCE_SCANS
from key_matrix import KeyMatrix


class FakePin:
    IN = 0
    OUT = 1
    PULL_DOWN = 2

    def __init__(self, number, mode, pull=None, value=0):
        self.number = number
        self._value = value

    def value(self, new_value=None):
        if new_value is not None:
            self._value = new_value
        return self._value


class KeyMatrixTests(unittest.TestCase):
    def test_debounces_row_major_key(self):
        matrix = KeyMatrix(FakePin)
        samples = [False] * 9
        matrix._raw = lambda: list(samples)

        samples[5] = True
        events = ()
        for scan in range(1, DEBOUNCE_SCANS + 1):
            events = matrix.update(scan * 4)

        self.assertEqual(1, len(events))
        self.assertEqual(5, events[0].key)
        self.assertTrue(events[0].pressed)
        self.assertTrue(matrix.pressed(5))

    def test_bounce_does_not_create_event(self):
        matrix = KeyMatrix(FakePin)
        samples = [False] * 9
        matrix._raw = lambda: list(samples)
        samples[0] = True
        matrix.update(4)
        samples[0] = False
        self.assertFalse(matrix.update(8))

    def test_uses_as_built_row_and_column_pins(self):
        matrix = KeyMatrix(FakePin)
        self.assertEqual([27, 26, 16], [pin.number for pin in matrix.rows])
        self.assertEqual([17, 13, 0], [pin.number for pin in matrix.columns])


if __name__ == "__main__":
    unittest.main()
