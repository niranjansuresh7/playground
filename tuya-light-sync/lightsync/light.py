"""Outputs: the real Tuya bulb (local Wi-Fi) or a terminal preview."""

import sys
import time
import colorsys

from .effects import Color


class _Throttle:
    """Skip updates that come too fast or barely change the colour."""

    def __init__(self, max_rate):
        self.min_interval = 1.0 / max_rate
        self.last_time = 0.0
        self.last = None

    def ready(self, c: Color):
        now = time.monotonic()
        if now - self.last_time < self.min_interval:
            return False
        if self.last is not None:
            dh = abs((c.h - self.last.h + 180) % 360 - 180)
            if dh < 3 and abs(c.s - self.last.s) < 0.03 and abs(c.v - self.last.v) < 0.02:
                return False
        self.last_time, self.last = now, c
        return True


class TuyaLight:
    """Controls the bulb directly over your home network (no cloud round-trip)."""

    def __init__(self, device_id, ip, local_key, version=3.3, max_rate=10):
        import tinytuya

        self.dev = tinytuya.BulbDevice(device_id, ip, local_key, version=float(version))
        self.dev.set_socketPersistent(True)
        status = self.dev.status()
        if not status or "Error" in status:
            raise RuntimeError(
                f"Could not reach the bulb at {ip}: {status}. "
                "Check the IP, local_key and version in config.json, and that the "
                "laptop and bulb are on the same Wi-Fi."
            )
        self.dev.set_hsv(0, 0, 0.3)  # switch to colour mode once
        self.throttle = _Throttle(max_rate)

    def set_color(self, c: Color):
        if not self.throttle.ready(c):
            return False
        # Tuya rejects brightness 0, so keep a tiny minimum.
        self.dev.set_hsv(c.h / 360.0, c.s, max(c.v, 0.01), nowait=True)
        return True

    def close(self):
        try:
            self.dev.set_hsv(30 / 360.0, 0.6, 0.4)  # leave a calm warm glow
            self.dev.close()
        except Exception:
            pass


class ConsoleLight:
    """Dry run: shows the colour as a bar in the terminal instead of driving the bulb."""

    def __init__(self, max_rate=30):
        self.throttle = _Throttle(max_rate)

    def set_color(self, c: Color):
        if not self.throttle.ready(c):
            return False
        r, g, b = (int(x * 255) for x in colorsys.hsv_to_rgb(c.h / 360, c.s, c.v))
        bar = "█" * int(c.v * 40)
        sys.stdout.write(f"\r\x1b[38;2;{r};{g};{b}m{bar:<40}\x1b[0m h={c.h:5.0f} v={c.v:.2f} ")
        sys.stdout.flush()
        return True

    def close(self):
        sys.stdout.write("\n")
