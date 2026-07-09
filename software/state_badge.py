import time
import math
import random
import supervisor
from rainbowio import colorwheel
from setup import pixels, NUM_PIXELS, BACKLIGHT_START, LED_POSITIONS
from setup import keys, sensor, ACCEL_AVAILABLE
from state import State
import global_tools

# ---------------------------------------------------------------------------
# USB HID keyboard (requires boot.py to have enabled usb_hid)
# ---------------------------------------------------------------------------
try:
    import usb_hid
    from adafruit_hid.keyboard import Keyboard
    from adafruit_hid.keycode import Keycode
    _keyboard = Keyboard(usb_hid.devices)
    HID_AVAILABLE = True
except Exception:
    _keyboard = None
    HID_AVAILABLE = False

# Numpad layout — top-left key sends 7, bottom-right sends 3
if HID_AVAILABLE:
    _KEY_CODES = [
        Keycode.KEYPAD_SEVEN, Keycode.KEYPAD_EIGHT, Keycode.KEYPAD_NINE,
        Keycode.KEYPAD_FOUR,  Keycode.KEYPAD_FIVE,  Keycode.KEYPAD_SIX,
        Keycode.KEYPAD_ONE,   Keycode.KEYPAD_TWO,   Keycode.KEYPAD_THREE,
    ]
else:
    _KEY_CODES = [None] * 9

# One vibrant colour per key, evenly spaced on the colour wheel
_KEY_COLORS = [colorwheel(i * 28) for i in range(9)]

# ---------------------------------------------------------------------------
# Ripple parameters
# ---------------------------------------------------------------------------
_RIPPLE_SPEED  = 1.8   # grid units per second
_RIPPLE_MAX_R  = 4.5   # radius at which a ripple disappears
_RIPPLE_WIDTH  = 0.7   # wavefront half-thickness

_NUM_PATTERNS  = 3
_FRAME_TIME    = 0.03  # ~33 fps target
_SHAKE_THRESH  = 16.0  # m/s² total acceleration to trigger pattern change
_SHAKE_COOLDOWN = 2.0  # seconds between shake-triggered pattern changes


class _Ripple:
    __slots__ = ("origin", "color", "start_time")

    def __init__(self, origin_led, color):
        self.origin = origin_led
        self.color = color
        self.start_time = time.monotonic()

    def radius(self):
        return (time.monotonic() - self.start_time) * _RIPPLE_SPEED

    def is_done(self):
        return self.radius() > _RIPPLE_MAX_R

    def brightness_for(self, led_index):
        r = self.radius()
        ox, oy = LED_POSITIONS[self.origin]
        lx, ly = LED_POSITIONS[led_index]
        dist = ((lx - ox) ** 2 + (ly - oy) ** 2) ** 0.5
        diff = abs(dist - r)
        if diff >= _RIPPLE_WIDTH:
            return 0.0
        b = (1.0 - diff / _RIPPLE_WIDTH) * (1.0 - r / _RIPPLE_MAX_R)
        return max(0.0, b)


class BadgeState(State):

    @property
    def name(self):
        return "badge"

    def __init__(self):
        self.ripples = []
        self.pattern = 0
        self.last_frame = 0.0
        self.last_shake = 0.0

        # Shared animation offset (drives waves and hue shifts)
        self.bg_offset = 0.0
        self.bg_hue = 0

        # Sparkle per-LED decay values
        self.sparkle = [0.0] * NUM_PIXELS

        # Accelerometer influence on colour offset
        self.accel_hue_shift = 0

    def enter(self, machine):
        self.ripples = []
        self.bg_offset = 0.0
        self.last_frame = time.monotonic()
        pixels.fill((0, 0, 0))
        pixels.show()
        State.enter(self, machine)

    def exit(self, machine):
        if HID_AVAILABLE and _keyboard:
            try:
                _keyboard.release_all()
            except Exception:
                pass
        pixels.fill((0, 0, 0))
        pixels.show()
        State.exit(self, machine)

    # ------------------------------------------------------------------
    # Accelerometer helpers
    # ------------------------------------------------------------------

    def _read_accel(self):
        if not ACCEL_AVAILABLE or sensor is None:
            return 0.0, 0.0, 0.0
        try:
            return sensor.acceleration
        except Exception:
            return 0.0, 0.0, 0.0

    def _update_accel(self, now):
        ax, ay, az = self._read_accel()
        total = (ax ** 2 + ay ** 2 + az ** 2) ** 0.5

        # Shift hue based on tilt direction
        if abs(ax) > abs(ay):
            self.accel_hue_shift = int((ax / 10.0) * 40) % 256
        else:
            self.accel_hue_shift = int((ay / 10.0) * 40) % 256

        # Vigorous shake → cycle to next pattern
        if total > _SHAKE_THRESH and (now - self.last_shake) > _SHAKE_COOLDOWN:
            self.pattern = (self.pattern + 1) % _NUM_PATTERNS
            self.last_shake = now

    # ------------------------------------------------------------------
    # Background patterns  (write directly into pixels buffer)
    # ------------------------------------------------------------------

    def _bg_rainbow_wave(self, delta):
        self.bg_offset = (self.bg_offset + delta * 90) % 256
        for i in range(NUM_PIXELS):
            if i < 9:
                row = i // 3
                col = i % 3
                phase = row * 45 + col * 30
            else:
                # Backlight LEDs get their own band offset
                phase = (i - BACKLIGHT_START) * 40 + 128
            hue = int((phase + self.bg_offset + self.accel_hue_shift) % 256)
            pixels[i] = colorwheel(hue)

    def _bg_breathing(self, delta):
        self.bg_offset += delta * 1.8
        self.bg_hue = (self.bg_hue + int(delta * 15) + 1) % 256
        intensity = (math.sin(self.bg_offset) + 1.0) / 2.0
        base = colorwheel((self.bg_hue + self.accel_hue_shift) % 256)
        color = tuple(int(c * intensity) for c in base)
        # Key LEDs breathe together; backlight LEDs breathe slightly offset
        for i in range(9):
            pixels[i] = color
        bl_intensity = (math.sin(self.bg_offset + 0.8) + 1.0) / 2.0
        bl_color = tuple(int(c * bl_intensity) for c in base)
        for i in range(BACKLIGHT_START, NUM_PIXELS):
            pixels[i] = bl_color

    def _bg_sparkle(self, delta):
        # Decay existing sparkles
        for i in range(NUM_PIXELS):
            self.sparkle[i] = max(0.0, self.sparkle[i] - delta * 2.8)
        # Randomly ignite new ones
        if random.random() < delta * 14:
            self.sparkle[random.randint(0, NUM_PIXELS - 1)] = 1.0
        self.bg_hue = (self.bg_hue + int(delta * 25) + 1) % 256
        for i in range(NUM_PIXELS):
            v = self.sparkle[i]
            if v > 0.005:
                hue = (self.bg_hue + i * 19 + self.accel_hue_shift) % 256
                c = colorwheel(hue)
                pixels[i] = tuple(int(ch * v) for ch in c)
            else:
                pixels[i] = (0, 0, 0)

    # ------------------------------------------------------------------
    # Ripple overlay (additive blend on top of background)
    # ------------------------------------------------------------------

    def _apply_ripples(self):
        for ripple in self.ripples:
            for i in range(NUM_PIXELS):
                b = ripple.brightness_for(i)
                if b < 0.01:
                    continue
                rc, gc, bc = ripple.color
                pr, pg, pb = pixels[i]
                pixels[i] = (
                    min(255, pr + int(rc * b)),
                    min(255, pg + int(gc * b)),
                    min(255, pb + int(bc * b)),
                )

    # ------------------------------------------------------------------
    # Main update
    # ------------------------------------------------------------------

    def update(self, machine):
        now = time.monotonic()
        delta = now - self.last_frame
        if delta < _FRAME_TIME:
            return
        self.last_frame = now

        # Clean up finished ripples
        self.ripples = [r for r in self.ripples if not r.is_done()]

        # Accelerometer reactivity
        if ACCEL_AVAILABLE:
            self._update_accel(now)

        # Key events
        event = keys.events.get()
        if event:
            key = event.key_number
            if event.pressed:
                self.ripples.append(_Ripple(key, _KEY_COLORS[key]))
                if HID_AVAILABLE and supervisor.runtime.usb_connected:
                    try:
                        _keyboard.press(_KEY_CODES[key])
                    except Exception:
                        pass
            elif event.released:
                if HID_AVAILABLE and supervisor.runtime.usb_connected:
                    try:
                        _keyboard.release(_KEY_CODES[key])
                    except Exception:
                        pass

        # Render background
        if self.pattern == 0:
            self._bg_rainbow_wave(delta)
        elif self.pattern == 1:
            self._bg_breathing(delta)
        elif self.pattern == 2:
            self._bg_sparkle(delta)

        # Overlay ripples
        self._apply_ripples()

        pixels.show()
