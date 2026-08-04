"""Sanity checks for the text-adventure room data."""

import os
import sys
import unittest

REPOSITORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPOSITORY, "software"))

import rooms
from rooms import ROOMS


class RoomsTests(unittest.TestCase):
    def test_room_count_is_nine(self):
        self.assertEqual(9, len(ROOMS))
        self.assertEqual(9, rooms.NUM_ROOMS)

    def test_every_room_has_required_fields(self):
        for room in ROOMS:
            self.assertIsInstance(room["name"], str)
            self.assertTrue(room["name"])
            self.assertIsInstance(room["description"], str)
            self.assertTrue(room["description"])
            self.assertIsInstance(room["exits"], dict)
            self.assertTrue(room["item"] is None or isinstance(room["item"], str))
            self.assertIsInstance(room["hint"], str)
            self.assertTrue(callable(room["check"]))

    def test_every_exit_target_is_a_valid_room_id(self):
        for room in ROOMS:
            for target in room["exits"].values():
                self.assertIsInstance(target, int)
                self.assertGreaterEqual(target, 0)
                self.assertLess(target, len(ROOMS))

    def test_every_exit_direction_is_a_string(self):
        for room in ROOMS:
            for direction in room["exits"]:
                self.assertIsInstance(direction, str)
                self.assertTrue(direction)

    def test_default_check_returns_false(self):
        self.assertFalse(rooms._never_solved(None, "use", "key"))

    def test_example_room_check_demonstrates_the_shape(self):
        check = ROOMS[0]["check"]
        self.assertTrue(check(None, "use", "key"))
        self.assertFalse(check(None, "use", "torch"))
        self.assertFalse(check(None, "take", "key"))

    def test_example_room_item_matches_its_puzzle(self):
        self.assertEqual("key", ROOMS[0]["item"])


if __name__ == "__main__":
    unittest.main()
