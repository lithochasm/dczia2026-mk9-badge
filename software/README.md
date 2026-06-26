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

### NeoPixel LEDs (15 total — GP22)

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
| SAO1 G1 | GP29 |
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
| 0 | Rainbow wave  |
| 1 | Breathing pulse |
| 2 | Sparkle / twinkle |

**Ripple effect** — each keypress launches an expanding wavefront from that key's LED position. Up to N simultaneous ripples are supported. Each key has a unique colour derived from its position on the colour wheel.

**Accelerometer reactivity** — tilt shifts the hue offset of the background pattern continuously. A vigorous shake (>16 m/s²) cycles to the next pattern after a 2-second cooldown.

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

- **Add a new background pattern** — add a `_bg_yourpattern()` method to `BadgeState`, increment `_NUM_PATTERNS`, and add an `elif` branch in `update()`.
- **Remap keys** — edit `_KEY_CODES` in `state_badge.py`. Any `Keycode.*` constant works.
- **Change key colours** — edit `_KEY_COLORS` in `state_badge.py`.
- **Add an SAO** — use `i2c_sao` (already initialised) and the `sao*_gpio*` pins from `setup.py`.
- **Add a new state** — subclass `State`, implement `name`, `enter`, `exit`, `update`; register it with `machine.add_state()` in `code.py`.
