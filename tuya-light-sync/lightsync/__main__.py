"""Sync a Tuya (Wipro) Wi-Fi bulb to whatever your Mac is playing.

    python -m lightsync --mode music
    python -m lightsync --mode movie
    python -m lightsync --mode chill
    python -m lightsync --list-devices
    python -m lightsync --dry-run      # preview in the terminal, no bulb needed

For the menu bar app, see `python -m lightsync.menubar` and macos/build_app.sh.
"""

import argparse
import sys
from pathlib import Path

from .config import DEFAULT_CONFIG, bulb_config_problems, load_config
from .effects import EFFECTS
from .engine import SyncEngine, SyncError


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mode", choices=sorted(EFFECTS), default="music")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--dry-run", action="store_true", help="show colours in the terminal instead of the bulb")
    parser.add_argument("--list-devices", action="store_true", help="list audio devices and exit")
    parser.add_argument("--sensitivity", type=float, help="beat threshold; lower = more beats (default 1.4)")
    parser.add_argument("--max-rate", type=float, help="max bulb updates per second (default 10)")
    args = parser.parse_args()

    if args.list_devices:
        import sounddevice as sd

        print(sd.query_devices())
        return

    config = load_config(args.config)
    if not args.dry_run:
        problems = bulb_config_problems(config)
        if problems:
            sys.exit(f"Problems in {args.config}:\n  - " + "\n  - ".join(problems))

    engine = SyncEngine(config, mode=args.mode, sensitivity=args.sensitivity,
                        max_rate=args.max_rate, dry_run=args.dry_run)
    try:
        connection = engine.connect()
        print(f"Listening on '{connection[2]['name']}', mode={args.mode}. Ctrl+C to stop.")
        engine.run(connection)
    except SyncError as exc:
        sys.exit(str(exc))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
