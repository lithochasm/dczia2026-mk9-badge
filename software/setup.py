import board
import busio
import neopixel
import keypad
import digitalio
import global_tools

# ---------------------------------------------------------------------------
# NeoPixels — 15 LEDs on GP21 (net "RGB" in the as-built PCB)
# LEDs 0-8:  key LEDs, row-major (left→right, top→bottom)
#            key_number from KeyMatrix = row*3+col = LED index
# LEDs 9-14: backlight LEDs, clockwise from top-right
# ---------------------------------------------------------------------------
NUM_PIXELS = 15
NUM_KEY_LEDS = 9
BACKLIGHT_START = 9

pixels = neopixel.NeoPixel(
    board.GP21,
    NUM_PIXELS,
    brightness=global_tools.current_brightness,
    auto_write=False,
    pixel_order=neopixel.GRB,
)

# ---------------------------------------------------------------------------
# Key matrix 3×3
# key_number = row * 3 + col
#   0=C0R0  1=C1R0  2=C2R0
#   3=C0R1  4=C1R1  5=C2R1
#   6=C0R2  7=C1R2  8=C2R2
# ---------------------------------------------------------------------------
row_pins = (board.GP27, board.GP26, board.GP16)
col_pins = (board.GP17, board.GP13, board.GP0)
# PCB path is column -> switch -> diode anode -> diode cathode -> row.
keys = keypad.KeyMatrix(row_pins, col_pins, columns_to_anodes=True)

# ---------------------------------------------------------------------------
# Accelerometer — I2C1, SDA=GP18, SCL=GP19
# ---------------------------------------------------------------------------
try:
    import adafruit_msa3xx
    _i2c_accel = busio.I2C(board.GP19, board.GP18)
    sensor = adafruit_msa3xx.MSA301(_i2c_accel)
    ACCEL_AVAILABLE = True
except Exception:
    sensor = None
    ACCEL_AVAILABLE = False

# ---------------------------------------------------------------------------
# SAO connector — I2C0, SDA=GP9, SCL=GP10
# ---------------------------------------------------------------------------
try:
    i2c_sao = busio.I2C(board.GP10, board.GP9)
    SAO_AVAILABLE = True
except Exception:
    i2c_sao = None
    SAO_AVAILABLE = False

# SAO GPIO pins (configured as inputs with pull-up; change per SAO use case)
# The generic Raspberry Pi Pico CircuitPython build exposes GPIO29 as A3
# (voltage-monitor input on a stock Pico), not as board.GP29.  On this custom
# RP2040 board the same physical pin is routed to SAO1 G1.
sao1_gpio1 = digitalio.DigitalInOut(board.A3)
sao1_gpio2 = digitalio.DigitalInOut(board.GP28)
sao2_gpio1 = digitalio.DigitalInOut(board.GP12)
sao2_gpio2 = digitalio.DigitalInOut(board.GP11)
for _pin in (sao1_gpio1, sao1_gpio2, sao2_gpio1, sao2_gpio2):
    _pin.switch_to_input(pull=digitalio.Pull.UP)

# ---------------------------------------------------------------------------
# LED spatial positions — (row, col) in grid units
# Used by the ripple engine to compute distances.
# Key LEDs occupy integer grid coordinates matching their physical layout.
# Backlight LEDs are placed around the perimeter (fractional/negative coords).
# ---------------------------------------------------------------------------
LED_POSITIONS = [
    (0.0,  0.0),  # LED 0  — C0R0 (top-left key)
    (0.0,  1.0),  # LED 1  — C1R0
    (0.0,  2.0),  # LED 2  — C2R0 (top-right key)
    (1.0,  0.0),  # LED 3  — C0R1
    (1.0,  1.0),  # LED 4  — C1R1 (centre key)
    (1.0,  2.0),  # LED 5  — C2R1
    (2.0,  0.0),  # LED 6  — C0R2 (bottom-left key)
    (2.0,  1.0),  # LED 7  — C1R2
    (2.0,  2.0),  # LED 8  — C2R2 (bottom-right key)
    (-0.7,  2.7), # LED 9  — backlight top-right
    ( 1.0,  3.2), # LED 10 — backlight right
    ( 2.7,  2.7), # LED 11 — backlight bottom-right
    ( 2.7, -0.7), # LED 12 — backlight bottom-left
    ( 1.0, -1.2), # LED 13 — backlight left
    (-0.7, -0.7), # LED 14 — backlight top-left
]
