# MicroPython Hardware Tester

Upload the production `software/` files first, then upload `testing/main.py`
as `/main.py` on the badge. Reset it to start the test.

- All 15 LEDs continuously sweep through red, green, and blue.
- Holding a key turns its matching LED white and prints its number.
- Tilting the badge turns the matching perimeter edge white and prints live
  X/Y/Z acceleration every half second.
- If the accelerometer is missing, all six perimeter LEDs blink red.

The key numbers are row-major:

```text
1 2 3
4 5 6
7 8 9
```

Restore `software/main.py` as `/main.py` when testing is finished.
