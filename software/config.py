"""Hardware map and user-tunable settings for the MK9 badge."""

# As-built RP2040 wiring.
PIXEL_PIN = 21
NUM_PIXELS = 15
NUM_KEY_LEDS = 9
BACKLIGHT_START = 9

ROW_PINS = (27, 26, 16)
COLUMN_PINS = (17, 13, 0)

ACCEL_I2C_ID = 1
ACCEL_SDA_PIN = 18
ACCEL_SCL_PIN = 19

# The SAO pins are not a valid hardware-I2C pair on RP2040, so hardware.py
# intentionally creates a SoftI2C bus for them.
SAO_SDA_PIN = 9
SAO_SCL_PIN = 10
SAO_GPIO_PINS = (29, 28, 12, 11)

# Animation/input tuning.
GLOBAL_BRIGHTNESS = 0.30
FRAME_MS = 25
KEY_SCAN_MS = 4
DEBOUNCE_SCANS = 4
LONG_PRESS_MS = 750
STARTUP_MS = 3200

# key number -> USB keypad key code (7 8 9 / 4 5 6 / 1 2 3)
NUMPAD_CODES = (95, 96, 97, 92, 93, 94, 89, 90, 91)

THEME_NAMES = (
    "Prism",
    "Vaporwave",
    "Deep Ocean",
    "Ember",
    "Matrix",
    "Ultraviolet",
    "Sunset",
    "Glacier",
    "Moonlight",
)

# (row, column), including the six perimeter LEDs.
LED_POSITIONS = (
    (0.0, 0.0),
    (0.0, 1.0),
    (0.0, 2.0),
    (1.0, 0.0),
    (1.0, 1.0),
    (1.0, 2.0),
    (2.0, 0.0),
    (2.0, 1.0),
    (2.0, 2.0),
    (-0.7, 2.7),
    (1.0, 3.2),
    (2.7, 2.7),
    (2.7, -0.7),
    (1.0, -1.2),
    (-0.7, -0.7),
)
