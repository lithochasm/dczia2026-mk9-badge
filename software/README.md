# MK9 Badge — Firmware

CircuitPython firmware for the MK9 badge. State-machine architecture adapted from the [DCZIA Zippy Badge](https://github.com/dczia/zippy-badge).

---

## Hardware

### Microcontroller
RP2040-based board running CircuitPython 8+.

### Key Matrix (3×3)
Scanned with `keypad.KeyMatrix`. Physical layout:

```
C0R0  C1R0  C2R0        key# 0  key# 1  key# 2
C0R1  C1R1  C2R1   →    key# 3  key# 4  key# 5
C0R2  C1R2  C2R2        key# 6  key# 7  key# 8
```

| Signal | GPIO |
|--------|------|
| C0     | GP17 |
| C1     | GP13 |
| C2     | GP0  |
| R0     | GP27 |
| R1     | GP26 |
| R2     | GP16 |

### NeoPixel LEDs (15 total — GP21)

**Key LEDs 0–8** sit beneath each key. `LED index == key_number`.

**Backlight LEDs 9–14** ring the board perimeter (clockwise from top-right):

| Index | Position             |
|-------|----------------------|
| 9     | Top-right            |
| 10    | Right side           |
| 11    | Bottom-right         |
| 12    | Bottom-left          |
| 13    | Left side            |
| 14    | Top-left             |

### Accelerometer — I2C1
Adafruit MSA301-compatible device.

| Signal | GPIO |
|--------|------|
| SDA    | GP18 |
| SCL    | GP19 |

### SAO Connectors

**I2C0** (shared bus for both SAOs):

| Signal | GPIO |
|--------|------|
| SDA    | GP9  |
| SCL    | GP10 |

**SAO GPIO pins** (configured as inputs with pull-up by default):

| Pin     | GPIO |
|---------|------|
| SAO1 G1 | GP29 (`board.A3` in the generic Pico CircuitPython build) |
| SAO1 G2 | GP28 |
| SAO2 G1 | GP12 |
| SAO2 G2 | GP11 |

---

## Software Structure

```
software/
├── boot.py          — Runs before code.py; enables USB HID keyboard
├── code.py          — Entry point; creates and runs the state machine
├── state.py         — Base State and StateMachine classes
├── setup.py         — Hardware initialisation (pixels, keymatrix, I2C, accel)
├── color_tools.py   — Packed-color conversion and RGB blending helpers
├── global_tools.py  — Shared mutable globals (brightness, pattern index)
├── state_startup.py — Boot animation: diagonal colour wipe
└── state_badge.py   — Main badge mode: backgrounds, ripples, HID output
```

### State machine

`code.py` creates a `StateMachine` and registers two states:

| State     | Description |
|-----------|-------------|
| `startup` | Diagonal rainbow sweep across keys + backlights, then fades into badge mode. Any keypress skips straight to badge mode. |
| `badge`   | Continuous background pattern with ripple overlays on keypresses and NKRO USB keyboard output. |

### Badge mode details

**Background patterns** (shake the badge to cycle):

| # | Pattern       |
|---|---------------|
| 0 | Prism current — flowing spatial rainbow |
| 1 | Vaporwave — magenta/cyan plasma |
| 2 | Breathing rings — concentric color pulse |
| 3 | Starfield — decaying colored twinkles |
| 4 | Scanner — rotating, tilt-steered light bar |

**Key effects** — each keypress gets an immediate white-hot impact followed by an expanding spatial wavefront. Held keys retain a gentle pulse, and up to six simultaneous ripples are composited over the background.

**Accelerometer reactivity** — low-pass gravity gives the patterns smooth tilt control. Shake detection uses the high-pass motion component instead of total acceleration, so simply rotating the badge does not change modes. A successful mode change runs a short confirmation chase.

**Performance / power** — keyboard events are drained independently of the 40 fps renderer, while a 1 ms main-loop yield avoids needlessly pinning the RP2040 at full duty cycle. Background levels are deliberately restrained; reactive peaks get the brightness budget.

**USB keyboard** — when connected to a host, keypresses are sent as numpad keycodes with full N-key rollover:

```
7  8  9
4  5  6
1  2  3
```

---

## Required CircuitPython Libraries

Place in the `lib/` folder on CIRCUITPY:

| Library | Source |
|---------|--------|
| `neopixel.mpy` | Adafruit CircuitPython NeoPixel |
| `adafruit_msa3xx.mpy` | Adafruit CircuitPython MSA3XX |
| `adafruit_hid/` | Adafruit CircuitPython HID |

All available from the [Adafruit CircuitPython Bundle](https://github.com/adafruit/Adafruit_CircuitPython_Bundle/releases).

---

## Programming / Flashing

1. Hold BOOTSEL while plugging in the RP2040 — it mounts as `RPI-RP2`.
2. Drag the CircuitPython UF2 onto the drive. It reboots as `CIRCUITPY`.
3. Copy the `lib/` folder contents to `CIRCUITPY/lib/`.
4. Copy all `*.py` files from this directory to the root of `CIRCUITPY`.
5. The badge will restart and run `boot.py` then `code.py` automatically.

> **Note:** `boot.py` enables USB HID. After the first boot with `boot.py` present the drive will still appear as mass storage — both HID and storage are active simultaneously.

---

## Extending / Customising

- **Add a new background pattern** — add a `_bg_yourpattern()` method to `BadgeState`, increment `_NUM_PATTERNS`, and add a branch in `_render_background()`.
- **Remap keys** — edit `_KEY_CODES` in `state_badge.py`. Any `Keycode.*` constant works.
- **Change key colours** — edit `_KEY_COLORS` in `state_badge.py`.
- **Add an SAO** — use `i2c_sao` (already initialised) and the `sao*_gpio*` pins from `setup.py`.
- **Add a new state** — subclass `State`, implement `name`, `enter`, `exit`, `update`; register it with `machine.add_state()` in `code.py`.

## Host-side checks

The RGB helpers have small CPython tests (with `rainbowio` stubbed):

```sh
python -m unittest discover -s tests -v
python -m compileall -q software testing tests
```
