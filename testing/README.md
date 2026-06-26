# Hardware Tester

Self-contained hardware test fixture for the MK9 badge. Copy `code.py` to the root of `CIRCUITPY` (replacing the production firmware) to run the tests.

## What It Tests

### LEDs
All 15 LEDs (9 key + 6 backlight) cycle through **red → green → blue** continuously:
- Each color holds for **0.5 s**
- A directional wipe sweeps the next color across all LEDs over **0.5 s**
- Total: **1 second per color**

### Key Matrix
Press any key — its **LED fast-flashes white at 10 Hz** as long as the key is held. All 9 keys can be held simultaneously to verify N-key rollover. Expected LED for each key:

```
key 0 (C0R0) → LED 0    key 1 (C1R0) → LED 1    key 2 (C2R0) → LED 2
key 3 (C0R1) → LED 3    key 4 (C1R1) → LED 4    key 5 (C2R1) → LED 5
key 6 (C0R2) → LED 6    key 7 (C1R2) → LED 7    key 8 (C2R2) → LED 8
```

### Accelerometer
The wipe direction changes based on tilt when a new wipe starts:

| Tilt | Direction |
|------|-----------|
| Right (+X) | Left → Right |
| Left  (−X) | Right → Left |
| Toward you (+Y) | Top → Bottom |
| Away  (−Y) | Bottom → Top |
| Flat (both axes < 1 m/s²) | Holds last direction |

Tilt the badge and watch the wipe direction change on the next colour transition.

## Libraries Required

Same as production firmware — only `adafruit_msa3xx` is needed beyond CircuitPython built-ins:

| Library | Source |
|---------|--------|
| `adafruit_msa3xx.mpy` | Adafruit CircuitPython Bundle |

If the accelerometer library is missing or the sensor doesn't respond, the tester falls back gracefully — LEDs and keys still work, wipe direction defaults to left-to-right.

## Restoring Production Firmware

After testing, copy all files from `software/` back to the root of `CIRCUITPY` (including `boot.py`).
