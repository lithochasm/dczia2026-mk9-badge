"""Interactive lighting, key handling, and motion behavior for the MK9."""

import math
import random
import time

from color_tools import add, blend, wheel
from config import (
    DEFAULT_THEME,
    FRAME_MS,
    LED_POSITIONS,
    LONG_PRESS_MS,
    NUM_KEY_LEDS,
    NUM_PIXELS,
    NUMPAD_CODES,
    PARTY_BPM,
    PARTY_BPM_DOWN_KEY,
    PARTY_BPM_MAX,
    PARTY_BPM_MIN,
    PARTY_BPM_STEP,
    PARTY_BPM_UP_KEY,
    PARTY_MODE_THEME,
    PARTY_TAP_HISTORY,
    PARTY_TAP_TEMPO_KEY,
    PARTY_TAP_TIMEOUT_MS,
    STARTUP_MS,
    THEME_NAMES,
)
from serial_menu import SerialMenu
from themes import render_startup, render_theme, theme_accent
import usb_keyboard
import user_config

_WHITE = (255, 255, 255)
_FLASH_ORDER = (14, 0, 1, 2, 9, 10, 5, 8, 11, 12, 7, 6, 13, 3, 4)
_RIPPLE_SPEED = 2.5
_RIPPLE_WIDTH = 0.58
_RIPPLE_MAX_RADIUS = 4.25
_ROTATION_MIN_ACCEL_SQUARED = 4.0
_POOL_LEVEL = 1.0
_MOTION_RESPONSE = 0.30
_POOL_SPRING = 0.16
_POOL_DAMPING = 0.78
_POOL_Z_FULL = 7.0
_POOL_Z_OFF = 8.6
_MOTION_HUE_BLEND = 0.16
_MOTION_HUE_SPEED_BOOST = 0.08
_PI = 3.14159265
_TAU = 6.28318531
_FRAME_STEP_SCALE = 1.0 / FRAME_MS
_WAVE_CYCLE_SCALE = 1.0 / _TAU
_WAVE_CYCLE_OFFSET = 16.0

_X = tuple(position[1] - 1.0 for position in LED_POSITIONS)
_Y = tuple(position[0] - 1.0 for position in LED_POSITIONS)
_POOL_X_256 = tuple(int(value * (256.0 / 2.25)) for value in _X)
_POOL_Y_256 = tuple(int(value * (256.0 / 2.25)) for value in _Y)


def _distance_map():
    result = []
    for origin in range(NUM_KEY_LEDS):
        row = []
        for led in range(NUM_PIXELS):
            dx = _X[led] - _X[origin]
            dy = _Y[led] - _Y[origin]
            row.append(math.sqrt(dx * dx + dy * dy))
        result.append(tuple(row))
    return tuple(result)


_DISTANCE = _distance_map()


class Badge:
    def __init__(self, hardware, serial_stream=None):
        self.hardware = hardware
        self.serial_menu = SerialMenu(self, hardware, serial_stream)
        self.frame = hardware.frame
        self.theme = DEFAULT_THEME
        self.party_bpm = PARTY_BPM
        self.tap_times = []
        self.start_ms = time.ticks_ms()
        self.last_frame_ms = time.ticks_add(self.start_ms, -FRAME_MS)
        self.animation_seconds = 0.0

        self.held = [False] * NUM_KEY_LEDS
        self.press_ms = [0] * NUM_KEY_LEDS
        self.long_fired = [False] * NUM_KEY_LEDS
        self.ripples = []
        self.sparkle = [0.0] * NUM_PIXELS

        self.gravity_x = 0.0
        self.gravity_y = 0.0
        self.gravity_z = 9.80665
        self.motion_ready = False
        self.pool_x = 0.0
        self.pool_y = 0.0
        self.pool_angle = 0.0
        self.pool_angular_velocity = 0.0
        self.pool_direction_ready = False
        self.pool_strength = 0.0

        self.flash_start_ms = time.ticks_add(self.start_ms, -2000)
        self.flash_origin = 0

    @property
    def theme_name(self):
        return THEME_NAMES[self.theme]

    def _press(self, key, now_ms):
        self.held[key] = True
        self.press_ms[key] = now_ms
        self.long_fired[key] = False
        if len(self.ripples) >= 6:
            del self.ripples[0]
        self.ripples.append((key, now_ms, theme_accent(key)))
        if self.theme == PARTY_MODE_THEME and key == PARTY_TAP_TEMPO_KEY:
            self._tap_tempo(now_ms)

    def _release(self, key):
        self.held[key] = False
        if self.long_fired[key]:
            return
        # Party Mode is a flashy visual effect, not a typing surface -- don't
        # let casual key presses leak numpad keystrokes into whatever has
        # focus on the host while it's active. Instead, two of its otherwise-
        # idle keys become a tempo control.
        if self.theme == PARTY_MODE_THEME:
            if key == PARTY_BPM_DOWN_KEY:
                self._adjust_party_bpm(-PARTY_BPM_STEP)
            elif key == PARTY_BPM_UP_KEY:
                self._adjust_party_bpm(PARTY_BPM_STEP)
            return
        usb_keyboard.tap(NUMPAD_CODES[key])

    def _adjust_party_bpm(self, delta):
        self.party_bpm = max(PARTY_BPM_MIN, min(PARTY_BPM_MAX, self.party_bpm + delta))
        user_config.save(self.theme, self.hardware.brightness, self.party_bpm)

    def _tap_tempo(self, now_ms):
        if self.tap_times and time.ticks_diff(now_ms, self.tap_times[-1]) > PARTY_TAP_TIMEOUT_MS:
            self.tap_times = []
        self.tap_times.append(now_ms)
        if len(self.tap_times) > PARTY_TAP_HISTORY:
            del self.tap_times[0]
        if len(self.tap_times) < 2:
            return
        intervals = [
            time.ticks_diff(self.tap_times[i], self.tap_times[i - 1])
            for i in range(1, len(self.tap_times))
        ]
        average_interval = sum(intervals) / len(intervals)
        if average_interval <= 0:
            return
        bpm = round(60000.0 / average_interval, 1)
        self.party_bpm = max(PARTY_BPM_MIN, min(PARTY_BPM_MAX, bpm))
        user_config.save(self.theme, self.hardware.brightness, self.party_bpm)

    def _select_theme(self, theme, now_ms, origin):
        self.theme = theme % len(THEME_NAMES)
        self.flash_start_ms = now_ms
        self.flash_origin = origin
        user_config.save(self.theme, self.hardware.brightness, self.party_bpm)

    def _handle_keys(self, now_ms):
        events = self.hardware.keys.update(now_ms)
        if self.serial_menu.game_active:
            # A game session owns the key LEDs and typed input; physical
            # keys become inert status lights (no HID taps, no theme
            # changes) until the player quits. Still drain the matrix
            # above so debounce state doesn't backlog while a game runs.
            return
        for event in events:
            if event.pressed:
                self._press(event.key, now_ms)
            else:
                self._release(event.key)

        for key in range(NUM_KEY_LEDS):
            if not self.held[key] or self.long_fired[key]:
                continue
            if time.ticks_diff(now_ms, self.press_ms[key]) >= LONG_PRESS_MS:
                self.long_fired[key] = True
                self._select_theme(key, now_ms, key)

    def _update_motion(self, now_ms, delta_ms=FRAME_MS):
        sensor = self.hardware.accelerometer
        if sensor is None:
            return
        try:
            acceleration = sensor.acceleration()
        except Exception:
            return

        acceleration_x = acceleration[0]
        acceleration_y = acceleration[1]
        acceleration_z = acceleration[2]
        frame_steps = delta_ms * _FRAME_STEP_SCALE
        if frame_steps < 0.0:
            frame_steps = 0.0
        # The normal path avoids an expensive fractional power on every frame.
        response = (
            _MOTION_RESPONSE
            if frame_steps == 1.0
            else 1.0 - math.pow(1.0 - _MOTION_RESPONSE, frame_steps)
        )
        if not self.motion_ready:
            self.gravity_x = acceleration_x
            self.gravity_y = acceleration_y
            self.gravity_z = acceleration_z
            self.motion_ready = True
        else:
            # Filter sensor chatter, but respond quickly enough for the pool to
            # visibly follow rotation of a hanging badge.
            self.gravity_x += (
                acceleration_x - self.gravity_x
            ) * response
            self.gravity_y += (
                acceleration_y - self.gravity_y
            ) * response
            self.gravity_z += (
                acceleration_z - self.gravity_z
            ) * response

        planar_acceleration_squared = (
            self.gravity_x * self.gravity_x + self.gravity_y * self.gravity_y
        )
        z_gate = (
            _POOL_Z_OFF - abs(self.gravity_z)
        ) / (_POOL_Z_OFF - _POOL_Z_FULL)
        if z_gate <= 0.0:
            z_gate = 0.0
        elif z_gate >= 1.0:
            z_gate = 1.0
        else:
            z_gate = z_gate * z_gate * (3.0 - 2.0 * z_gate)
        if (
            planar_acceleration_squared < _ROTATION_MIN_ACCEL_SQUARED
            or z_gate < 0.01
        ):
            # When the badge is nearly face-up, an accelerometer cannot measure
            # rotation around Z. Fade the pool instead of amplifying noise.
            self.pool_angular_velocity *= (
                0.50
                if frame_steps == 1.0
                else math.pow(0.50, frame_steps)
            )
            self.pool_direction_ready = False
            self.pool_strength += (
                0.0 - self.pool_strength
            ) * response
            return

        # atan2 only needs the direction, so no square root or normalization is
        # required. Proper acceleration points uphill, hence the minus signs.
        # Z only suppresses the effect near face-up; it does not steer the pool.
        target_angle = math.atan2(-self.gravity_y, -self.gravity_x)
        if not self.pool_direction_ready:
            self.pool_angle = target_angle
            self.pool_angular_velocity = 0.0
            self.pool_direction_ready = True
        else:
            # Preserve the tuned 25 ms spring behavior while making longer or
            # shorter frames advance by the corresponding amount of time.
            if frame_steps == 1.0:
                angle_error = (
                    target_angle - self.pool_angle + _PI
                ) % _TAU - _PI
                self.pool_angular_velocity = (
                    self.pool_angular_velocity
                    + angle_error * _POOL_SPRING
                ) * _POOL_DAMPING
                self.pool_angle = (
                    self.pool_angle
                    + self.pool_angular_velocity
                    + _PI
                ) % _TAU - _PI
            else:
                remaining = frame_steps
                while remaining > 0.0001:
                    step = 1.0 if remaining >= 1.0 else remaining
                    angle_error = (
                        target_angle - self.pool_angle + _PI
                    ) % _TAU - _PI
                    self.pool_angular_velocity += (
                        angle_error * _POOL_SPRING * step
                    )
                    self.pool_angular_velocity *= (
                        _POOL_DAMPING
                        if step == 1.0
                        else math.pow(_POOL_DAMPING, step)
                    )
                    self.pool_angle = (
                        self.pool_angle
                        + self.pool_angular_velocity * step
                        + _PI
                    ) % _TAU - _PI
                    remaining -= step
        self.pool_x = math.cos(self.pool_angle)
        self.pool_y = math.sin(self.pool_angle)
        strength_target = _POOL_LEVEL * z_gate
        self.pool_strength += (
            strength_target - self.pool_strength
        ) * response

    def _update_sparkles(self, delta_ms):
        decay = delta_ms / 620.0
        for led in range(NUM_PIXELS):
            self.sparkle[led] = max(0.0, self.sparkle[led] - decay)
        chance = min(255, int(delta_ms * 0.45))
        if random.getrandbits(8) < chance:
            self.sparkle[random.getrandbits(8) % NUM_PIXELS] = 1.0

    def _apply_motion_color(self):
        """Sweep a smooth orientation-driven hue wash through every theme."""
        strength = self.pool_strength
        if not self.pool_direction_ready or strength < 0.015:
            return

        # The color wheel wraps at the same point as pool_angle, so rotating
        # through -pi/pi stays continuous instead of jumping between colors.
        hue = (self.pool_angle + _PI) / _TAU * 255.0
        speed = min(1.0, abs(self.pool_angular_velocity) * 1.8)
        amount = strength * (
            _MOTION_HUE_BLEND + speed * _MOTION_HUE_SPEED_BOOST
        )
        amount_256 = int(amount * 256.0)
        inverse_256 = 256 - amount_256
        wash = wheel(hue, 0.72)
        frame = self.frame
        for led in range(NUM_PIXELS):
            color = frame[led]
            frame[led] = (
                (color[0] * inverse_256 + wash[0] * amount_256) >> 8,
                (color[1] * inverse_256 + wash[1] * amount_256) >> 8,
                (color[2] * inverse_256 + wash[2] * amount_256) >> 8,
            )

    def _apply_light_pool(self):
        strength = self.pool_strength
        if strength < 0.015 or abs(self.pool_x) + abs(self.pool_y) < 0.015:
            return

        # Geometry below is 8.8 fixed point. On the RP2040, doing these small
        # per-pixel transforms as integers is substantially faster than float
        # division while preserving more precision than the LEDs can display.
        direction_x_256 = int(self.pool_x * 256.0)
        direction_y_256 = int(self.pool_y * 256.0)
        strength_256 = int(strength * 256.0)
        slosh_speed = min(1.0, abs(self.pool_angular_velocity) * 1.8)
        wobble_256 = int(
            (0.075 + slosh_speed * 0.09) * strength * 256.0
        )
        wave_phase = self.animation_seconds * 2.7
        wave_cycle = wave_phase * _WAVE_CYCLE_SCALE + _WAVE_CYCLE_OFFSET
        wave_fraction = wave_cycle - int(wave_cycle)
        wave_256 = int((1.0 - 4.0 * abs(wave_fraction - 0.5)) * 256.0)
        accent = theme_accent(self.theme)
        frame = self.frame
        x_positions = _POOL_X_256
        y_positions = _POOL_Y_256
        for led in range(NUM_PIXELS):
            x = x_positions[led]
            y = y_positions[led]
            projection_256 = (
                x * direction_x_256 + y * direction_y_256
            ) >> 8
            if projection_256 < -256:
                projection_256 = -256
            elif projection_256 > 256:
                projection_256 = 256

            # A slightly uneven shoreline makes the lit area feel liquid
            # instead of like a plain linear brightness gradient. A triangle
            # wave keeps the shoreline continuous, and the small bend makes
            # it vary across the direction of travel without per-LED trig.
            across_256 = (
                -x * direction_y_256 + y * direction_x_256
            ) >> 8
            shoreline_256 = 31 + (
                (
                    wave_256 + ((across_256 * 46) >> 8)
                ) * wobble_256
                >> 8
            )
            difference_256 = projection_256 - shoreline_256
            wetness_256 = (difference_256 * 441) >> 8
            if wetness_256 <= 0:
                wetness_256 = 0
            elif wetness_256 >= 256:
                wetness_256 = 256
            else:
                wetness_256 = (
                    wetness_256
                    * wetness_256
                    * (768 - 2 * wetness_256)
                ) >> 16
            surface_256 = 256 - ((abs(difference_256) * 1164) >> 8)
            if surface_256 < 0:
                surface_256 = 0

            # Make the uphill area visibly "dry" while the pool and its bright
            # surface gather at the downhill edge.
            level_256 = (
                256
                - ((strength_256 * 236) >> 8)
                + ((strength_256 * wetness_256 * 499) >> 16)
                + ((strength_256 * surface_256 * 141) >> 16)
            )
            accent_256 = (
                strength_256
                * (wetness_256 * 77 + surface_256 * 90)
            ) >> 16
            color = frame[led]
            red = (color[0] * level_256 + accent[0] * accent_256) >> 8
            green = (
                color[1] * level_256 + accent[1] * accent_256
            ) >> 8
            blue = (
                color[2] * level_256 + accent[2] * accent_256
            ) >> 8
            frame[led] = (
                255 if red > 255 else red,
                255 if green > 255 else green,
                255 if blue > 255 else blue,
            )

    def _apply_ripples(self, now_ms):
        active = []
        for origin, started, color in self.ripples:
            age = time.ticks_diff(now_ms, started) / 1000.0
            radius = age * _RIPPLE_SPEED
            if radius <= _RIPPLE_MAX_RADIUS:
                active.append((origin, started, color))
            life = max(0.0, 1.0 - radius / _RIPPLE_MAX_RADIUS)
            for led in range(NUM_PIXELS):
                difference = abs(_DISTANCE[origin][led] - radius)
                if difference < _RIPPLE_WIDTH:
                    strength = (1.0 - difference / _RIPPLE_WIDTH) * life * life
                    self.frame[led] = add(self.frame[led], color, strength * 0.90)
            if age < 0.16:
                impact = 1.0 - age / 0.16
                self.frame[origin] = add(self.frame[origin], blend(color, _WHITE, 0.62), impact)
        self.ripples = active

    def _apply_held(self, now_ms):
        for key in range(NUM_KEY_LEDS):
            if not self.held[key]:
                continue
            held_ms = max(0, time.ticks_diff(now_ms, self.press_ms[key]))
            progress = min(1.0, held_ms / float(LONG_PRESS_MS))
            pulse = 0.5 + 0.5 * math.sin(self.animation_seconds * 9.0 + key)
            color = blend(theme_accent(key), _WHITE, progress * 0.72)
            self.frame[key] = add(self.frame[key], color, 0.16 + progress * 0.36 + pulse * 0.10)

    def _apply_theme_flash(self, now_ms):
        age_ms = time.ticks_diff(now_ms, self.flash_start_ms)
        if age_ms < 0 or age_ms >= 720:
            return
        head = age_ms / 720.0 * (len(_FLASH_ORDER) + 3)
        color = theme_accent(self.theme)
        for order, led in enumerate(_FLASH_ORDER):
            strength = max(0.0, 1.0 - abs(order - head) / 2.6)
            if strength:
                self.frame[led] = add(self.frame[led], color, strength * 0.78)
        self.frame[self.flash_origin % NUM_KEY_LEDS] = add(
            self.frame[self.flash_origin % NUM_KEY_LEDS], _WHITE, max(0.0, 1.0 - age_ms / 300.0)
        )

    def update(self):
        now_ms = time.ticks_ms()
        self._handle_keys(now_ms)
        usb_keyboard.update(now_ms)
        self.serial_menu.update(now_ms)

        delta_ms = time.ticks_diff(now_ms, self.last_frame_ms)
        if delta_ms < FRAME_MS:
            return
        self.last_frame_ms = now_ms
        delta_ms = min(delta_ms, 100)
        self.animation_seconds += delta_ms / 1000.0

        if not self.serial_menu.game_active:
            self._update_motion(now_ms, delta_ms)
            self._update_sparkles(delta_ms)
            startup_elapsed = time.ticks_diff(now_ms, self.start_ms)
            motion_x = self.pool_x * self.pool_strength
            motion_y = self.pool_y * self.pool_strength
            if startup_elapsed < STARTUP_MS:
                render_startup(
                    self.frame,
                    startup_elapsed,
                    self.theme,
                    motion_x,
                    motion_y,
                    self.sparkle,
                    self.party_bpm,
                )
            else:
                render_theme(
                    self.frame,
                    self.theme,
                    self.animation_seconds,
                    motion_x,
                    motion_y,
                    self.sparkle,
                    self.party_bpm,
                )

        # Theme rendering is the longest CPU-bound stage. Service input again
        # before overlays and the LED write so a frame cannot monopolize the
        # scanner, USB HID output, or the serial console for its full duration.
        now_ms = time.ticks_ms()
        self._handle_keys(now_ms)
        usb_keyboard.update(now_ms)
        self.serial_menu.update(now_ms)

        if not self.serial_menu.game_active:
            self._apply_motion_color()
            self._apply_light_pool()
            self._apply_ripples(now_ms)
            self._apply_held(now_ms)
            self._apply_theme_flash(now_ms)
        self.hardware.show(self.frame)

    def run(self):
        try:
            while True:
                self.update()
                time.sleep_ms(1)
        finally:
            usb_keyboard.release_all()
            self.hardware.off()
