"""Room data for the text-adventure game mode.

This module holds essentially all the *content* of the game; game.py is
generic plumbing that should never need to change as you fill this in.

Room id == physical key index (0-8):
    0 1 2
    3 4 5
    6 7 8
(same 3x3 ordering as config.NUMPAD_CODES / LED_POSITIONS[0:9]).

Each room is a dict with:
    "name":        str, short title shown by `look`.
    "description": str, freeform text shown on entry and by `look`.
                   TODO(you): replace every placeholder description.
    "exits":       dict[str, int], direction/noun -> target room id.
                   Rooms are NOT required to share a common compass; define
                   whatever exit names make sense per room (see room 0).
    "item":        str or None. An item sitting in this room that `take`
                   picks up into the inventory; `use <item>` only works on
                   items you're carrying. None if the room has nothing to
                   take.
    "hint":        str, one-line nudge shown by the `hint` command while
                   unsolved. Use "" for a room with no puzzle.
    "check":       callable(game, verb, noun) -> bool. Called on every
                   `take`/`use` typed while standing in this room. Return
                   True the instant this room's puzzle should flip to
                   "solved" (green key). Defaults to `_never_solved`.
"""

NUM_ROOMS = 9


def _never_solved(game, verb, noun):
    """Default `check` hook: this room has no puzzle."""
    return False


def _example_check(game, verb, noun):
    """TODO(you): replace with real puzzle logic for this room.

    Worked example: solved by typing "use key" while standing here.
    verb/noun are the lowercased words after the command name, e.g.
    "use rusty key" -> verb="use", noun="rusty key".
    """
    return verb == "use" and noun == "key"


ROOMS = (
    # Room 0 -- fully worked EXAMPLE. Replace with your own room 0.
    {
        "name": "Entrance Hall",
        "description": (
            "TODO(you): real description. This is the example room, wired "
            "up end to end (exits + a solvable puzzle) to prove the shape "
            "works; replace this text."
        ),
        "exits": {"east": 1, "south": 3},
        "item": "key",
        "hint": "TODO(you): try 'use key'.",
        "check": _example_check,
    },
    {
        "name": "Room 1",
        "description": "TODO(you): describe this room.",
        "exits": {"east": 2, "south": 4, "west": 0},
        "item": None,
        "hint": "",
        "check": _never_solved,
    },
    {
        "name": "Room 2",
        "description": "TODO(you): describe this room.",
        "exits": {"south": 5, "west": 1},
        "item": None,
        "hint": "",
        "check": _never_solved,
    },
    {
        "name": "Room 3",
        "description": "TODO(you): describe this room.",
        "exits": {"east": 4, "north": 0, "south": 6},
        "item": None,
        "hint": "",
        "check": _never_solved,
    },
    {
        "name": "Room 4",
        "description": "TODO(you): describe this room.",
        "exits": {"east": 5, "north": 1, "south": 7, "west": 3},
        "item": None,
        "hint": "",
        "check": _never_solved,
    },
    {
        "name": "Room 5",
        "description": "TODO(you): describe this room.",
        "exits": {"north": 2, "south": 8, "west": 4},
        "item": None,
        "hint": "",
        "check": _never_solved,
    },
    {
        "name": "Room 6",
        "description": "TODO(you): describe this room.",
        "exits": {"east": 7, "north": 3},
        "item": None,
        "hint": "",
        "check": _never_solved,
    },
    {
        "name": "Room 7",
        "description": "TODO(you): describe this room.",
        "exits": {"east": 8, "north": 4, "west": 6},
        "item": None,
        "hint": "",
        "check": _never_solved,
    },
    {
        "name": "Room 8",
        "description": "TODO(you): describe this room.",
        "exits": {"north": 5, "west": 7},
        "item": None,
        "hint": "",
        "check": _never_solved,
    },
)

assert len(ROOMS) == NUM_ROOMS
