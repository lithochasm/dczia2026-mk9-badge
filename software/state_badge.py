"""Main badge mode: motion-reactive light art plus a USB numpad."""

import math
import random
import time
import supervisor

from color_tools import add, blend, scale, wheel
from setup import ACCEL_AVAILABLE, BACKLIGHT_START, LED_POSITIONS
from setup import NUM_KEY_LEDS, NUM_PIXELS, keys, pixels, sensor
from state import State
import global_tools


# ---------------------------------------------------------------------------
# USB HID keyboard (boot.py enables the keyboard device)
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


if HID_AVAILABLE:
    _KEY_CODES = (
        Keycode.KEYPAD_SEVEN, Keycode.KEYPAD_EIGHT, Keycode.KEYPAD_NINE,
        Keycode.KEYPAD_FOUR, Keycode.KEYPAD_FIVE, Keycode.KEYPAD_SIX,
        Keycode.KEYPAD_ONE, Keycode.KEYPAD_TWO, Keycode.KEYPAD_THREE,
    )
else:
    _KEY_CODES = (None,) * NUM_KEY_LEDS


# A distinct impact color for every key.  The center is intentionally offset
# from its neighbors so adjacent simultaneous ripples stay legible.
_KEY_COLORS = tuple(wheel(8 + key * 28) for key in range(NUM_KEY_LEDS))


# ---------------------------------------------------------------------------
# Animation geometry and tuning
# ---------------------------------------------------------------------------
_FRAME_TIME = 0.025             # 40 fps; input events are handled faster
_NUM_PATTERNS = 5
_MAX_RIPPLES = 6

_RIPPLE_SPEED = 2.5             # grid units / second
_RIPPLE_MAX_RADIUS = 4.25
_RIPPLE_WIDTH = 0.58

_SHAKE_THRESHOLD = 5.5          # high-pass acceleration, m/s^2
_SHAKE_COOLDOWN = 1.2
_GRAVITY_ALPHA = 0.12
_SHAKE_ALPHA = 0.25

_MODE_FLASH_DURATION = 0.65
_MODE_FLASH_ORDER = (14, 0, 1, 2, 9, 10, 5, 8, 11, 12, 7, 6, 13, 3, 4)

_VAPOR_PINK = (255, 20, 170)
_VAPOR_PURPLE = (92, 18, 220)
_VAPOR_CYAN = (0, 225, 255)
_STAR_BASE = (5, 1, 18)
_WHITE = (255, 255, 255)
_OFF = (0, 0, 0)


# setup.LED_POSITIONS stores (row, column).  Center the key grid around zero
# for wave, angle, and scanner calculations.
_X = tuple(position[1] - 1.0 for position in LED_POSITIONS)
_Y = tuple(position[0] - 1.0 for position in LED_POSITIONS)
_RADIUS = tuple(math.sqrt(_X[i] ** 2 + _Y[i] ** 2)
                for i in range(NUM_PIXELS))


def _make_distance_map():
    distances = []
    for origin in range(NUM_KEY_LEDS):
        row = []
        for led in range(NUM_PIXELS):
            dx = _X[led] - _X[origin]
            dy = _Y[led] - _Y[origin]
            row.append(math.sqrt(dx * dx + dy * dy))
        distances.append(tuple(row))
    return tuple(distances)


_DISTANCE = _make_distance_map()


def _clamp(value, low, high):
    if value < low:
        return low
    if value > high:
        return high
    return value


def _usb_connected():
    """Work on current CircuitPython and fail open on older releases."""
    try:
        return supervisor.runtime.usb_connected
    except AttributeError:
        return True


class _Ripple:
    __slots__ = ("origin", "color", "start_time")

    def __init__(self, origin, color, now):
        self.origin = origin
        self.color = color
        self.start_time = now

    def age(self, now):
        return now - self.start_time

    def is_done(self, now):
        return self.age(now) * _RIPPLE_SPEED > _RIPPLE_MAX_RADIUS

    def brightness_for(self, led, now):
        radius = self.age(now) * _RIPPLE_SPEED
        difference = abs(_DISTANCE[self.origin][led] - radius)
        if difference >= _RIPPLE_WIDTH:
            return 0.0
        edge = 1.0 - difference / _RIPPLE_WIDTH
        life = 1.0 - radius / _RIPPLE_MAX_RADIUS
        return edge * life * life


class BadgeState(State):

    @property
    def name(self):
        return "badge"

    def __init__(self):
        self.pattern = int(global_tools.pattern_index) % _NUM_PATTERNS
        self.ripples = []
        self.held = [False] * NUM_KEY_LEDS
        self.frame = [_OFF] * NUM_PIXELS
        self.sparkle = [0.0] * NUM_PIXELS

        self.last_frame = 0.0
        self.anim_time = 0.0
        self.mode_flash_start = -10.0

        self.motion_ready = False
        self.gravity_x = 0.0
        self.gravity_y = 0.0
        self.gravity_z = 9.81
        self.tilt_x = 0.0
        self.tilt_y = 0.0
        self.shake_energy = 0.0
        self.last_shake = 0.0

    def enter(self, machine):
        now = time.monotonic()
        self.pattern = int(global_tools.pattern_index) % _NUM_PATTERNS
        self.ripples = []
        for key in range(NUM_KEY_LEDS):
            self.held[key] = False
        for led in range(NUM_PIXELS):
            self.sparkle[led] = 0.0
        self.last_frame = now
        self.anim_time = 0.0
        self.motion_ready = False
        self.shake_energy = 0.0
        pixels.fill(_OFF)
        pixels.show()
        State.enter(self, machine)

    def exit(self, machine):
        if HID_AVAILABLE and _keyboard:
            try:
                _keyboard.release_all()
            except Exception:
                pass
        pixels.fill(_OFF)
        pixels.show()
        State.exit(self, machine)

    # ------------------------------------------------------------------
    # Input and motion
    # ------------------------------------------------------------------

    def _start_ripple(self, key, now):
        if len(self.ripples) >= _MAX_RIPPLES:
            del self.ripples[0]
        self.ripples.append(_Ripple(key, _KEY_COLORS[key], now))

    def _handle_key_events(self, now):
        # Drain the queue every pass.  HID latency is no longer tied to the
        # animation frame rate and fast chords cannot build up stale events.
        while True:
            event = keys.events.get()
            if event is None:
                return

            key = event.key_number
            if key < 0 or key >= NUM_KEY_LEDS:
                continue

            if event.pressed:
                self.held[key] = True
                self._start_ripple(key, now)
                if HID_AVAILABLE and _usb_connected():
                    try:
                        _keyboard.press(_KEY_CODES[key])
                    except Exception:
                        pass
            elif event.released:
                self.held[key] = False
                if HID_AVAILABLE and _usb_connected():
                    try:
                        _keyboard.release(_KEY_CODES[key])
                    except Exception:
                        pass

    def _read_accel(self):
        if not ACCEL_AVAILABLE or sensor is None:
            return None
        try:
            return sensor.acceleration
        except Exception:
            return None

    def _cycle_pattern(self, now):
        self.pattern = (self.pattern + 1) % _NUM_PATTERNS
        global_tools.pattern_index = self.pattern
        self.last_shake = now
        self.mode_flash_start = now
        self.shake_energy = 0.0
        for led in range(NUM_PIXELS):
            self.sparkle[led] = 0.0

    def _update_motion(self, now):
        acceleration = self._read_accel()
        if acceleration is None:
            return
        ax, ay, az = acceleration

        if not self.motion_ready:
            self.gravity_x = ax
            self.gravity_y = ay
            self.gravity_z = az
            self.motion_ready = True
            return

        # The low-pass component estimates gravity for smooth tilt control.
        # The residual is orientation-independent motion used for shake
        # detection, unlike a threshold on total acceleration (which includes
        # Earth's 9.81 m/s^2 and produces false positives).
        dx = ax - self.gravity_x
        dy = ay - self.gravity_y
        dz = az - self.gravity_z
        self.gravity_x += dx * _GRAVITY_ALPHA
        self.gravity_y += dy * _GRAVITY_ALPHA
        self.gravity_z += dz * _GRAVITY_ALPHA

        residual = math.sqrt(dx * dx + dy * dy + dz * dz)
        self.shake_energy += (residual - self.shake_energy) * _SHAKE_ALPHA

        target_x = _clamp(self.gravity_x / 9.81, -1.0, 1.0)
        target_y = _clamp(self.gravity_y / 9.81, -1.0, 1.0)
        self.tilt_x += (target_x - self.tilt_x) * 0.18
        self.tilt_y += (target_y - self.tilt_y) * 0.18

        if (self.shake_energy > _SHAKE_THRESHOLD and
                now - self.last_shake > _SHAKE_COOLDOWN):
            self._cycle_pattern(now)

    # ------------------------------------------------------------------
    # Background patterns
    # ------------------------------------------------------------------

    def _bg_prism(self):
        tilt_hue = (self.tilt_x * 38.0) + (self.tilt_y * 24.0)
        for led in range(NUM_PIXELS):
            wave = (math.sin(self.anim_time * 1.7 + _X[led] * 1.35 -
                             _Y[led] * 0.9) + 1.0) * 0.5
            level = 0.10 + wave * 0.24
            if led >= BACKLIGHT_START:
                level += 0.07
            hue = (self.anim_time * 30.0 + _X[led] * 29.0 +
                   _Y[led] * 43.0 + tilt_hue)
            self.frame[led] = wheel(hue, level)

    def _bg_vaporwave(self):
        for led in range(NUM_PIXELS):
            diagonal = (math.sin(self.anim_time * 1.35 + _X[led] * 1.15 +
                                 _Y[led] * 0.72 + self.tilt_x) + 1.0) * 0.5
            horizon = (math.sin(self.anim_time * 0.7 - _Y[led] * 1.8 +
                                self.tilt_y * 1.4) + 1.0) * 0.5
            color = blend(_VAPOR_PINK, _VAPOR_CYAN, diagonal)
            color = blend(color, _VAPOR_PURPLE, horizon * 0.42)
            level = 0.19 + 0.13 * (1.0 - horizon)
            if led >= BACKLIGHT_START:
                level += 0.08
            self.frame[led] = scale(color, level)

    def _bg_breathe(self):
        hue_base = self.anim_time * 9.0 + self.tilt_x * 45.0
        for led in range(NUM_PIXELS):
            pulse = (math.sin(self.anim_time * 2.05 - _RADIUS[led] * 0.92 +
                              self.tilt_y * 0.8) + 1.0) * 0.5
            # Squaring gives the pulse a crisp crest and a long, calm tail.
            level = 0.055 + pulse * pulse * 0.34
            if led >= BACKLIGHT_START:
                level += 0.055
            self.frame[led] = wheel(hue_base + _RADIUS[led] * 23.0,
                                    level)

    def _bg_starfield(self, delta):
        decay = delta * 1.65
        for led in range(NUM_PIXELS):
            self.sparkle[led] = max(0.0, self.sparkle[led] - decay)

        if random.random() < min(1.0, delta * 10.0):
            self.sparkle[random.randint(0, NUM_PIXELS - 1)] = 1.0

        drift = self.anim_time * 12.0 + self.tilt_x * 30.0
        for led in range(NUM_PIXELS):
            star = self.sparkle[led]
            color = add(_STAR_BASE, wheel(155 + led * 11 + drift),
                        star * star * 0.78)
            if led >= BACKLIGHT_START:
                color = add(color, _VAPOR_PURPLE, 0.045)
            self.frame[led] = color

    def _bg_scanner(self):
        cycle = (self.anim_time * 0.52) % 2.0
        if cycle < 1.0:
            position = -2.25 + cycle * 4.5
        else:
            position = 2.25 - (cycle - 1.0) * 4.5

        angle = self.anim_time * 0.22 + self.tilt_x * 0.9
        direction_x = math.cos(angle)
        direction_y = math.sin(angle + self.tilt_y * 0.65)
        scanner_color = wheel(18 + self.anim_time * 18.0)
        base_color = wheel(155 + self.anim_time * 3.0, 0.035)

        for led in range(NUM_PIXELS):
            projection = _X[led] * direction_x + _Y[led] * direction_y
            distance = abs(projection - position)
            beam = max(0.0, 1.0 - distance / 0.58)
            glow = max(0.0, 1.0 - distance / 1.35) * 0.11
            color = add(base_color, scanner_color, glow + beam * 0.68)
            self.frame[led] = color

    def _render_background(self, delta):
        if self.pattern == 0:
            self._bg_prism()
        elif self.pattern == 1:
            self._bg_vaporwave()
        elif self.pattern == 2:
            self._bg_breathe()
        elif self.pattern == 3:
            self._bg_starfield(delta)
        else:
            self._bg_scanner()

    # ------------------------------------------------------------------
    # Reactive overlays
    # ------------------------------------------------------------------

    def _apply_ripples(self, now):
        for ripple in self.ripples:
            age = ripple.age(now)
            for led in range(NUM_PIXELS):
                strength = ripple.brightness_for(led, now)
                if strength > 0.008:
                    self.frame[led] = add(self.frame[led], ripple.color,
                                          strength * 0.92)

            # A short white-hot impact makes even a quick tap feel immediate.
            if age < 0.16:
                impact = 1.0 - age / 0.16
                hot = blend(ripple.color, _WHITE, 0.62)
                origin = ripple.origin
                self.frame[origin] = add(self.frame[origin], hot, impact)

    def _apply_held_keys(self):
        for key in range(NUM_KEY_LEDS):
            if not self.held[key]:
                continue
            pulse = (math.sin(self.anim_time * 8.5 + key * 0.7) + 1.0) * 0.5
            glow = blend(_KEY_COLORS[key], _WHITE, 0.34)
            self.frame[key] = add(self.frame[key], glow, 0.16 + pulse * 0.20)

    def _apply_mode_flash(self, now):
        age = now - self.mode_flash_start
        if age < 0.0 or age >= _MODE_FLASH_DURATION:
            return

        head = (age / _MODE_FLASH_DURATION) * (len(_MODE_FLASH_ORDER) + 3)
        color = wheel(self.pattern * 49 + 16)
        fade = 1.0 - age / _MODE_FLASH_DURATION * 0.35
        for order, led in enumerate(_MODE_FLASH_ORDER):
            distance = abs(order - head)
            strength = max(0.0, 1.0 - distance / 2.6) * fade
            if strength > 0.01:
                self.frame[led] = add(self.frame[led], color, strength)

    def _show(self):
        for led in range(NUM_PIXELS):
            pixels[led] = self.frame[led]
        pixels.show()

    # ------------------------------------------------------------------
    # Main update
    # ------------------------------------------------------------------

    def update(self, machine):
        now = time.monotonic()

        # Run input at loop speed instead of waiting for the next LED frame.
        self._handle_key_events(now)

        delta = now - self.last_frame
        if delta < _FRAME_TIME:
            return
        self.last_frame = now
        delta = min(delta, 0.10)
        self.anim_time += delta

        if ACCEL_AVAILABLE:
            self._update_motion(now)

        self.ripples = [ripple for ripple in self.ripples
                        if not ripple.is_done(now)]

        self._render_background(delta)
        self._apply_ripples(now)
        self._apply_held_keys()
        self._apply_mode_flash(now)
        self._show()
