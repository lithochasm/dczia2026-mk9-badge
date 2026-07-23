"""Initialise MK9 peripherals using MicroPython's machine APIs."""

from machine import I2C, Pin, SoftI2C
import neopixel

from color_tools import scale
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


class Hardware:
    def __init__(self):
        self.pixels = neopixel.NeoPixel(Pin(PIXEL_PIN, Pin.OUT), NUM_PIXELS)
        self.keys = KeyMatrix()
        self.frame = [(0, 0, 0)] * NUM_PIXELS

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

    def show(self, frame=None):
        if frame is None:
            frame = self.frame
        for index in range(NUM_PIXELS):
            self.pixels[index] = scale(frame[index], GLOBAL_BRIGHTNESS)
        self.pixels.write()

    def off(self):
        self.pixels.fill((0, 0, 0))
        self.pixels.write()
