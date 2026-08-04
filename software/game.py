"""Text-adventure game-mode state machine.

Generic plumbing only -- movement, inventory, save/load, and the room-status
LEDs. All actual content (room text, puzzle solutions) lives in rooms.py.
"""

import json

from rooms import ROOMS as _DEFAULT_ROOMS

_DEFAULT_SAVE_PATH = "/game_save.json"

# Placeholder flat colors -- purely a skeleton, retune freely.
_COLOR_NOT_VISITED = (40, 0, 0)   # red: room never visited
_COLOR_VISITED = (40, 32, 0)      # yellow: visited, puzzle unsolved
_COLOR_SOLVED = (0, 40, 0)        # green: visited, puzzle solved
_COLOR_OFF = (0, 0, 0)

_HELP_LINES = (
    "Game commands:",
    "  look                 describe the current room",
    "  go <direction>       move through one of this room's exits",
    "  take [item]          pick up the item in this room",
    "  use <item>           use a carried item / attempt this room's puzzle",
    "  hint                 show a hint for this room's puzzle",
    "  inventory (inv, i)   list carried items",
    "  save                 save your progress",
    "  load                 load your last saved progress",
    "  restart              wipe progress and start over",
    "  help                 show this listing",
    "  quit                 save progress and return to the badge console",
)


class Game:
    """One play session. Construct fresh each time `play` is typed."""

    def __init__(self, hardware, write, save_path=_DEFAULT_SAVE_PATH, room_table=None):
        self.hardware = hardware
        self._write = write  # same write(*parts) contract as SerialMenu._write_line
        self.save_path = save_path
        self.room_table = room_table if room_table is not None else _DEFAULT_ROOMS
        self._reset_state()

    def _reset_state(self):
        num_rooms = len(self.room_table)
        self.room = 0
        self.visited = [False] * num_rooms
        self.solved = [False] * num_rooms
        self.inventory = []
        self.flags = {}

    def start(self, now_ms):
        self._reset_state()
        self.visited[self.room] = True
        self.render_leds()
        self._write("Type 'help' for commands, 'quit' to leave the game.")
        self._look()

    def handle_line(self, line, now_ms):
        """Parse and dispatch one typed line. Returns False to signal quit."""
        line = line.strip()
        if not line:
            return True
        parts = line.split()
        verb = parts[0].lower()
        args = parts[1:]
        handler = _VERBS.get(verb)
        if handler is None:
            self._write("I don't understand '" + verb + "'. Try 'help'.")
            return True
        try:
            return handler(self, args, now_ms)
        except Exception as error:
            self._write("Something went wrong:", error)
            return True

    def render_leds(self):
        """Paint the 9 room-status key LEDs; blank the rest while in-game."""
        frame = self.hardware.frame
        num_rooms = len(self.room_table)
        for room_id in range(num_rooms):
            if self.solved[room_id]:
                frame[room_id] = _COLOR_SOLVED
            elif self.visited[room_id]:
                frame[room_id] = _COLOR_VISITED
            else:
                frame[room_id] = _COLOR_NOT_VISITED
        # Perimeter LEDs (frame[9:15] in production) sit idle here. Easy
        # extension point: highlight the current room's perimeter LED, etc.
        for led in range(num_rooms, len(frame)):
            frame[led] = _COLOR_OFF
        self.hardware.show(self.hardware.frame)

    def save(self):
        data = {
            "room": self.room,
            "visited": self.visited,
            "solved": self.solved,
            "inventory": self.inventory,
            "flags": self.flags,
        }
        text = json.dumps(data)
        with open(self.save_path, "w") as handle:
            handle.write(text)

    def load(self):
        try:
            with open(self.save_path) as handle:
                text = handle.read()
        except OSError:
            return False
        data = json.loads(text)
        num_rooms = len(self.room_table)
        self.room = data.get("room", 0)
        self.visited = data.get("visited", [False] * num_rooms)
        self.solved = data.get("solved", [False] * num_rooms)
        self.inventory = data.get("inventory", [])
        self.flags = data.get("flags", {})
        return True

    def _look(self):
        room = self.room_table[self.room]
        self._write(room["name"])
        self._write(room["description"])
        item = room.get("item")
        if item and item not in self.inventory:
            self._write("You see:", item)
        exits = sorted(room["exits"].keys())
        if exits:
            self._write("Exits:", ", ".join(exits))
        else:
            self._write("There are no obvious exits.")

    def _hint(self):
        room = self.room_table[self.room]
        if self.solved[self.room]:
            self._write("Nothing more to figure out here.")
        elif room.get("hint"):
            self._write("Hint:", room["hint"])
        else:
            self._write("No hint for this room.")

    def _check_puzzle(self, verb, noun):
        room_id = self.room
        if self.solved[room_id]:
            return
        check = self.room_table[room_id]["check"]
        if check(self, verb, noun):
            self.solved[room_id] = True
            self.render_leds()
            self._write("*** Puzzle solved! ***")  # TODO(you): customize


def _verb_look(game, args, now_ms):
    game._look()
    return True


def _verb_go(game, args, now_ms):
    if not args:
        game._write("Go where? Try 'go <direction>'.")
        return True
    direction = args[0].lower()
    room = game.room_table[game.room]
    target = room["exits"].get(direction)
    if target is None:
        exits = ", ".join(sorted(room["exits"])) or "(none)"
        game._write("You can't go that way. Exits:", exits)
        return True
    game.room = target
    game.visited[target] = True
    game.render_leds()
    game._look()
    return True


def _verb_take(game, args, now_ms):
    room = game.room_table[game.room]
    item = room.get("item")
    if item is None:
        game._write("There's nothing here to take.")
        return True
    if args:
        noun = " ".join(args).lower()
        if noun != item.lower():
            game._write("There's no", noun, "here.")
            return True
    if item in game.inventory:
        game._write("You already have the", item + ".")
        return True
    game.inventory.append(item)
    game._write("Taken:", item)
    game._check_puzzle("take", item)
    return True


def _verb_use(game, args, now_ms):
    if not args:
        game._write("Use what?")
        return True
    noun = " ".join(args).lower()
    if noun not in game.inventory:
        game._write("You don't have that.")
        return True
    game._check_puzzle("use", noun)
    return True


def _verb_hint(game, args, now_ms):
    game._hint()
    return True


def _verb_inventory(game, args, now_ms):
    if game.inventory:
        game._write("Carrying:", ", ".join(game.inventory))
    else:
        game._write("You aren't carrying anything.")
    return True


def _verb_save(game, args, now_ms):
    game.save()
    game._write("Game saved.")
    return True


def _verb_load(game, args, now_ms):
    if game.load():
        game.render_leds()
        game._write("Game loaded.")
        game._look()
    else:
        game._write("No saved game found.")
    return True


def _verb_help(game, args, now_ms):
    for line in _HELP_LINES:
        game._write(line)
    return True


def _verb_restart(game, args, now_ms):
    game._write("Restarting...")
    game.start(now_ms)
    return True


def _verb_quit(game, args, now_ms):
    try:
        game.save()
        game._write("Progress saved.")
    except Exception as error:
        game._write("Could not save:", error)
    game._write("Goodbye. Returning to the badge console.")
    return False


_VERBS = {
    "look": _verb_look,
    "go": _verb_go,
    "take": _verb_take,
    "use": _verb_use,
    "hint": _verb_hint,
    "inventory": _verb_inventory,
    "inv": _verb_inventory,
    "i": _verb_inventory,
    "save": _verb_save,
    "load": _verb_load,
    "restart": _verb_restart,
    "help": _verb_help,
    "quit": _verb_quit,
}
