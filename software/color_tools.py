"""Small RGB helpers shared by the badge animations.

CircuitPython's ``rainbowio.colorwheel`` returns a packed 0xRRGGBB integer.
NeoPixel accepts that representation directly, but animation math needs RGB
tuples.  Keeping the conversion here prevents the packed value from being
accidentally treated as an iterable.
"""

from rainbowio import colorwheel as _packed_colorwheel


def _unit(value):
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def unpack(packed):
    """Convert a packed 0xRRGGBB value to an (r, g, b) tuple."""
    return ((packed >> 16) & 0xFF, (packed >> 8) & 0xFF, packed & 0xFF)


def wheel(hue, level=1.0):
    """Return a color-wheel RGB tuple, optionally scaled by ``level``."""
    color = unpack(_packed_colorwheel(int(hue) & 0xFF))
    return scale(color, level)


def scale(color, level):
    """Scale an RGB tuple without allowing negative output."""
    level = _unit(level)
    if level >= 1.0:
        return color
    return (
        int(color[0] * level),
        int(color[1] * level),
        int(color[2] * level),
    )


def blend(first, second, amount):
    """Linearly blend from ``first`` to ``second``."""
    amount = _unit(amount)
    inverse = 1.0 - amount
    return (
        int(first[0] * inverse + second[0] * amount),
        int(first[1] * inverse + second[1] * amount),
        int(first[2] * inverse + second[2] * amount),
    )


def add(base, overlay, level=1.0):
    """Add an RGB overlay with saturation at 255."""
    level = _unit(level)
    return (
        min(255, base[0] + int(overlay[0] * level)),
        min(255, base[1] + int(overlay[1] * level)),
        min(255, base[2] + int(overlay[2] * level)),
    )
