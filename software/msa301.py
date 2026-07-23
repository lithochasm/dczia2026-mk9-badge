"""Small native MicroPython driver for the MSA301/GSDA213 accelerometer."""

_ADDRESS = 0x26
_PART_ID = 0x13

_REG_PART_ID = 0x01
_REG_X_L = 0x02
_REG_RES_RANGE = 0x0F
_REG_ODR = 0x10
_REG_POWER_MODE = 0x11

STANDARD_GRAVITY = 9.80665


def decode_axis(low, high):
    """Decode one signed, left-aligned 14-bit sample."""
    raw = low | (high << 8)
    if raw & 0x8000:
        raw -= 0x10000
    return raw >> 2


class MSA301:
    ADDRESS = _ADDRESS

    def __init__(self, i2c, address=_ADDRESS):
        self.i2c = i2c
        self.address = address
        if self._read(_REG_PART_ID, 1)[0] != _PART_ID:
            raise OSError("MSA301 part ID mismatch")

        # All axes enabled, 125 Hz sample rate.
        self._update(_REG_ODR, 0x10, 0x07)
        # Normal power mode, 62.5 Hz bandwidth.
        self._update(_REG_POWER_MODE, 0x21, 0x0E)
        # 14-bit resolution, +/-4 g range.
        self._update(_REG_RES_RANGE, 0xF0, 0x01)
        self.scale_counts_per_g = 2048.0

    def _read(self, register, length):
        return self.i2c.readfrom_mem(self.address, register, length)

    def _write(self, register, value):
        self.i2c.writeto_mem(self.address, register, bytes((value & 0xFF,)))

    def _update(self, register, keep_mask, bits):
        value = self._read(register, 1)[0]
        self._write(register, (value & keep_mask) | bits)

    def read_raw(self):
        data = self._read(_REG_X_L, 6)
        return (
            decode_axis(data[0], data[1]),
            decode_axis(data[2], data[3]),
            decode_axis(data[4], data[5]),
        )

    def acceleration(self):
        factor = STANDARD_GRAVITY / self.scale_counts_per_g
        x, y, z = self.read_raw()
        return (x * factor, y * factor, z * factor)
