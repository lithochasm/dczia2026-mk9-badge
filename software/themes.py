"""Nine spatial color themes plus the boot rainbow."""

import math

from color_tools import add, blend, palette, scale, smoothstep, wheel
from config import BACKLIGHT_START, LED_POSITIONS, NUM_PIXELS, STARTUP_MS

_X = tuple(position[1] - 1.0 for position in LED_POSITIONS)
_Y = tuple(position[0] - 1.0 for position in LED_POSITIONS)
_RADIUS = tuple(math.sqrt(_X[i] * _X[i] + _Y[i] * _Y[i]) for i in range(NUM_PIXELS))
_ANGLE = tuple(math.atan2(_Y[i], _X[i]) for i in range(NUM_PIXELS))

_VAPOR = ((255, 18, 154), (93, 26, 230), (0, 225, 255), (255, 18, 154))
_OCEAN = ((0, 8, 38), (0, 54, 120), (0, 190, 185), (90, 255, 235))
_EMBER = ((18, 0, 0), (150, 5, 0), (255, 55, 0), (255, 190, 20))
_ULTRA = ((18, 0, 65), (90, 0, 210), (214, 20, 255), (20, 70, 255))
_SUNSET = ((105, 0, 100), (245, 22, 105), (255, 102, 20), (255, 215, 55))
_GLACIER = ((0, 20, 50), (0, 125, 205), (40, 245, 255), (225, 255, 255))


def theme_accent(theme):
    accents = (
        (255, 255, 255),
        (255, 20, 190),
        (20, 240, 225),
        (255, 92, 10),
        (35, 255, 70),
        (185, 45, 255),
        (255, 165, 35),
        (185, 255, 255),
        (190, 215, 255),
    )
    return accents[theme % len(accents)]


def render_theme(frame, theme, seconds, tilt_x=0.0, tilt_y=0.0, sparkle=None):
    """Render one complete theme into the supplied 15-element frame."""
    theme %= 9
    for led in range(NUM_PIXELS):
        x = _X[led]
        y = _Y[led]
        edge = 0.08 if led >= BACKLIGHT_START else 0.0

        if theme == 0:  # Prism: flowing diagonal rainbow
            wave = 0.5 + 0.5 * math.sin(seconds * 1.8 + x * 1.4 - y)
            hue = seconds * 34.0 + x * 32.0 + y * 45.0 + tilt_x * 42.0 + tilt_y * 24.0
            color = wheel(hue, 0.16 + wave * 0.34 + edge)

        elif theme == 1:  # Vaporwave plasma
            field = 0.5 + 0.5 * math.sin(seconds * 1.35 + x * 1.25 + y * 0.8 + tilt_x)
            color = scale(palette(_VAPOR, field), 0.22 + 0.20 * (1.0 - field) + edge)

        elif theme == 2:  # Deep ocean waves
            wave = 0.5 + 0.5 * math.sin(seconds * 1.05 - y * 1.7 + x * 0.45 + tilt_y * 1.3)
            swell = 0.5 + 0.5 * math.sin(seconds * 0.52 + _RADIUS[led] * 1.3)
            color = scale(palette(_OCEAN, wave * 0.72 + swell * 0.18), 0.20 + wave * 0.27 + edge)

        elif theme == 3:  # Ember: heat rising upward
            heat = 0.5 + 0.5 * math.sin(seconds * 2.7 + x * 2.2 + y * 0.75)
            heat = heat * heat
            color = scale(palette(_EMBER, 0.18 + heat * 0.72), 0.16 + heat * 0.42 + edge)

        elif theme == 4:  # Matrix: falling green columns
            fall = (seconds * 0.72 + y * 0.31 + x * 0.13) % 1.0
            head = max(0.0, 1.0 - abs(fall - 0.16) / 0.18)
            trail = max(0.0, 1.0 - fall) * 0.24
            level = 0.035 + trail + head * 0.66 + edge * 0.35
            color = scale((60, 255, 80), level)

        elif theme == 5:  # Ultraviolet spiral
            spiral = (_ANGLE[led] / 6.28318 + _RADIUS[led] * 0.20 - seconds * 0.15 + tilt_x * 0.08)
            pulse = 0.5 + 0.5 * math.sin(seconds * 1.5 - _RADIUS[led] * 1.2)
            color = scale(palette(_ULTRA, spiral), 0.17 + pulse * 0.34 + edge)

        elif theme == 6:  # Sunset horizon
            horizon = 0.5 + 0.5 * math.sin(seconds * 0.68 + x * 0.45 - y * 0.9 + tilt_y)
            shimmer = 0.5 + 0.5 * math.sin(seconds * 2.1 + _RADIUS[led] * 1.8)
            color = scale(palette(_SUNSET, 0.16 + horizon * 0.70), 0.21 + shimmer * 0.25 + edge)

        elif theme == 7:  # Glacier breathing rings
            ring = 0.5 + 0.5 * math.sin(seconds * 1.55 - _RADIUS[led] * 1.55 + tilt_x * 0.7)
            crest = ring * ring
            color = scale(palette(_GLACIER, 0.28 + crest * 0.60), 0.15 + crest * 0.43 + edge)

        else:  # Moonlight scanner and occasional stars
            beam_position = math.sin(seconds * 0.8) * 2.2
            projection = x * math.cos(seconds * 0.18) + y * math.sin(seconds * 0.18 + tilt_y * 0.5)
            beam = max(0.0, 1.0 - abs(projection - beam_position) / 0.72)
            star = 0.0 if sparkle is None else sparkle[led]
            color = add(scale((35, 55, 105), 0.13 + edge), (205, 225, 255), beam * 0.55)
            color = add(color, (255, 255, 255), star * star * 0.75)

        frame[led] = color


def render_startup(frame, elapsed_ms, theme=0, tilt_x=0.0, tilt_y=0.0, sparkle=None):
    """Fade in a moving rainbow, then cross-fade to the active theme."""
    progress = min(1.0, max(0.0, elapsed_ms / float(STARTUP_MS)))
    rainbow = [None] * NUM_PIXELS
    fade_in = smoothstep(progress / 0.24)

    for led in range(NUM_PIXELS):
        x = _X[led]
        y = _Y[led]
        glow = 0.72 + 0.28 * math.sin(elapsed_ms * 0.0032 + x * 0.8 - y * 0.65)
        hue = elapsed_ms * 0.055 + x * 35.0 + y * 44.0
        rainbow[led] = wheel(hue, fade_in * glow)

    if progress < 0.72:
        for led in range(NUM_PIXELS):
            frame[led] = rainbow[led]
        return

    render_theme(frame, theme, elapsed_ms / 1000.0, tilt_x, tilt_y, sparkle)
    amount = smoothstep((progress - 0.72) / 0.28)
    for led in range(NUM_PIXELS):
        frame[led] = blend(rainbow[led], frame[led], amount)
