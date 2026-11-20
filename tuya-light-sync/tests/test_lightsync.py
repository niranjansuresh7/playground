import unittest

import numpy as np

from lightsync.analysis import AudioAnalyzer
from lightsync.effects import EFFECTS

SR, BLOCK = 44100, 1024


def kick_track(seconds=6.0, bpm=120):
    """Quiet hi-hat noise with a 60 Hz kick drum every beat."""
    t = np.arange(int(SR * seconds)) / SR
    rng = np.random.default_rng(0)
    audio = 0.02 * rng.standard_normal(t.size)
    for start in np.arange(0, seconds, 60 / bpm):
        i = int(start * SR)
        n = int(0.12 * SR)
        env = np.exp(-np.arange(n) / (0.03 * SR))
        audio[i:i + n] += 0.8 * env * np.sin(2 * np.pi * 60 * np.arange(n) / SR)[: audio[i:i + n].size]
    return audio


def blocks(audio):
    for i in range(0, audio.size - BLOCK, BLOCK):
        yield audio[i:i + BLOCK]


class AnalyzerTests(unittest.TestCase):
    def test_detects_kicks_at_120_bpm(self):
        analyzer = AudioAnalyzer(SR, BLOCK)
        beats = sum(analyzer.process(b).beat for b in blocks(kick_track()))
        # 12 kicks in 6 s; the first ~0.5 s is warm-up.
        self.assertGreaterEqual(beats, 9)
        self.assertLessEqual(beats, 12)

    def test_silence_has_no_beats(self):
        analyzer = AudioAnalyzer(SR, BLOCK)
        features = [analyzer.process(np.zeros(BLOCK)) for _ in range(100)]
        self.assertFalse(any(f.beat for f in features))
        self.assertTrue(all(f.silent for f in features))


class EffectTests(unittest.TestCase):
    def test_colours_stay_in_range(self):
        for name, cls in EFFECTS.items():
            analyzer, effect = AudioAnalyzer(SR, BLOCK), cls()
            for b in blocks(kick_track(3.0)):
                c = effect.update(analyzer.process(b), analyzer.block_dt)
                self.assertTrue(0 <= c.h < 360, name)
                self.assertTrue(0 <= c.s <= 1, name)
                self.assertTrue(0 <= c.v <= 1, name)

    def test_music_mode_changes_colour_on_beats(self):
        analyzer, effect = AudioAnalyzer(SR, BLOCK), EFFECTS["music"]()
        hues = {round(effect.update(analyzer.process(b), analyzer.block_dt).h) for b in blocks(kick_track())}
        self.assertGreater(len(hues), 3)


if __name__ == "__main__":
    unittest.main()
