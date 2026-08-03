"""Save/load of the persisted theme/brightness settings file."""

import os
import shutil
import sys
import tempfile
import unittest

REPOSITORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPOSITORY, "software"))

import user_config


class UserConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp_dir, "user_config.json")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def test_save_then_load_round_trips_values(self):
        user_config.save(4, 0.55, path=self.path)
        data = user_config.load(path=self.path)
        self.assertEqual({"theme": 4, "brightness": 0.55}, data)

    def test_load_with_no_file_returns_none(self):
        self.assertIsNone(user_config.load(path=self.path))

    def test_load_with_corrupt_json_returns_none(self):
        with open(self.path, "w") as handle:
            handle.write("{not valid json")
        self.assertIsNone(user_config.load(path=self.path))

    def test_save_to_unwritable_path_does_not_raise(self):
        bad_path = os.path.join(self.tmp_dir, "missing_dir", "user_config.json")
        user_config.save(0, 0.3, path=bad_path)  # must not raise

    def test_save_overwrites_previous_value(self):
        user_config.save(1, 0.2, path=self.path)
        user_config.save(7, 0.9, path=self.path)
        self.assertEqual({"theme": 7, "brightness": 0.9}, user_config.load(path=self.path))


if __name__ == "__main__":
    unittest.main()
