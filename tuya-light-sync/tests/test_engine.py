import sys
import time
import types
import unittest
from unittest import mock

import numpy as np

from lightsync import engine as engine_mod
from lightsync.config import bulb_config_problems
from lightsync.engine import SyncEngine, SyncError

from .test_lightsync import BLOCK, SR, kick_track


class FakeStream:
    def __init__(self, audio, **kwargs):
        self.audio, self.pos, self.channels = audio, 0, kwargs["channels"]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, n):
        chunk = self.audio[self.pos:self.pos + n]
        self.pos = (self.pos + n) % (self.audio.size - n)
        time.sleep(0.001)
        return np.repeat(chunk[:, None], self.channels, axis=1).astype("float32"), False


def fake_sounddevice(devices):
    audio = kick_track(2.0)
    return types.SimpleNamespace(
        query_devices=lambda: devices,
        InputStream=lambda **kw: FakeStream(audio, **kw),
    )


BLACKHOLE = {"name": "BlackHole 2ch", "max_input_channels": 2, "default_samplerate": SR}


class RecordingLight:
    def __init__(self, *a, **kw):
        self.colors, self.closed = [], False

    def set_color(self, c):
        self.colors.append(c)

    def close(self):
        self.closed = True


class EngineTests(unittest.TestCase):
    def test_runs_in_background_and_switches_mode(self):
        light = RecordingLight()
        sd = fake_sounddevice([{"name": "Mic", "max_input_channels": 1, "default_samplerate": SR}, BLACKHOLE])
        with mock.patch.dict(sys.modules, {"sounddevice": sd}), \
             mock.patch.object(engine_mod, "TuyaLight", lambda *a, **kw: light):
            eng = SyncEngine({"device_id": "x", "ip": "1.2.3.4", "local_key": "k" * 16})
            eng.start()
            time.sleep(0.2)
            eng.set_mode("movie")
            eng.set_sensitivity(1.2)
            time.sleep(0.1)
            self.assertTrue(eng.running)
            eng.stop()
        self.assertFalse(eng.running)
        self.assertTrue(light.closed)
        self.assertGreater(len(light.colors), 10)
        self.assertEqual(eng.device_name, "BlackHole 2ch")

    def test_missing_blackhole_is_a_readable_error(self):
        sd = fake_sounddevice([{"name": "Mic", "max_input_channels": 1, "default_samplerate": SR}])
        with mock.patch.dict(sys.modules, {"sounddevice": sd}):
            with self.assertRaises(SyncError):
                SyncEngine({}).start()

    def test_config_problems(self):
        good = {"device_id": "abc", "ip": "192.168.1.12", "local_key": "l" * 16}
        self.assertEqual(bulb_config_problems(good), [])
        bad = dict(good, ip="1192.168.1.12", local_key="short")
        self.assertEqual(len(bulb_config_problems(bad)), 2)


if __name__ == "__main__":
    unittest.main()
