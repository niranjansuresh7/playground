"""The sync loop: audio in, colours out. Shared by the command line and the menu bar app."""

import threading

from .analysis import AudioAnalyzer
from .effects import EFFECTS
from .light import ConsoleLight, TuyaLight


class SyncError(Exception):
    pass


def find_input_device(sd, name_hint):
    for index, dev in enumerate(sd.query_devices()):
        if name_hint.lower() in dev["name"].lower() and dev["max_input_channels"] > 0:
            return index, dev
    raise SyncError(
        f"No audio input matching '{name_hint}'. Check BlackHole is installed, "
        "or set \"audio_device\" in config.json."
    )


class SyncEngine:
    """Owns the bulb connection and the audio stream.

    `run()` blocks until `stop()` is called; `start()` runs it on a background thread.
    Mode and sensitivity can be changed while it runs.
    """

    def __init__(self, config, mode="music", sensitivity=None, max_rate=None, dry_run=False):
        if mode not in EFFECTS:
            raise ValueError(f"unknown mode {mode!r}")
        self.config = config
        self.dry_run = dry_run
        self.sensitivity = sensitivity or config.get("sensitivity", 1.4)
        self.max_rate = max_rate or config.get("max_rate", 10)
        self._mode = mode
        self._effect = EFFECTS[mode]()
        self._analyzer = None
        self._stop = threading.Event()
        self._thread = None
        self.error = None  # set if the background thread fails
        self.device_name = None

    # --- live controls -------------------------------------------------
    @property
    def mode(self):
        return self._mode

    def set_mode(self, mode):
        self._effect = EFFECTS[mode]()
        self._mode = mode

    def set_sensitivity(self, value):
        self.sensitivity = value
        if self._analyzer is not None:
            self._analyzer.sensitivity = value

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    # --- lifecycle -----------------------------------------------------
    def connect(self):
        """Open the bulb and find the audio device. Raises SyncError with a readable message."""
        import sounddevice as sd

        index, device = find_input_device(sd, self.config.get("audio_device", "BlackHole"))
        if self.dry_run:
            light = ConsoleLight()
        else:
            try:
                light = TuyaLight(
                    self.config["device_id"], self.config["ip"], self.config["local_key"],
                    version=self.config.get("version", 3.3), max_rate=self.max_rate,
                )
            except RuntimeError as exc:
                raise SyncError(str(exc)) from exc
        return sd, index, device, light

    def run(self, connection=None):
        sd, index, device, light = connection or self.connect()
        samplerate = int(device["default_samplerate"])
        blocksize = 1024 if samplerate <= 48000 else 2048
        channels = min(2, device["max_input_channels"])
        self._analyzer = AudioAnalyzer(samplerate, blocksize, sensitivity=self.sensitivity)
        self.device_name = device["name"]
        self._stop.clear()
        try:
            with sd.InputStream(device=index, channels=channels, samplerate=samplerate,
                                blocksize=blocksize, dtype="float32") as stream:
                while not self._stop.is_set():
                    block, _overflowed = stream.read(blocksize)
                    features = self._analyzer.process(block.mean(axis=1))
                    light.set_color(self._effect.update(features, self._analyzer.block_dt))
        finally:
            light.close()

    def start(self):
        """Connect now (so errors surface to the caller), then sync on a background thread."""
        if self.running:
            return
        self.error = None
        connection = self.connect()

        def target():
            try:
                self.run(connection)
            except Exception as exc:  # reported to the UI via self.error
                self.error = exc

        self._thread = threading.Thread(target=target, name="lightsync", daemon=True)
        self._thread.start()

    def stop(self, timeout=2.0):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout)
            self._thread = None
