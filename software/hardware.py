"""Initialise MK9 peripherals using MicroPython's machine APIs."""

from machine import I2C, Pin, SoftI2C
import neopixel

from config import (
    ACCEL_I2C_ID,
    ACCEL_SCL_PIN,
    ACCEL_SDA_PIN,
    GLOBAL_BRIGHTNESS,
    NUM_PIXELS,
    PIXEL_PIN,
    SAO_GPIO_PINS,
    SAO_SCL_PIN,
    SAO_SDA_PIN,
)
from key_matrix import KeyMatrix
from msa301 import MSA301

def _brightness_lut(level):
    return bytes([int(value * level) for value in range(256)])


class Hardware:
    def __init__(self):
        self.pixels = neopixel.NeoPixel(Pin(PIXEL_PIN, Pin.OUT), NUM_PIXELS)
        self.keys = KeyMatrix()
        self.frame = [(0, 0, 0)] * NUM_PIXELS
        self.brightness = GLOBAL_BRIGHTNESS
        self._lut = _brightness_lut(self.brightness)

        self.accel_i2c = None
        self.accelerometer = None
        self.accelerometer_error = None
        try:
            self.accel_i2c = I2C(
                ACCEL_I2C_ID,
                sda=Pin(ACCEL_SDA_PIN),
                scl=Pin(ACCEL_SCL_PIN),
                freq=400000,
            )
            self.accelerometer = MSA301(self.accel_i2c)
        except Exception as error:
            self.accelerometer_error = error

        # Preserve both SAO connectors. SoftI2C is required for this PCB's
        # GP9/GP10 routing because it is not one RP2040 hardware-I2C pin pair.
        self.sao_i2c = None
        self.sao_gpio = ()
        self.sao_error = None
        try:
            self.sao_i2c = SoftI2C(
                sda=Pin(SAO_SDA_PIN),
                scl=Pin(SAO_SCL_PIN),
                freq=100000,
            )
            self.sao_gpio = tuple(Pin(pin, Pin.IN, Pin.PULL_UP) for pin in SAO_GPIO_PINS)
        except Exception as error:
            self.sao_error = error

    def set_brightness(self, level):
        self.brightness = max(0.0, min(1.0, level))
        self._lut = _brightness_lut(self.brightness)

    def show(self, frame=None):
        if frame is None:
            frame = self.frame
        # NeoPixel stores three-channel pixels in GRB byte order. Filling the
        # buffer directly avoids 15 tuple allocations and method calls per
        # frame; the lookup also replaces repeated floating-point scaling.
        buffer = self.pixels.buf
        lut = self._lut
        offset = 0
        for color in frame:
            buffer[offset] = lut[color[1]]
            buffer[offset + 1] = lut[color[0]]
            buffer[offset + 2] = lut[color[2]]
            offset += 3
        self.pixels.write()

    def off(self):
        self.pixels.fill((0, 0, 0))
        self.pixels.write()
