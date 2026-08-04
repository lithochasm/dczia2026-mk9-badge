"""Text-adventure state machine: movement, inventory, puzzles, save/load."""

import os
import shutil
import sys
import tempfile
import unittest

REPOSITORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPOSITORY, "software"))

from game import Game


def _fixture_check(game, verb, noun):
    return verb == "use" and noun == "key"


def _never_solved(game, verb, noun):
    return False


def _stub_room(number):
    return {
        "name": "Room %d" % number,
        "description": "Description of room %d." % number,
        "exits": {},
        "item": None,
        "hint": "",
        "check": _never_solved,
    }


def _make_room_table():
    rooms = [
        {
            "name": "Start Room",
            "description": "A small deterministic test room.",
            "exits": {"north": 1},
            "item": "key",
            "hint": "try 'use key'",
            "check": _fixture_check,
        },
        {
            "name": "North Room",
            "description": "The room to the north.",
            "exits": {"south": 0},
            "item": "torch",
            "hint": "",
            "check": _never_solved,
        },
    ]
    rooms.extend(_stub_room(number) for number in range(2, 9))
    return tuple(rooms)


class FakeHardware:
    def __init__(self):
        self.frame = [(0, 0, 0)] * 15
        self.show_calls = 0

    def show(self, frame):
        self.show_calls += 1


class WriteCapture:
    def __init__(self):
        self.lines = []

    def __call__(self, *parts):
        self.lines.append(" ".join(str(part) for part in parts))

    def text(self):
        return "\n".join(self.lines)


class GameTests(unittest.TestCase):
    def setUp(self):
        self.hardware = FakeHardware()
        self.write = WriteCapture()
        self.room_table = _make_room_table()
        self.tmp_dir = tempfile.mkdtemp()
        self.save_path = os.path.join(self.tmp_dir, "save.json")
        self.game = Game(self.hardware, self.write, save_path=self.save_path, room_table=self.room_table)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def test_start_marks_room_zero_visited_and_prints_name(self):
        self.game.start(1000)
        self.assertTrue(self.game.visited[0])
        self.assertIn("Start Room", self.write.text())

    def test_look_reprints_current_room(self):
        self.game.start(1000)
        self.write.lines.clear()
        self.game.handle_line("look", 1000)
        self.assertIn("Start Room", self.write.text())

    def test_look_does_not_include_the_hint(self):
        self.game.start(1000)
        self.write.lines.clear()
        self.game.handle_line("look", 1000)
        self.assertNotIn("use key", self.write.text())

    def test_hint_shows_room_hint_when_unsolved(self):
        self.game.start(1000)
        self.write.lines.clear()
        self.game.handle_line("hint", 1000)
        self.assertIn("use key", self.write.text())

    def test_hint_reports_nothing_more_once_solved(self):
        self.game.start(1000)
        self.game.handle_line("take key", 1000)
        self.game.handle_line("use key", 1000)
        self.write.lines.clear()
        self.game.handle_line("hint", 1000)
        self.assertIn("Nothing more to figure out here", self.write.text())

    def test_hint_reports_no_hint_for_rooms_without_one(self):
        self.game.start(1000)
        self.game.handle_line("go north", 1000)
        self.write.lines.clear()
        self.game.handle_line("hint", 1000)
        self.assertIn("No hint for this room", self.write.text())

    def test_go_valid_direction_moves_and_marks_target_visited(self):
        self.game.start(1000)
        self.game.handle_line("go north", 1000)
        self.assertEqual(1, self.game.room)
        self.assertTrue(self.game.visited[1])
        self.assertIn("North Room", self.write.text())

    def test_go_invalid_direction_prints_error_and_does_not_move(self):
        self.game.start(1000)
        self.game.handle_line("go west", 1000)
        self.assertEqual(0, self.game.room)
        self.assertIn("can't go that way", self.write.text())

    def test_go_without_argument_prompts_usage(self):
        self.game.start(1000)
        self.write.lines.clear()
        self.game.handle_line("go", 1000)
        self.assertEqual(0, self.game.room)
        self.assertIn("Go where?", self.write.text())

    def test_render_leds_colors_reflect_not_visited_visited_solved(self):
        self.game.start(1000)
        self.game.solved[0] = False
        self.game.visited[1] = True
        self.game.solved[2] = True
        self.game.visited[2] = True
        self.game.render_leds()
        self.assertEqual((40, 32, 0), self.hardware.frame[0])
        self.assertEqual((40, 32, 0), self.hardware.frame[1])
        self.assertEqual((0, 40, 0), self.hardware.frame[2])
        self.assertEqual((40, 0, 0), self.hardware.frame[3])

    def test_render_leds_blanks_perimeter_leds(self):
        self.game.start(1000)
        self.assertEqual([(0, 0, 0)] * 6, self.hardware.frame[9:15])

    def test_take_adds_item_to_inventory(self):
        self.game.start(1000)
        self.game.handle_line("take key", 1000)
        self.assertIn("key", self.game.inventory)

    def test_inventory_reports_empty_then_lists_items(self):
        self.game.start(1000)
        self.write.lines.clear()
        self.game.handle_line("inventory", 1000)
        self.assertIn("aren't carrying anything", self.write.text())

        self.game.handle_line("take key", 1000)
        self.write.lines.clear()
        self.game.handle_line("inv", 1000)
        self.assertIn("key", self.write.text())

    def test_take_with_no_args_takes_room_item(self):
        self.game.start(1000)
        self.game.handle_line("take", 1000)
        self.assertIn("key", self.game.inventory)

    def test_take_mismatched_name_reports_nothing_here(self):
        self.game.start(1000)
        self.game.handle_line("take torch", 1000)
        self.assertNotIn("torch", self.game.inventory)

    def test_take_reports_nothing_when_room_has_no_item(self):
        self.game.start(1000)
        self.game.room = 2  # a stub room with no item
        self.write.lines.clear()
        self.game.handle_line("take", 1000)
        self.assertIn("nothing here to take", self.write.text())

    def test_take_again_reports_already_have_it(self):
        self.game.start(1000)
        self.game.handle_line("take key", 1000)
        self.write.lines.clear()
        self.game.handle_line("take key", 1000)
        self.assertIn("already have", self.write.text())
        self.assertEqual(["key"], self.game.inventory)

    def test_look_mentions_room_item_when_present(self):
        self.game.start(1000)
        self.write.lines.clear()
        self.game.handle_line("look", 1000)
        self.assertIn("key", self.write.text())

    def test_look_omits_item_once_taken(self):
        self.game.start(1000)
        self.game.handle_line("take key", 1000)
        self.write.lines.clear()
        self.game.handle_line("look", 1000)
        self.assertNotIn("You see:", self.write.text())

    def test_use_reports_error_when_item_not_carried(self):
        self.game.start(1000)
        self.write.lines.clear()
        self.game.handle_line("use key", 1000)
        self.assertIn("don't have that", self.write.text())
        self.assertFalse(self.game.solved[0])

    def test_use_item_solving_puzzle_marks_room_solved_and_turns_key_green(self):
        self.game.start(1000)
        self.game.handle_line("take key", 1000)
        self.game.handle_line("use key", 1000)
        self.assertTrue(self.game.solved[0])
        self.assertEqual((0, 40, 0), self.hardware.frame[0])
        self.assertIn("Puzzle solved", self.write.text())

    def test_use_item_not_matching_puzzle_leaves_room_unsolved(self):
        self.game.start(1000)
        self.game.handle_line("go north", 1000)
        self.game.handle_line("take torch", 1000)
        self.game.handle_line("go south", 1000)
        self.game.handle_line("use torch", 1000)
        self.assertFalse(self.game.solved[0])

    def test_puzzle_check_not_re_invoked_once_room_already_solved(self):
        calls = []

        def counting_check(game, verb, noun):
            calls.append((verb, noun))
            return True

        self.room_table[0]["check"] = counting_check
        self.game.start(1000)
        self.game.handle_line("take key", 1000)
        self.game.handle_line("use key", 1000)
        self.game.handle_line("use key", 1000)
        self.assertEqual(1, len(calls))

    def test_save_then_load_round_trips_state(self):
        self.game.start(1000)
        self.game.handle_line("take key", 1000)
        self.game.handle_line("go north", 1000)
        self.game.handle_line("take torch", 1000)
        self.game.room_table[1]["check"] = _fixture_check
        self.game.handle_line("use key", 1000)
        self.game.flags["visited_shrine"] = True
        self.game.save()

        reloaded = Game(FakeHardware(), WriteCapture(), save_path=self.save_path, room_table=self.room_table)
        loaded = reloaded.load()

        self.assertTrue(loaded)
        self.assertEqual(self.game.room, reloaded.room)
        self.assertEqual(self.game.visited, reloaded.visited)
        self.assertEqual(self.game.solved, reloaded.solved)
        self.assertEqual(self.game.inventory, reloaded.inventory)
        self.assertEqual(self.game.flags, reloaded.flags)

    def test_load_without_existing_save_file_reports_and_returns_false(self):
        self.game.start(1000)
        self.write.lines.clear()
        result = self.game.handle_line("load", 1000)
        self.assertTrue(result)
        self.assertIn("No saved game found", self.write.text())

    def test_save_writes_valid_json_with_expected_keys(self):
        import json

        self.game.start(1000)
        self.game.save()
        with open(self.save_path) as handle:
            data = json.loads(handle.read())
        for key in ("room", "visited", "solved", "inventory", "flags"):
            self.assertIn(key, data)

    def test_quit_returns_false(self):
        self.game.start(1000)
        self.assertFalse(self.game.handle_line("quit", 1000))

    def test_quit_auto_saves_progress(self):
        self.game.start(1000)
        self.game.handle_line("take key", 1000)
        self.game.handle_line("use key", 1000)
        self.game.handle_line("quit", 1000)

        reloaded = Game(FakeHardware(), WriteCapture(), save_path=self.save_path, room_table=self.room_table)
        self.assertTrue(reloaded.load())
        self.assertTrue(reloaded.solved[0])
        self.assertEqual(["key"], reloaded.inventory)

    def test_quit_reports_save_failure_but_still_quits(self):
        self.game.start(1000)
        self.game.save_path = os.path.join(self.tmp_dir, "missing_dir", "save.json")
        self.write.lines.clear()
        result = self.game.handle_line("quit", 1000)
        self.assertFalse(result)
        self.assertIn("Could not save", self.write.text())

    def test_restart_wipes_progress_and_stays_in_game(self):
        self.game.start(1000)
        self.game.handle_line("take key", 1000)
        self.game.handle_line("use key", 1000)
        self.game.handle_line("go east", 1000)

        result = self.game.handle_line("restart", 1000)

        self.assertTrue(result)
        self.assertEqual(0, self.game.room)
        self.assertEqual([], self.game.inventory)
        self.assertFalse(any(self.game.solved))
        self.assertEqual([True] + [False] * (len(self.room_table) - 1), self.game.visited)

    def test_restart_reprints_the_opening_room(self):
        self.game.start(1000)
        self.game.handle_line("go east", 1000)
        self.write.lines.clear()
        self.game.handle_line("restart", 1000)
        self.assertIn("Restarting...", self.write.text())
        self.assertIn("Start Room", self.write.text())

    def test_non_quit_verbs_return_true(self):
        self.game.start(1000)
        self.assertTrue(self.game.handle_line("look", 1000))
        self.assertTrue(self.game.handle_line("help", 1000))

    def test_unknown_verb_reports_friendly_error_without_crashing(self):
        self.game.start(1000)
        self.write.lines.clear()
        result = self.game.handle_line("xyzzy", 1000)
        self.assertTrue(result)
        self.assertIn("don't understand", self.write.text())

    def test_empty_line_is_a_no_op(self):
        self.game.start(1000)
        self.write.lines.clear()
        result = self.game.handle_line("   ", 1000)
        self.assertTrue(result)
        self.assertEqual([], self.write.lines)

    def test_help_lists_all_verbs(self):
        self.game.start(1000)
        self.write.lines.clear()
        self.game.handle_line("help", 1000)
        output = self.write.text()
        for verb in ("look", "go", "take", "use", "hint", "inventory", "save", "load", "restart", "quit"):
            self.assertIn(verb, output)


if __name__ == "__main__":
    unittest.main()
