#!/bin/bash
# Builds ~/Applications/LightSync.app: a menu bar app that runs this project's code.
# Re-run it any time; after `git pull` you don't need to, since the app uses this folder's code.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$PROJECT_DIR/.venv/bin/python"
APP="$HOME/Applications/LightSync.app"

if [ ! -x "$PYTHON" ]; then
  echo "Setting up Python environment in $PROJECT_DIR/.venv ..."
  python3 -m venv "$PROJECT_DIR/.venv"
fi
echo "Installing/updating packages ..."
"$PYTHON" -m pip install --quiet --prefer-binary --timeout 60 --retries 8 -r "$PROJECT_DIR/requirements.txt"

echo "Building $APP ..."
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources" "$HOME/Library/Logs"

cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>LightSync</string>
  <key>CFBundleDisplayName</key><string>LightSync</string>
  <key>CFBundleIdentifier</key><string>local.lightsync.menubar</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleExecutable</key><string>LightSync</string>
  <key>LSUIElement</key><true/>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
  <key>NSMicrophoneUsageDescription</key>
  <string>LightSync listens to the BlackHole audio device to sync your light to music and movies.</string>
</dict>
</plist>
PLIST

cat > "$APP/Contents/MacOS/LightSync" <<LAUNCHER
#!/bin/bash
cd "$PROJECT_DIR"
exec "$PYTHON" -m lightsync.menubar >> "\$HOME/Library/Logs/LightSync.log" 2>&1
LAUNCHER
chmod +x "$APP/Contents/MacOS/LightSync"

# Ad-hoc signature so macOS remembers the microphone permission.
codesign --force --deep --sign - "$APP" >/dev/null 2>&1 || true

echo
echo "Done! Open it with:  open \"$APP\""
echo "Look for 🔅/💡 in the menu bar (top right). Logs: ~/Library/Logs/LightSync.log"
