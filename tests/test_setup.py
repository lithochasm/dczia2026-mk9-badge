"""Import setup.py against the pin names exposed by generic Pico firmware."""

import importlib.util
import os
import sys
import types
import unittest


REPOSITORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPOSITORY, "software"))


class Pin:

    def __init__(self, name):
        self.name = name


fake_board = types.ModuleType("board")
for number in range(29):
    setattr(fake_board, "GP" + str(number), Pin("GP" + str(number)))
# Raspberry Pi Pico's pins.c maps physical GPIO29 to A3, not GP29.
fake_board.A3 = Pin("GP29/A3")


class FakeI2C:

    def __init__(self, clock, data):
        self.clock = clock
        self.data = data


fake_busio = types.ModuleType("busio")
fake_busio.I2C = FakeI2C


class FakePixels:

    def __init__(self, pin, count, **kwargs):
        self.pin = pin
        self.count = count
        self.options = kwargs


fake_neopixel = types.ModuleType("neopixel")
fake_neopixel.GRB = "GRB"
fake_neopixel.NeoPixel = FakePixels


class FakeKeyMatrix:

    def __init__(self, rows, columns, **kwargs):
        self.rows = rows
        self.columns = columns
        self.options = kwargs


fake_keypad = types.ModuleType("keypad")
fake_keypad.KeyMatrix = FakeKeyMatrix


class FakeDigitalInOut:

    def __init__(self, pin):
        self.pin = pin

    def switch_to_input(self, **kwargs):
        self.input_options = kwargs


fake_digitalio = types.ModuleType("digitalio")
fake_digitalio.DigitalInOut = FakeDigitalInOut
fake_digitalio.Pull = types.SimpleNamespace(UP="UP")

fake_accelerometer = types.ModuleType("adafruit_msa3xx")
fake_accelerometer.MSA301 = lambda i2c: types.SimpleNamespace(i2c=i2c)


class SetupTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        replacements = {
            "board": fake_board,
            "busio": fake_busio,
            "neopixel": fake_neopixel,
            "keypad": fake_keypad,
            "digitalio": fake_digitalio,
            "adafruit_msa3xx": fake_accelerometer,
        }
        cls.original_modules = {}
        for name, module in replacements.items():
            cls.original_modules[name] = sys.modules.get(name)
            sys.modules[name] = module

        path = os.path.join(REPOSITORY, "software", "setup.py")
        spec = importlib.util.spec_from_file_location("setup_under_test", path)
        cls.setup = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.setup)

    @classmethod
    def tearDownClass(cls):
        for name, original in cls.original_modules.items():
            if original is None:
                del sys.modules[name]
            else:
                sys.modules[name] = original

    def test_rgb_chain_uses_as_built_gp21_net(self):
        self.assertIs(fake_board.GP21, self.setup.pixels.pin)

    def test_sao_gp29_uses_pico_firmware_a3_alias(self):
        self.assertFalse(hasattr(fake_board, "GP29"))
        self.assertIs(fake_board.A3, self.setup.sao1_gpio1.pin)


if __name__ == "__main__":
    unittest.main()
