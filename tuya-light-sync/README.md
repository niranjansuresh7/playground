# tuya-light-sync

Make a Wipro (Tuya) Wi‑Fi bulb react to whatever your MacBook is playing:
music, movies, or background sound while you work.

| Mode    | What it does                                                         |
|---------|----------------------------------------------------------------------|
| `music` | Jumps to a new colour and flashes on every beat                      |
| `movie` | Smooth mood lighting from the soundtrack, flashes on big hits         |
| `chill` | Slow, gentle colour drift that breathes with the sound (for working) |

How it works: BlackHole hands your Mac's audio to the script, the script finds
beats and loudness, and sends colours **directly to the bulb over your home
Wi‑Fi** (via [tinytuya](https://github.com/jasonacox/tinytuya)). The Tuya cloud
is only used once, to fetch the bulb's local key. The cloud is too slow for
beat sync.

## 1. Install

You need Python 3.9+ on the Mac.

```bash
cd playground/tuya-light-sync
```

```bash
python3 -m venv .venv
```

```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

## 2. Hear the sound and send it to BlackHole

BlackHole on its own swallows the audio, so you'd hear nothing. Make a device
that plays to your speakers *and* BlackHole at the same time:

1. Open **Audio MIDI Setup** (Spotlight → "Audio MIDI Setup").
2. Click **+** at the bottom left → **Create Multi-Output Device**.
3. Tick **MacBook Pro Speakers** (or your headphones) **and** **BlackHole 2ch**.
   Put your speakers first and set them as the clock source (Primary Device).
4. Tick **Drift Correction** for BlackHole 2ch.
5. Go to **System Settings → Sound → Output** and choose the **Multi-Output Device**.

Note: macOS doesn't let you change the volume of a Multi-Output Device with the
keyboard. Set it in the app (Spotify, YouTube, VLC) instead, or switch output
back to your speakers when you're not using the light.

## 3. Get your bulb's local key

You already created the Tuya cloud project and linked your app, so:

```bash
python -m tinytuya wizard
```

Enter your cloud project's **Access ID** and **Access Secret** (Tuya IoT
Platform → your project → Overview), pick your data centre region (India
accounts are usually **in**), and say **Y** to scanning the network. When it
finishes it writes `devices.json` and `snapshot.json` in this folder.

From those files, note your bulb's:

- `id` → `device_id`
- `key` → `local_key`
- `ip` (in `snapshot.json`) → `ip`
- `ver` (in `snapshot.json`) → `version` (usually 3.3, 3.4 or 3.5)

Then:

```bash
cp config.example.json config.json
```

and paste those four values into `config.json`. `config.json` and the wizard
files are in `.gitignore`. **Never commit them**: the local key lets anyone on
your network control the bulb.

Tip: give the bulb a fixed IP in your router (DHCP reservation) so the IP in
`config.json` doesn't change.

## 4. Run it

Check the Mac sees BlackHole:

```bash
python -m lightsync --list-devices
```

Try it without the bulb first (shows a colour bar in the terminal):

```bash
python -m lightsync --dry-run --mode music
```

Then for real:

```bash
python -m lightsync --mode music
```

```bash
python -m lightsync --mode movie
```

```bash
python -m lightsync --mode chill
```

Press **Ctrl+C** to stop; the bulb goes back to a warm glow.

## 5. Menu bar app (no Terminal needed)

Build it once:

```bash
./macos/build_app.sh
```

This creates **LightSync.app** in your `Applications` folder (inside your
home folder). Open it from Spotlight (Cmd+Space → "LightSync") and a 🔅 appears
in the menu bar at the top right. Click it to:

- **Start / Stop** syncing (the icon turns 💡 while it's running)
- pick a **Mode**: Music, Movie or Chill (switches instantly, no restart)
- set **Beat sensitivity**: More beats / Normal / Fewer beats
- **Start syncing when app opens**: on by default
- **Edit bulb settings…**: opens `config.json`

Your choices are remembered next time.

**Start it automatically when you log in:** System Settings → General →
Login Items → **+** under "Open at Login" → pick LightSync from your home
folder's Applications.

The first time it starts, macOS asks whether LightSync can use the
microphone. Click **Allow**: that's how it hears BlackHole. If the light
doesn't react to sound, check System Settings → Privacy & Security →
Microphone and turn on LightSync (or Python).

If something goes wrong, the app shows a message; details are in
`~/Library/Logs/LightSync.log`.

The app runs the code in this folder, so after `git pull` just quit and
reopen it. Re-run `build_app.sh` only if you move the folder or
`requirements.txt` changes.

## Tuning

| Problem                                   | Fix                                                    |
|-------------------------------------------|--------------------------------------------------------|
| Misses beats                              | `--sensitivity 1.2` (lower = more beats)               |
| Flashes on things that aren't beats       | `--sensitivity 1.7`                                    |
| Bulb lags, stutters or stops responding   | `--max-rate 6` (fewer updates per second)              |
| "Could not reach the bulb"                | Check IP/key/version; Mac and bulb on the same Wi‑Fi; close the Wipro app on your phone (some bulbs allow only one local connection) |

The bulb itself fades a little between colours, so very fast music won't be
perfectly sharp. That's the hardware, not the script.

## Tests

```bash
python -m unittest -v
```

## Files

- `lightsync/analysis.py`: beat and loudness detection from audio
- `lightsync/effects.py`: the `music`, `movie` and `chill` modes
- `lightsync/light.py`: talks to the bulb (or the terminal preview)
- `lightsync/engine.py`: the sync loop (shared by the app and the command line)
- `lightsync/menubar.py`: the menu bar app
- `lightsync/config.py`: reads and checks `config.json`
- `lightsync/__main__.py`: command line entry point
- `macos/build_app.sh`: builds `LightSync.app`
