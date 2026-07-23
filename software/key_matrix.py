"""Active-high scanner for the MK9's diode-isolated 3x3 key matrix."""

import time

from config import COLUMN_PINS, DEBOUNCE_SCANS, KEY_SCAN_MS, ROW_PINS

try:
    _ticks_diff = time.ticks_diff
except AttributeError:
    def _ticks_diff(first, second):
        return first - second

try:
    _sleep_us = time.sleep_us
except AttributeError:
    def _sleep_us(microseconds):
        time.sleep(microseconds / 1000000.0)


class KeyEvent:
    def __init__(self, key, pressed):
        self.key = key
        self.pressed = pressed


class KeyMatrix:
    """Scan column -> switch -> diode -> row, with software debouncing."""

    def __init__(self, pin_class=None):
        if pin_class is None:
            from machine import Pin

            pin_class = Pin

        self._pin_class = pin_class
        self.rows = tuple(pin_class(pin, pin_class.IN, pin_class.PULL_DOWN) for pin in ROW_PINS)
        self.columns = tuple(pin_class(pin, pin_class.OUT, value=0) for pin in COLUMN_PINS)
        self._stable = [False] * 9
        self._counts = [0] * 9
        self._last_scan = 0

    def _raw(self):
        result = [False] * 9
        for column_index, column in enumerate(self.columns):
            column.value(1)
            _sleep_us(2)
            for row_index, row in enumerate(self.rows):
                result[row_index * 3 + column_index] = bool(row.value())
            column.value(0)
        return result

    def update(self, now_ms):
        if _ticks_diff(now_ms, self._last_scan) < KEY_SCAN_MS:
            return ()
        self._last_scan = now_ms
        raw = self._raw()
        events = []
        for key in range(9):
            if raw[key] == self._stable[key]:
                self._counts[key] = 0
                continue
            self._counts[key] += 1
            if self._counts[key] >= DEBOUNCE_SCANS:
                self._stable[key] = raw[key]
                self._counts[key] = 0
                events.append(KeyEvent(key, raw[key]))
        return events

    def pressed(self, key):
        return self._stable[key]
