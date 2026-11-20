"""Effects turn audio features into a bulb colour (hue 0-360, sat 0-1, value 0-1)."""

import math
import random
from dataclasses import dataclass

from .analysis import Features


@dataclass
class Color:
    h: float  # 0..360
    s: float  # 0..1
    v: float  # 0..1


def _approach(current, target, dt, tau):
    """Exponential smoothing: move `current` toward `target` with time constant `tau`."""
    if tau <= 0:
        return target
    return current + (target - current) * (1 - math.exp(-dt / tau))


class MusicEffect:
    """Party mode: jump to a new colour and flash on every beat."""

    PALETTE = [0, 30, 55, 120, 175, 210, 260, 300, 330]

    def __init__(self, floor=0.08):
        self.floor = floor
        self.index = 0
        self.flash = 0.0
        self.level = 0.0

    def update(self, f: Features, dt) -> Color:
        if f.beat:
            self.index = (self.index + random.randint(1, len(self.PALETTE) - 1)) % len(self.PALETTE)
            self.flash = 0.6 + 0.4 * f.beat_strength
        self.flash = _approach(self.flash, 0.0, dt, 0.18)
        self.level = _approach(self.level, f.loudness, dt, 0.08)

        hue = (self.PALETTE[self.index] + 20 * (f.brightness - 0.5)) % 360
        v = max(self.flash, self.floor + (0.55 - self.floor) * self.level)
        return Color(hue, 1.0, min(v, 1.0))


class MovieEffect:
    """Ambient mode: smooth mood colours that follow the soundtrack, flash on big hits."""

    WARM, COOL = 15.0, 225.0  # deep orange for rumbles, blue for bright/airy scenes

    def __init__(self, floor=0.05):
        self.floor = floor
        self.hue = self.WARM
        self.level = 0.0
        self.flash = 0.0

    def update(self, f: Features, dt) -> Color:
        target_hue = self.WARM + (self.COOL - self.WARM) * f.brightness
        self.hue = _approach(self.hue, target_hue, dt, 1.2)

        target = 0.0 if f.silent else f.loudness
        tau = 0.12 if target > self.level else 0.8  # quick rise, slow fade
        self.level = _approach(self.level, target, dt, tau)

        if f.beat and f.beat_strength > 0.6 and f.bass > 0.7:
            self.flash = 1.0  # explosions, drum hits in the score
        self.flash = _approach(self.flash, 0.0, dt, 0.25)

        v = self.floor + (0.75 - self.floor) * self.level
        v = max(v, self.flash)
        s = 0.9 - 0.6 * self.flash  # flashes go towards white
        return Color(self.hue % 360, s, min(v, 1.0))


class ChillEffect:
    """Work mode: slow colour drift that breathes gently with the music."""

    def __init__(self, floor=0.2):
        self.floor = floor
        self.hue = random.uniform(0, 360)
        self.level = 0.0

    def update(self, f: Features, dt) -> Color:
        self.level = _approach(self.level, f.loudness, dt, 1.5)
        self.hue = (self.hue + dt * (3 + 10 * self.level)) % 360
        v = self.floor + 0.3 * self.level
        return Color(self.hue, 0.75, v)


EFFECTS = {"music": MusicEffect, "movie": MovieEffect, "chill": ChillEffect}
