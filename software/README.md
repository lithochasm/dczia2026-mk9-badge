# MK9 Badge — MicroPython Firmware

Native MicroPython firmware for the RP2040-based DCZia MK9 badge. It has no
runtime dependency on CircuitPython or Adafruit libraries.

## Behavior

Startup is a 3.2-second smoothly fading, moving rainbow that cross-fades into
the active theme. Normal key taps still send the USB numpad layout:

```text
7 8 9
4 5 6
1 2 3
```

Hold a key for 750 ms to select its theme. A long press changes lighting and
does not send a number:

| Key | Theme |
|---:|---|
| 1 | Party Mode |
| 2 | Vaporwave |
| 3 | Deep Ocean |
| 4 | Ember |
| 5 | Matrix |
| 6 | Ultraviolet |
| 7 | Sunset |
| 8 | Glacier |
| 9 | Moonlight |

**Party Mode** (key 1) is a random-looking flicker across all 15 LEDs,
pulsing at 175 BPM by default but only hitting on every other beat: each
pulse snaps to a new random pattern, holds it for the first 55% of the
pulse, then blacks out for the rest before the next pulse's pattern snaps
in. The tempo is adjustable live with the `bpm` command (see below), or
directly from the badge: while Party Mode is active, key 7 nudges it down
and key 8 nudges it up, 2 BPM per short press. While Party Mode is active,
physical key presses otherwise stop sending USB numpad keystrokes
(long-press theme selection still works on every key, including 7 and 8, so
you can always long-press back out into a different theme).

There's also a 10th theme, **Prism** — the original default rainbow — which
isn't bound to a key (there are only 9 for 10 themes), so reach it from the
serial console with `theme 10` or `theme prism`.

Every press creates a spatial ripple. As a hanging badge rotates, the current
theme's light quickly follows physical down and gathers like liquid at the
lowest edge or corner, with a short overshoot and settling shoreline wobble.
Forward/back tilt and quick movement do not change the pool while it is
hanging; Z smoothly suppresses the effect when the badge is laid flat. If the
accelerometer is not responding, the keys, LEDs, and USB keyboard continue to
work.

## Hardware map

| Function | GPIO |
|---|---|
| 15-pixel WS2812/SK6812 chain | GP21 |
| Matrix rows R0/R1/R2 | GP27, GP26, GP16 |
| Matrix columns C0/C1/C2 | GP17, GP13, GP0 |
| MSA301/GSDA213 SDA/SCL | GP18, GP19 (I2C1) |
| SAO SDA/SCL | GP9, GP10 (software I2C) |
| SAO GPIO | GP29, GP28, GP12, GP11 |

The key scanner drives one column high and reads rows with pull-downs. This
matches the PCB's column → switch → diode → row orientation.

### Physical layout

Traced from the PCB netlist (switch → diode → row nets, and each LED's
DIN/DOUT chain position), viewed from the front of the badge:

```text
                 ┌──[pwr]──[ USB-C ]──[boot]──[reset]──┐
                 │                                     │
     D27 ●       │    [ 7 ]      [ 8 ]      [ 9 ]      │       ● D22
  (pixel 14)     │   key 0       key 1       key 2     │    (pixel 9)
                 │   pixel 0     pixel 1     pixel 2   │
                 │                                     │
                 │    [ 4 ]      [ 5 ]      [ 6 ]      │
                 │   key 3       key 4       key 5     │
     D26 ●       │   pixel 3     pixel 4     pixel 5   │       ● D23
  (pixel 13)     │                                     │    (pixel 10)
                 │    [ 1 ]      [ 2 ]      [ 3 ]      │
                 │   key 6       key 7       key 8     │
                 │   pixel 6     pixel 7     pixel 8   │
                 │                                     │
                 └──────────●───────────●──────────────┘
                           D25          D24
                        (pixel 12)   (pixel 11)
```

| Key index | Pixel index | Numpad digit | Row/Col nets | Switch ref | LED ref | Physical position |
|---|---|---|---|---|---|---|
| 0 | 0 | 7 | R0,C0 | SW4 | D13 | top-left |
| 1 | 1 | 8 | R0,C1 | SW5 | D14 | top-middle |
| 2 | 2 | 9 | R0,C2 | SW6 | D15 | top-right |
| 3 | 3 | 4 | R1,C0 | SW7 | D16 | mid-left |
| 4 | 4 | 5 | R1,C1 | SW8 | D17 | mid-middle |
| 5 | 5 | 6 | R1,C2 | SW9 | D18 | mid-right |
| 6 | 6 | 1 | R2,C0 | SW10 | D19 | bottom-left |
| 7 | 7 | 2 | R2,C1 | SW11 | D20 | bottom-middle |
| 8 | 8 | 3 | R2,C2 | SW12 | D21 | bottom-right |

Key index and pixel index match for all 9 keys — the per-key LEDs are simply
the first 9 pixels in the chain, so `badge.py` indexes straight into
`frame[key]` with no translation. Pixels 9-14 are the 6 side-firing
underglow LEDs (2 per left/right edge, 2 along the bottom); the top edge has
none since it's occupied by USB-C, the power switch, and the reset/BOOTSEL
buttons.

## Firmware structure

```text
software/
├── boot.py          USB serial + HID setup
├── main.py          MicroPython entry point
├── badge.py         keys, long presses, motion, ripples, main loop
├── themes.py        startup rainbow and all nine themes
├── hardware.py      NeoPixels, matrix, accelerometer, and SAO setup
├── key_matrix.py    active-high scanner with software debounce
├── msa301.py        native accelerometer driver
├── color_tools.py   portable RGB math
├── config.py        pins and user-tunable timing/brightness
├── usb_keyboard.py  non-blocking numpad reports
├── serial_menu.py   typed USB-serial console (help/status/theme/brightness/accel/reset/bootloader)
├── rooms.py         text-adventure room data — this is where you write your game
├── game.py          text-adventure state machine (movement, inventory, save/load)
├── user_config.py   persisted theme/brightness/party-bpm settings, loaded on boot
└── lib/usb/         official MicroPython USB device libraries
```

## Serial console

While the badge is running (not just at the REPL), the USB-CDC serial
connection also accepts typed commands — connect with `mpremote connect auto
repl`, Thonny's shell, or any serial terminal, then type `help` and press
Enter for the full command listing (`status`, `theme [n|name]`, `brightness
[0-100]`, `bpm [1-999]`, `accel`, `reset`, `bootloader`). Typing anything at
all before you've seen the listing prints it automatically. Ctrl-C still
drops to the real MicroPython REPL and kills the running badge script, same
as always — that's unrelated to and unaffected by the console.

Changing the theme (long-press or `theme`), `brightness`, or `bpm` (Party
Mode's tempo) saves all three settings to `/user_config.json` on the badge's
flash filesystem, and they're restored automatically the next time the badge
boots.

## Text adventure

Typing `play` at the serial console starts a small text-adventure game that
runs inside the same firmware, taking over the typed console until you type
`quit`. All game content — room names/descriptions, exits, and puzzles —
lives in `rooms.py`; fill that in with your own 9 rooms. `game.py`'s
plumbing (movement, inventory, save/load, room-status LEDs) needs no changes
to add content.

While the game is active the 9 physical keys stop sending USB numpad
keystrokes and stop selecting lighting themes. Instead, each key becomes a
purely visual status board for the room of the same index (key 1 = room 0,
etc.) — pressing a key does not move you:

| Color  | Meaning                         |
|--------|----------------------------------|
| Red    | Room not yet visited            |
| Yellow | Visited, puzzle not yet solved  |
| Green  | Visited, puzzle solved          |

Commands: `look`, `go <direction>` (per-room exits, not fixed compass
directions), `take` (picks up the current room's item, if any), `use <item>`
(only works on items you're carrying), `hint`, `inventory` (`inv`/`i`),
`save`, `load`, `restart` (wipes progress and starts over), `help`, `quit`.
Progress saves to `/game_save.json` on the badge's flash filesystem
automatically when you `quit`, or on demand with `save`.

## Install on the badge

1. Hold **BOOTSEL** while plugging in the badge. It appears as `RPI-RP2`.
2. Copy the included `firmware/RPI_PICO-20260406-v1.28.0.uf2` onto `RPI-RP2`.
   It is the official stable v1.28 build from
   [micropython.org/download/RPI_PICO](https://micropython.org/download/RPI_PICO/).
3. The badge reboots into MicroPython. Unlike CircuitPython, it does not expose
   a drag-and-drop source drive. Use Thonny or `mpremote` to upload the files.

In Thonny, select **MicroPython (Raspberry Pi Pico)**, then upload every `.py`
file in `software/` to `/` and upload `software/lib/` as `/lib/`.

With `mpremote`:

```sh
cd software
mpremote connect auto fs mkdir :lib
mpremote connect auto fs mkdir :lib/usb
mpremote connect auto fs mkdir :lib/usb/device
mpremote connect auto fs cp *.py :
mpremote connect auto fs cp lib/usb/__init__.py :lib/usb/__init__.py
mpremote connect auto fs cp lib/usb/device/*.py :lib/usb/device/
mpremote connect auto reset
```

From the repository root, `tools/upload_micropython.sh` runs those commands
for you.

If a directory already exists, its `mkdir` command may print an error; continue
with the copy commands. `boot.py` deliberately keeps the serial REPL enabled
while adding the HID keyboard.

## Configuration

Edit `config.py` to change global brightness, long-press time, frame rate, or
pin assignments. Add or modify palettes and renderers in `themes.py`.
`GLOBAL_BRIGHTNESS` and `PARTY_BPM` are only the boot-time defaults — the
serial console's `brightness` and `bpm` commands can also change them live,
without reflashing, and those choices (along with the active theme) persist
across reboots via `user_config.py`.

## Verification

Host-side logic tests do not require a badge:

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q software testing tests
```

For physical diagnostics, see [`testing/README.md`](../testing/README.md).

The bundled `lib/usb/` modules come from the official MIT-licensed
`micropython-lib` project; its license is retained under `third_party/`.
