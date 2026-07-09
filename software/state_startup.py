import time
from rainbowio import colorwheel
from setup import pixels, NUM_PIXELS
from setup import keys
from state import State

# Diagonal sweep groups: LEDs lit per phase, top-left → bottom-right
# Key LED diagonal = row + col for LED index i: row = i//3, col = i%3
_DIAG_LEDS = [
    [0],          # phase 0 — C0R0
    [1, 3],       # phase 1 — C1R0, C0R1
    [2, 4, 6],    # phase 2 — C2R0, C1R1, C0R2
    [5, 7],       # phase 3 — C2R1, C1R2
    [8],          # phase 4 — C2R2
    [9, 10],      # phase 5 — right backlights
    [11, 12],     # phase 6 — bottom backlights
    [13, 14],     # phase 7 — left backlights
]

_PHASE_DURATION = 0.14   # seconds per diagonal step
_HOLD_DURATION  = 0.5    # hold all lit before fading out
_FADE_DURATION  = 0.4    # fade to black before transitioning
_NUM_PHASES = len(_DIAG_LEDS)


class StartupState(State):

    @property
    def name(self):
        return "startup"

    def __init__(self):
        self.phase = 0
        self.phase_start = 0.0
        self.base_hue = 0
        self.stage = "sweep"   # "sweep" | "hold" | "fade"

    def enter(self, machine):
        self.phase = 0
        self.phase_start = time.monotonic()
        self.base_hue = 0
        self.stage = "sweep"
        pixels.fill((0, 0, 0))
        pixels.show()
        State.enter(self, machine)

    def exit(self, machine):
        pixels.fill((0, 0, 0))
        pixels.show()
        State.exit(self, machine)

    def update(self, machine):
        # Any keypress skips straight to the badge state
        event = keys.events.get()
        if event and event.pressed:
            machine.go_to_state("badge")
            return

        now = time.monotonic()
        elapsed = now - self.phase_start

        if self.stage == "sweep":
            if elapsed >= _PHASE_DURATION:
                self.phase += 1
                self.phase_start = now
                elapsed = 0.0
                if self.phase >= _NUM_PHASES:
                    self.stage = "hold"
                    return

            # Render all lit phases so far
            pixels.fill((0, 0, 0))
            for p in range(min(self.phase + 1, _NUM_PHASES)):
                age = self.phase - p
                hue = (self.base_hue + p * 30) % 256
                color = colorwheel(hue)
                # Older diagonals fade gently
                fade = max(0.35, 1.0 - age * 0.10)
                faded = tuple(int(c * fade) for c in color)
                for led in _DIAG_LEDS[p]:
                    pixels[led] = faded
            pixels.show()

            # Advance hue each frame for a rolling rainbow feel
            self.base_hue = (self.base_hue + 2) % 256

        elif self.stage == "hold":
            if elapsed >= _HOLD_DURATION:
                self.stage = "fade"
                self.phase_start = now

        elif self.stage == "fade":
            if elapsed >= _FADE_DURATION:
                machine.go_to_state("badge")
                return
            # Linearly dim everything to black
            t = elapsed / _FADE_DURATION
            for i in range(NUM_PIXELS):
                r, g, b = pixels[i]
                pixels[i] = (int(r * (1 - t)), int(g * (1 - t)), int(b * (1 - t)))
            pixels.show()
