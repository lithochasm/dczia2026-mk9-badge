"""Allocation-light RGB helpers that work on MicroPython and CPython."""


def clamp(value, low=0.0, high=1.0):
    if value < low:
        return low
    if value > high:
        return high
    return value


def scale(color, level):
    level = clamp(level)
    return (
        int(color[0] * level),
        int(color[1] * level),
        int(color[2] * level),
    )


def multiply(color, level):
    """Scale RGB while allowing gentle amplification above 100%."""
    level = max(0.0, level)
    return (
        min(255, int(color[0] * level)),
        min(255, int(color[1] * level)),
        min(255, int(color[2] * level)),
    )


def blend(first, second, amount):
    amount = clamp(amount)
    inverse = 1.0 - amount
    return (
        int(first[0] * inverse + second[0] * amount),
        int(first[1] * inverse + second[1] * amount),
        int(first[2] * inverse + second[2] * amount),
    )


def add(base, overlay, level=1.0):
    level = clamp(level)
    return (
        min(255, base[0] + int(overlay[0] * level)),
        min(255, base[1] + int(overlay[1] * level)),
        min(255, base[2] + int(overlay[2] * level)),
    )


def wheel(position, level=1.0):
    """Return a smooth RGB rainbow color for position 0..255."""
    position = int(position) & 255
    if position < 85:
        color = (255 - position * 3, position * 3, 0)
    elif position < 170:
        position -= 85
        color = (0, 255 - position * 3, position * 3)
    else:
        position -= 170
        color = (position * 3, 0, 255 - position * 3)
    return scale(color, level)


def palette(colors, position):
    """Sample a looping palette using a normalized position."""
    position %= 1.0
    scaled = position * len(colors)
    index = int(scaled) % len(colors)
    return blend(colors[index], colors[(index + 1) % len(colors)], scaled - int(scaled))


def smoothstep(value):
    value = clamp(value)
    return value * value * (3.0 - 2.0 * value)
