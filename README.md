```
___  ____     _____  ______           _            
|  \/  | |   |  _  | | ___ \         | |           
| .  . | | __| |_| | | |_/ / __ _  __| | __ _  ___ 
| |\/| | |/ /\____ | | ___ \/ _` |/ _` |/ _` |/ _ \
| |  | |   < .___/ / | |_/ / (_| | (_| | (_| |  __/
\_|  |_/_|\_\\____/  \____/ \__,_|\__,_|\__, |\___|
                                         __/ |     
                                        |___/      
-------------------------------------------------
D C Z I A  ----------  2 0 2 6
```

DCZia Presents: The MK9 Badge

It blinks. It types. You can wear it around your neck and then set it on your desk and actually use it\*.

\* _Desk productivity not guaranteed. DCZia assumes no responsibility for keys accidentally sent during badge parties. Consult your keyboard layer documentation before operating heavy machinery._

---

## About

The **MK9** is a fully functional **3×3 mechanical macropad badge**. Nine real mechanical switches, per-key RGB lighting, ambient underglow, an accelerometer that actually does something interesting, SAO support, and MicroPython firmware — all in a package sized to hang around your neck at DEF CON and survive the week.

---

## Specs

**Keys**
- 9× mechanical switches in a 3×3 grid — standard MX footprint, swap keycaps as you please
- Ships with translucent blue keycaps
- USB HID numpad when plugged into a computer

**Lighting**
- 9× WS2812B per-key RGB LEDs — one under each switch
- 6× SK6812 side-firing LEDs — edge-mounted for ambient underglow out the sides

**Brains & Sensors**
- RP2040 microcontroller
- 3-axis accelerometer — movement and tilt steer the lighting intensity
- 2× SAO connectors (standard 6-pin, I2C + 2 GPIO each) — expand with the badge add-on ecosystem

**Power & I/O**
- USB-C — power and data
- 3× AAA battery pack — run it untethered
- Power switch for battery mode
- Reset button + BOOTSEL button for easy firmware flashing

**Firmware**
- Native MicroPython firmware with bundled USB HID support
- QMK-compatible hardware — reflash and run it as a full QMK macropad

---

## What It Does Out of the Box

On boot: a smoothly fading rainbow flows across all keys and backlights, then
cross-fades into the active theme.

Once running:
- Nine spatial color themes animate all 15 LEDs — one theme for each key
- Pressing a key makes a white-hot impact and a colour ripple that expands across the whole board
- Long-press a key to select its theme; movement gently flows brightness across it
- Plug into a computer and it shows up as a numpad (7–9 / 4–6 / 1–3 layout)

---

## Repository

```
mk9-badge/
├── hardware/   — KiCad design files, BOM, fabrication outputs
└── software/   — MicroPython firmware
```

- [Hardware →](hardware/README.md) — schematics, PCB layout, drill files, BOM
- [Software →](software/README.md) — firmware architecture, pinout, library requirements, flashing instructions

**Fabrication outputs**:
- [PCB layer plot](hardware/output/mk9-badge.pdf)
- [PTH drill map](hardware/output/mk9-badge-PTH-drl_map.pdf)
- [NPTH drill map](hardware/output/mk9-badge-NPTH-drl_map.pdf)

---

## Programming / Updating

The badge runs [MicroPython](https://micropython.org). To install or update it:

1. Hold **BOOTSEL** while plugging the badge into your computer — it mounts as `RPI-RP2`.
2. Drag [`firmware/RPI_PICO-20260406-v1.28.0.uf2`](firmware/RPI_PICO-20260406-v1.28.0.uf2)
   onto the drive.
3. Use Thonny or `mpremote` to upload the `software/*.py` files to `/` and
   `software/lib/` to `/lib/` on the badge.

Full commands and the recommended firmware version are in the
[software flashing guide](software/README.md#install-on-the-badge).

Want to run QMK instead? The hardware is fully compatible; QMK setup instructions will be posted separately.

**Recommended tool:** [Thonny](https://thonny.org), which can edit and upload
files directly through the MicroPython serial connection.

---

## Open Source

DCZia is committed to open source hardware and software. All design files and firmware are publicly available.

- **Live CAD (OnShape):** [View the design](https://cad.onshape.com/documents/36884624fbe35c16a5af61a7/w/233227193d278274727a44c3/e/ea987b4b53c4648fa3dc84b6)
