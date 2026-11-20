"""Sync a Tuya (Wipro) Wi-Fi bulb to whatever your Mac is playing.

    python -m lightsync --mode music
    python -m lightsync --mode movie
    python -m lightsync --mode chill
    python -m lightsync --list-devices
    python -m lightsync --dry-run      # preview in the terminal, no bulb needed
"""

import argparse
import json
import sys
from pathlib import Path

from .analysis import AudioAnalyzer
from .effects import EFFECTS
from .light import ConsoleLight, TuyaLight

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "config.json"


def find_input_device(sd, name_hint):
    for index, dev in enumerate(sd.query_devices()):
        if name_hint.lower() in dev["name"].lower() and dev["max_input_channels"] > 0:
            return index, dev
    sys.exit(
        f"No input device matching '{name_hint}'. Run with --list-devices to see what's "
        "available, then set \"audio_device\" in config.json."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mode", choices=sorted(EFFECTS), default="music")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--dry-run", action="store_true", help="show colours in the terminal instead of the bulb")
    parser.add_argument("--list-devices", action="store_true", help="list audio devices and exit")
    parser.add_argument("--sensitivity", type=float, help="beat threshold; lower = more beats (default 1.4)")
    parser.add_argument("--max-rate", type=float, help="max bulb updates per second (default 10)")
    args = parser.parse_args()

    import sounddevice as sd

    if args.list_devices:
        print(sd.query_devices())
        return

    config = json.loads(args.config.read_text()) if args.config.exists() else {}
    if not args.dry_run and not config.get("local_key"):
        sys.exit(f"Missing bulb details. Copy config.example.json to {args.config} and fill it in.")

    sensitivity = args.sensitivity or config.get("sensitivity", 1.4)
    max_rate = args.max_rate or config.get("max_rate", 10)

    index, device = find_input_device(sd, config.get("audio_device", "BlackHole"))
    samplerate = int(device["default_samplerate"])
    blocksize = 1024 if samplerate <= 48000 else 2048
    channels = min(2, device["max_input_channels"])

    analyzer = AudioAnalyzer(samplerate, blocksize, sensitivity=sensitivity)
    effect = EFFECTS[args.mode]()

    if args.dry_run:
        light = ConsoleLight()
    else:
        light = TuyaLight(
            config["device_id"], config["ip"], config["local_key"],
            version=config.get("version", 3.3), max_rate=max_rate,
        )

    print(f"Listening on '{device['name']}' at {samplerate} Hz, mode={args.mode}. Ctrl+C to stop.")
    try:
        with sd.InputStream(device=index, channels=channels, samplerate=samplerate,
                            blocksize=blocksize, dtype="float32") as stream:
            while True:
                block, _overflowed = stream.read(blocksize)
                features = analyzer.process(block.mean(axis=1))
                light.set_color(effect.update(features, analyzer.block_dt))
    except KeyboardInterrupt:
        pass
    finally:
        light.close()


if __name__ == "__main__":
    main()
