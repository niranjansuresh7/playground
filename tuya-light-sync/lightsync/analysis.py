"""Turn raw audio blocks into simple features: loudness, bands, beats."""

from collections import deque
from dataclasses import dataclass

import numpy as np

SILENCE_RMS = 1e-4


@dataclass
class Features:
    loudness: float = 0.0       # 0..1, auto-gain normalised
    bass: float = 0.0           # 0..1
    mid: float = 0.0            # 0..1
    treble: float = 0.0         # 0..1
    brightness: float = 0.0     # 0..1, "colour" of the sound (low = warm, high = bright)
    beat: bool = False
    beat_strength: float = 0.0  # 0..1
    silent: bool = True


class _AutoGain:
    """Tracks a slowly decaying peak so quiet and loud songs both use the full range."""

    def __init__(self, block_dt, half_life=8.0, floor=1e-9):
        self.decay = 0.5 ** (block_dt / half_life)
        self.peak = floor
        self.floor = floor

    def __call__(self, value):
        self.peak = max(value, self.peak * self.decay, self.floor)
        return min(value / self.peak, 1.0)


class AudioAnalyzer:
    BANDS = {"bass": (20, 150), "mid": (150, 2000), "treble": (2000, 10000)}

    def __init__(self, samplerate, blocksize, sensitivity=1.4, min_beat_interval=0.25):
        self.samplerate = samplerate
        self.blocksize = blocksize
        self.block_dt = blocksize / samplerate
        self.sensitivity = sensitivity
        self.min_beat_interval = min_beat_interval

        self._window = np.hanning(blocksize)
        self._freqs = np.fft.rfftfreq(blocksize, 1 / samplerate)
        self._masks = {
            name: (self._freqs >= lo) & (self._freqs < hi)
            for name, (lo, hi) in self.BANDS.items()
        }
        self._gains = {name: _AutoGain(self.block_dt) for name in (*self.BANDS, "loudness")}

        # ~1 second of bass history for the adaptive beat threshold.
        self._history = deque(maxlen=max(4, int(round(1.0 / self.block_dt))))
        self._time = 0.0
        self._last_beat = -1e9

    def process(self, samples):
        """Analyse one mono block of float samples in -1..1."""
        samples = np.asarray(samples, dtype=np.float64)
        self._time += self.block_dt

        rms = float(np.sqrt(np.mean(samples ** 2))) if samples.size else 0.0
        if rms < SILENCE_RMS:
            self._history.append(0.0)
            return Features()

        spectrum = np.abs(np.fft.rfft(samples * self._window, n=self.blocksize)) ** 2
        energies = {name: float(spectrum[mask].sum()) for name, mask in self._masks.items()}

        total = float(spectrum.sum()) or 1e-12
        centroid = float((self._freqs * spectrum).sum() / total)
        lo, hi = np.log(100.0), np.log(8000.0)
        tone = float(np.clip((np.log(max(centroid, 1.0)) - lo) / (hi - lo), 0.0, 1.0))

        beat, strength = self._detect_beat(energies["bass"])

        return Features(
            loudness=self._gains["loudness"](rms),
            bass=self._gains["bass"](energies["bass"]),
            mid=self._gains["mid"](energies["mid"]),
            treble=self._gains["treble"](energies["treble"]),
            brightness=tone,
            beat=beat,
            beat_strength=strength,
            silent=False,
        )

    def _detect_beat(self, bass_energy):
        history = self._history
        ready = len(history) >= history.maxlen // 2
        average = float(np.mean(history)) if history else 0.0
        history.append(bass_energy)

        if not ready or average <= 0:
            return False, 0.0
        ratio = bass_energy / average
        if ratio < self.sensitivity:
            return False, 0.0
        if self._time - self._last_beat < self.min_beat_interval:
            return False, 0.0

        self._last_beat = self._time
        strength = float(np.clip((ratio - self.sensitivity) / self.sensitivity, 0.0, 1.0))
        return True, max(strength, 0.2)
