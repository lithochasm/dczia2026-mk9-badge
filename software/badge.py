"""Interactive lighting, key handling, and motion behavior for the MK9."""

import math
import random
import time

from color_tools import add, blend, multiply, smoothstep
from config import (
    FRAME_MS,
    LED_POSITIONS,
    LONG_PRESS_MS,
    NUM_KEY_LEDS,
    NUM_PIXELS,
    NUMPAD_CODES,
    STARTUP_MS,
    THEME_NAMES,
)
from themes import render_startup, render_theme, theme_accent
import usb_keyboard

_WHITE = (255, 255, 255)
_FLASH_ORDER = (14, 0, 1, 2, 9, 10, 5, 8, 11, 12, 7, 6, 13, 3, 4)
_RIPPLE_SPEED = 2.5
_RIPPLE_WIDTH = 0.58
_RIPPLE_MAX_RADIUS = 4.25

_X = tuple(position[1] - 1.0 for position in LED_POSITIONS)
_Y = tuple(position[0] - 1.0 for position in LED_POSITIONS)


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
    def __init__(self, hardware):
        self.hardware = hardware
        self.frame = hardware.frame
        self.theme = 0
        self.start_ms = time.ticks_ms()
        self.last_frame_ms = time.ticks_add(self.start_ms, -FRAME_MS)
        self.animation_seconds = 0.0

        self.held = [False] * NUM_KEY_LEDS
        self.press_ms = [0] * NUM_KEY_LEDS
        self.long_fired = [False] * NUM_KEY_LEDS
        self.ripples = []
        self.sparkle = [0.0] * NUM_PIXELS

        self.tilt_x = 0.0
        self.tilt_y = 0.0
        self.gravity = [0.0, 0.0, 9.80665]
        self.motion_ready = False
        self.linear_x = 0.0
        self.linear_y = 0.0
        self.pool_x = 0.0
        self.pool_y = 0.0
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

    def _release(self, key):
        self.held[key] = False
        if not self.long_fired[key]:
            usb_keyboard.tap(NUMPAD_CODES[key])

    def _select_theme(self, theme, now_ms, origin):
        self.theme = theme % len(THEME_NAMES)
        self.flash_start_ms = now_ms
        self.flash_origin = origin

    def _handle_keys(self, now_ms):
        for event in self.hardware.keys.update(now_ms):
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

    def _update_motion(self, now_ms):
        sensor = self.hardware.accelerometer
        if sensor is None:
            return
        try:
            acceleration = sensor.acceleration()
        except Exception:
            return

        if not self.motion_ready:
            self.gravity[:] = acceleration
            self.motion_ready = True
            return

        residual_x = acceleration[0] - self.gravity[0]
        residual_y = acceleration[1] - self.gravity[1]
        residual_z = acceleration[2] - self.gravity[2]
        self.gravity[0] += residual_x * 0.12
        self.gravity[1] += residual_y * 0.12
        self.gravity[2] += residual_z * 0.12

        target_x = max(-1.0, min(1.0, self.gravity[0] / 9.80665))
        target_y = max(-1.0, min(1.0, self.gravity[1] / 9.80665))
        self.tilt_x += (target_x - self.tilt_x) * 0.18
        self.tilt_y += (target_y - self.tilt_y) * 0.18

        # The high-pass component captures quick movement independently of
        # gravity. The sensor reports proper acceleration, so its X/Y direction
        # is opposite the downhill direction in which a liquid would settle.
        linear_target_x = max(-1.0, min(1.0, residual_x / 6.0))
        linear_target_y = max(-1.0, min(1.0, residual_y / 6.0))
        self.linear_x += (linear_target_x - self.linear_x) * 0.22
        self.linear_y += (linear_target_y - self.linear_y) * 0.22

        pool_target_x = max(-1.0, min(
            1.0, -(self.tilt_x * 1.65 + self.linear_x * 0.45)
        ))
        pool_target_y = max(-1.0, min(
            1.0, -(self.tilt_y * 1.65 + self.linear_y * 0.45)
        ))

        # A slower pool response gives the light visible weight and a small
        # amount of lag when the badge changes direction.
        self.pool_x += (pool_target_x - self.pool_x) * 0.10
        self.pool_y += (pool_target_y - self.pool_y) * 0.10
        strength_target = min(1.0, math.sqrt(
            pool_target_x * pool_target_x + pool_target_y * pool_target_y
        ))
        self.pool_strength += (strength_target - self.pool_strength) * 0.12

    def _update_sparkles(self, delta_ms):
        decay = delta_ms / 620.0
        for led in range(NUM_PIXELS):
            self.sparkle[led] = max(0.0, self.sparkle[led] - decay)
        chance = min(255, int(delta_ms * 0.45))
        if random.getrandbits(8) < chance:
            self.sparkle[random.getrandbits(8) % NUM_PIXELS] = 1.0

    def _apply_light_pool(self):
        magnitude = math.sqrt(self.pool_x * self.pool_x + self.pool_y * self.pool_y)
        strength = self.pool_strength
        if magnitude < 0.015 or strength < 0.015:
            return

        direction_x = self.pool_x / magnitude
        direction_y = self.pool_y / magnitude
        for led in range(NUM_PIXELS):
            projection = (_X[led] * direction_x + _Y[led] * direction_y) / 2.25
            projection = max(-1.0, min(1.0, projection))

            # A slightly uneven shoreline makes the lit area feel liquid
            # instead of like a plain linear brightness gradient.
            across = (-_X[led] * direction_y + _Y[led] * direction_x) / 2.25
            shoreline = 0.12 + math.sin(
                self.animation_seconds * 2.7 + across * 3.8
            ) * 0.075 * strength
            wetness = smoothstep((projection - shoreline) / 0.58)
            surface = max(0.0, 1.0 - abs(projection - shoreline) / 0.22)

            # At a strong tilt, the uphill area becomes visibly "dry" while
            # the pool and its bright surface gather at the downhill edge.
            level = (
                1.0
                - 0.72 * strength
                + 1.28 * strength * wetness
                + 0.24 * strength * surface
            )
            self.frame[led] = multiply(self.frame[led], level)

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

        delta_ms = time.ticks_diff(now_ms, self.last_frame_ms)
        if delta_ms < FRAME_MS:
            return
        self.last_frame_ms = now_ms
        delta_ms = min(delta_ms, 100)
        self.animation_seconds += delta_ms / 1000.0

        self._update_motion(now_ms)
        self._update_sparkles(delta_ms)
        startup_elapsed = time.ticks_diff(now_ms, self.start_ms)
        if startup_elapsed < STARTUP_MS:
            render_startup(
                self.frame,
                startup_elapsed,
                self.theme,
                self.tilt_x,
                self.tilt_y,
                self.sparkle,
            )
        else:
            render_theme(
                self.frame,
                self.theme,
                self.animation_seconds,
                self.tilt_x,
                self.tilt_y,
                self.sparkle,
            )

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
