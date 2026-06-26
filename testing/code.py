"""
MK9 Badge Hardware Tester

LED test: all 15 LEDs cycle red → green → blue.
  - Each color holds for 0.5 s, then a wipe sweeps the next color
    across in 0.5 s — 1 second total per color.
  - Tilt the badge on X or Y axis to change the wipe direction.

Key test: press any key to fast-flash that key's LED white at 10 Hz.
  All 9 keys can be held simultaneously (NKRO test).

Accelerometer test: tilt X/Y changes the wipe direction live.
  Tilt right  → left-to-right wipe
  Tilt left   → right-to-left wipe
  Tilt toward → top-to-bottom wipe
  Tilt away   → bottom-to-top wipe
  Flat        → keeps the last direction
"""

import board
import busio
import neopixel
import keypad
import time

# ---------------------------------------------------------------------------
# Hardware
# ---------------------------------------------------------------------------
NUM_PIXELS = 15

pixels = neopixel.NeoPixel(
    board.GP22, NUM_PIXELS,
    brightness=0.5,
    auto_write=False,
    pixel_order=neopixel.GRB,
)

row_pins = (board.GP27, board.GP26, board.GP16)
col_pins = (board.GP17, board.GP13, board.GP0)
keys = keypad.KeyMatrix(row_pins, col_pins, columns_to_anodes=False)

try:
    import adafruit_msa3xx
    _i2c = busio.I2C(board.GP19, board.GP18)
    sensor = adafruit_msa3xx.MSA301(_i2c)
    ACCEL_OK = True
except Exception:
    sensor = None
    ACCEL_OK = False

# ---------------------------------------------------------------------------
# Wipe groups — LED indices ordered by spatial position
#
# Key LED layout (index = row*3 + col):
#   0  1  2       col: 0.0  1.0  2.0
#   3  4  5       row: 0.0  1.0  2.0
#   6  7  8
#
# Backlight LED positions (row, col):
#   9  = (-0.7,  2.7)  top-right
#   10 = ( 1.0,  3.2)  right
#   11 = ( 2.7,  2.7)  bottom-right
#   12 = ( 2.7, -0.7)  bottom-left
#   13 = ( 1.0, -1.2)  left
#   14 = (-0.7, -0.7)  top-left
# ---------------------------------------------------------------------------
_WIPE = {
    'LR': [                     # left → right (col ascending)
        [13, 14, 12],           # left backlights
        [0, 3, 6],              # key col 0
        [1, 4, 7],              # key col 1
        [2, 5, 8],              # key col 2
        [9, 11, 10],            # right backlights
    ],
    'RL': [                     # right → left
        [9, 11, 10],
        [2, 5, 8],
        [1, 4, 7],
        [0, 3, 6],
        [13, 14, 12],
    ],
    'TB': [                     # top → bottom (row ascending)
        [9, 14],                # top backlights
        [0, 1, 2],              # key row 0
        [3, 4, 5, 10, 13],      # key row 1 + side backlights
        [6, 7, 8],              # key row 2
        [11, 12],               # bottom backlights
    ],
    'BT': [                     # bottom → top
        [11, 12],
        [6, 7, 8],
        [3, 4, 5, 10, 13],
        [0, 1, 2],
        [9, 14],
    ],
}

COLORS = [
    (255,   0,   0),   # red
    (  0, 255,   0),   # green
    (  0,   0, 255),   # blue
]

HOLD_TIME      = 0.5          # seconds each color is held solid
WIPE_STEP_TIME = 0.10         # 5 groups × 0.10 s = 0.5 s wipe
FLASH_HALF     = 0.05         # 10 Hz white flash (50 ms half-period)
ACCEL_DEAD     = 1.0          # m/s² — below this on both axes = "flat"

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
current_color = 0
next_color    = 1
wipe_dir      = 'LR'

# "hold" → all LEDs show current_color; "wipe" → sweeping next_color in
phase       = 'hold'
phase_start = time.monotonic()
wipe_step   = 0

# Per-LED colour buffer (modified as the wipe advances)
led_buf = [COLORS[current_color]] * NUM_PIXELS

key_held   = [False] * 9
flash_on   = True
last_flash = time.monotonic()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_direction():
    """Return 'LR'/'RL'/'TB'/'BT' from accel tilt, or None if flat/unavailable."""
    if not ACCEL_OK:
        return None
    try:
        ax, ay, _ = sensor.acceleration
    except Exception:
        return None
    if abs(ax) < ACCEL_DEAD and abs(ay) < ACCEL_DEAD:
        return None
    if abs(ax) >= abs(ay):
        return 'LR' if ax > 0 else 'RL'
    return 'TB' if ay > 0 else 'BT'


def _start_wipe():
    """Begin a new wipe: sample accel direction and reset wipe state."""
    global wipe_dir, wipe_step, phase, phase_start
    direction = _read_direction()
    if direction:
        wipe_dir = direction
    wipe_step   = 0
    phase       = 'wipe'
    phase_start = time.monotonic()


def _finish_wipe():
    """Wipe complete: advance colour cycle and enter hold phase."""
    global current_color, next_color, led_buf, phase, phase_start
    current_color = next_color
    next_color    = (next_color + 1) % len(COLORS)
    led_buf       = [COLORS[current_color]] * NUM_PIXELS
    phase         = 'hold'
    phase_start   = time.monotonic()


# Prime display
pixels.fill(COLORS[current_color])
pixels.show()

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
while True:
    now = time.monotonic()

    # --- Phase logic ---
    if phase == 'hold':
        if now - phase_start >= HOLD_TIME:
            _start_wipe()

    elif phase == 'wipe':
        elapsed_in_phase = now - phase_start
        target_step = int(elapsed_in_phase / WIPE_STEP_TIME)

        # Apply any new steps that are due
        while wipe_step <= target_step and wipe_step < len(_WIPE[wipe_dir]):
            for led in _WIPE[wipe_dir][wipe_step]:
                led_buf[led] = COLORS[next_color]
            wipe_step += 1

        if wipe_step >= len(_WIPE[wipe_dir]):
            _finish_wipe()

    # --- Key events ---
    event = keys.events.get()
    if event:
        if event.pressed:
            key_held[event.key_number] = True
        elif event.released:
            key_held[event.key_number] = False

    # --- 10 Hz flash toggle ---
    if now - last_flash >= FLASH_HALF:
        flash_on   = not flash_on
        last_flash = now

    # --- Render ---
    for i in range(NUM_PIXELS):
        pixels[i] = led_buf[i]

    # Overlay: held keys fast-flash white
    for k in range(9):
        if key_held[k]:
            pixels[k] = (255, 255, 255) if flash_on else (0, 0, 0)

    pixels.show()
