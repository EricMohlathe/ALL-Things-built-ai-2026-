#!/bin/bash
# Build "GODMODE OS.app" + .dmg from the cockpit/. macOS only, no deps.
set -e
OS="$HOME/ai-tools/trading/godmode-repo/GODMODE_OS"
DASH="$OS/cockpit"
BUILD="$OS/build"
APP="$BUILD/GODMODE OS.app"
rm -rf "$BUILD"; mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp -R "$DASH" "$APP/Contents/Resources/cockpit"
# bundle the FULL Live Runner hub (stdlib only) so the app serves run.html + /api/* (Roster/Trade/Portfolio…)
rsync -a --exclude='.git' --exclude='data' --exclude='logs' --exclude='__pycache__' --exclude='.env' --exclude='*.dmg' \
  "$HOME/ai-tools/trading/openalice-hub/" "$APP/Contents/Resources/hub/" 2>/dev/null || true
cp -R "$OS/../GODMODE_App" "$APP/Contents/Resources/GODMODE_App" 2>/dev/null || true

ICONSET="$BUILD/AppIcon.iconset"; mkdir -p "$ICONSET"
for s in 16 32 128 256 512; do
  sips -z $s $s "$DASH/icon-1024.png" --out "$ICONSET/icon_${s}x${s}.png" >/dev/null
  d=$((s*2)); sips -z $d $d "$DASH/icon-1024.png" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/AppIcon.icns"; rm -rf "$ICONSET"

cat > "$APP/Contents/MacOS/launcher" <<'SH'
#!/bin/bash
DIR="$(cd "$(dirname "$0")/../Resources" && pwd)"
PORT=7870
URL="http://127.0.0.1:$PORT/run.html"
HUB="$DIR/hub"
PY=""; for p in /usr/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3; do [ -x "$p" ] && PY="$p" && break; done
[ -z "$PY" ] && { open "$DIR/cockpit/index.html"; exit 0; }
SRV=""
if ! curl -s -o /dev/null "$URL" 2>/dev/null; then
  # serve the full Live Runner: run.html + /api/* (Roster/Trade/Portfolio/Systems/Coverage)
  ( cd "$HUB" && PYTHONPATH="$HUB" exec "$PY" -c "from openalice_hub import server; server.serve($PORT)" >/tmp/godmode_os.log 2>&1 ) &
  SRV=$!
  for i in $(seq 1 50); do curl -s -o /dev/null "$URL" 2>/dev/null && break; sleep 0.2; done
fi
open "$URL"
[ -n "$SRV" ] && wait $SRV
SH
chmod +x "$APP/Contents/MacOS/launcher"

cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
 <key>CFBundleName</key><string>GODMODE OS</string>
 <key>CFBundleDisplayName</key><string>GODMODE OS</string>
 <key>CFBundleIdentifier</key><string>com.ericmohlathe.godmode.os</string>
 <key>CFBundleExecutable</key><string>launcher</string>
 <key>CFBundleIconFile</key><string>AppIcon</string>
 <key>CFBundlePackageType</key><string>APPL</string>
 <key>CFBundleVersion</key><string>1.0</string>
 <key>CFBundleShortVersionString</key><string>1.0</string>
 <key>LSMinimumSystemVersion</key><string>11.0</string>
 <key>NSHighResolutionCapable</key><true/>
</dict></plist>
PLIST

codesign --force --deep -s - "$APP" 2>/dev/null && echo "ad-hoc signed" || echo "codesign skipped"
STAGE="$BUILD/dmg-stage"; mkdir -p "$STAGE"; cp -R "$APP" "$STAGE/"; ln -s /Applications "$STAGE/Applications"
DMG="$OS/GODMODE-OS.dmg"; rm -f "$DMG"
hdiutil create -volname "GODMODE OS" -srcfolder "$STAGE" -ov -format UDZO "$DMG" >/dev/null
rm -rf "$STAGE"
echo "DMG: $DMG ($(du -h "$DMG" | cut -f1))"
