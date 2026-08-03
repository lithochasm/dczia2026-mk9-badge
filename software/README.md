# MK9 Badge — MicroPython Firmware

Native MicroPython firmware for the RP2040-based DCZia MK9 badge. It has no
runtime dependency on CircuitPython or Adafruit libraries.

## Behavior

Startup is a 3.2-second smoothly fading, moving rainbow that cross-fades into
the active theme. Normal key taps still send the USB numpad layout:

```text
7 8 9
4 5 6
1 2 3
```

Hold a key for 750 ms to select its theme. A long press changes lighting and
does not send a number:

| Key | Theme |
|---:|---|
| 1 | Prism |
| 2 | Vaporwave |
| 3 | Deep Ocean |
| 4 | Ember |
| 5 | Matrix |
| 6 | Ultraviolet |
| 7 | Sunset |
| 8 | Glacier |
| 9 | Moonlight |

Every press creates a spatial ripple. As a hanging badge rotates, the current
theme's light quickly follows physical down and gathers like liquid at the
lowest edge or corner, with a short overshoot and settling shoreline wobble.
Forward/back tilt and quick movement do not change the pool while it is
hanging; Z smoothly suppresses the effect when the badge is laid flat. If the
accelerometer is not responding, the keys, LEDs, and USB keyboard continue to
work.

## Hardware map

| Function | GPIO |
|---|---|
| 15-pixel WS2812/SK6812 chain | GP21 |
| Matrix rows R0/R1/R2 | GP27, GP26, GP16 |
| Matrix columns C0/C1/C2 | GP17, GP13, GP0 |
| MSA301/GSDA213 SDA/SCL | GP18, GP19 (I2C1) |
| SAO SDA/SCL | GP9, GP10 (software I2C) |
| SAO GPIO | GP29, GP28, GP12, GP11 |

The key scanner drives one column high and reads rows with pull-downs. This
matches the PCB's column → switch → diode → row orientation.

## Firmware structure

```text
software/
├── boot.py          USB serial + HID setup
├── main.py          MicroPython entry point
├── badge.py         keys, long presses, motion, ripples, main loop
├── themes.py        startup rainbow and all nine themes
├── hardware.py      NeoPixels, matrix, accelerometer, and SAO setup
├── key_matrix.py    active-high scanner with software debounce
├── msa301.py        native accelerometer driver
├── color_tools.py   portable RGB math
├── config.py        pins and user-tunable timing/brightness
├── usb_keyboard.py  non-blocking numpad reports
├── serial_menu.py   typed USB-serial console (help/status/theme/brightness/accel/reset/bootloader)
└── lib/usb/         official MicroPython USB device libraries
```

## Serial console

While the badge is running (not just at the REPL), the USB-CDC serial
connection also accepts typed commands — connect with `mpremote connect auto
repl`, Thonny's shell, or any serial terminal, then type `help` and press
Enter for the full command listing (`status`, `theme [n|name]`, `brightness
[0-100]`, `accel`, `reset`, `bootloader`). Typing anything at all before
you've seen the listing prints it automatically. Ctrl-C still drops to the
real MicroPython REPL and kills the running badge script, same as always —
that's unrelated to and unaffected by the console.

## Install on the badge

1. Hold **BOOTSEL** while plugging in the badge. It appears as `RPI-RP2`.
2. Copy the included `firmware/RPI_PICO-20260406-v1.28.0.uf2` onto `RPI-RP2`.
   It is the official stable v1.28 build from
   [micropython.org/download/RPI_PICO](https://micropython.org/download/RPI_PICO/).
3. The badge reboots into MicroPython. Unlike CircuitPython, it does not expose
   a drag-and-drop source drive. Use Thonny or `mpremote` to upload the files.

In Thonny, select **MicroPython (Raspberry Pi Pico)**, then upload every `.py`
file in `software/` to `/` and upload `software/lib/` as `/lib/`.

With `mpremote`:

```sh
cd software
mpremote connect auto fs mkdir :lib
mpremote connect auto fs mkdir :lib/usb
mpremote connect auto fs mkdir :lib/usb/device
mpremote connect auto fs cp *.py :
mpremote connect auto fs cp lib/usb/__init__.py :lib/usb/__init__.py
mpremote connect auto fs cp lib/usb/device/*.py :lib/usb/device/
mpremote connect auto reset
```

From the repository root, `tools/upload_micropython.sh` runs those commands
for you.

If a directory already exists, its `mkdir` command may print an error; continue
with the copy commands. `boot.py` deliberately keeps the serial REPL enabled
while adding the HID keyboard.

## Configuration

Edit `config.py` to change global brightness, long-press time, frame rate, or
pin assignments. Add or modify palettes and renderers in `themes.py`.
`GLOBAL_BRIGHTNESS` is only the boot-time default — the serial console's
`brightness` command can also change it live, without reflashing.

## Verification

Host-side logic tests do not require a badge:

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q software testing tests
```

For physical diagnostics, see [`testing/README.md`](../testing/README.md).

The bundled `lib/usb/` modules come from the official MIT-licensed
`micropython-lib` project; its license is retained under `third_party/`.
