#!/bin/bash
# Build "OpenAlice Hub.app" + .dmg from dashboard/. macOS only, no deps.
set -e
HUB="$HOME/ai-tools/trading/openalice-hub"
DASH="$HUB/dashboard"
BUILD="$HUB/build"
APP="$BUILD/OpenAlice Hub.app"
rm -rf "$BUILD"; mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp -R "$DASH" "$APP/Contents/Resources/dashboard"

ICONSET="$BUILD/AppIcon.iconset"; mkdir -p "$ICONSET"
for s in 16 32 128 256 512; do
  sips -z $s $s "$DASH/icon-1024.png" --out "$ICONSET/icon_${s}x${s}.png" >/dev/null
  d=$((s*2)); sips -z $d $d "$DASH/icon-1024.png" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/AppIcon.icns"; rm -rf "$ICONSET"

cat > "$APP/Contents/MacOS/launcher" <<'SH'
#!/bin/bash
DIR="$(cd "$(dirname "$0")/../Resources/dashboard" && pwd)"
PORT=7869
URL="http://127.0.0.1:$PORT/"
PY=""; for p in /usr/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3; do [ -x "$p" ] && PY="$p" && break; done
[ -z "$PY" ] && { open "$URL"; exit 0; }
SRV=""
if ! curl -s -o /dev/null "$URL" 2>/dev/null; then
  ( cd "$DIR" && exec "$PY" -m http.server $PORT --bind 127.0.0.1 >/dev/null 2>&1 ) &
  SRV=$!
  for i in $(seq 1 40); do curl -s -o /dev/null "$URL" 2>/dev/null && break; sleep 0.2; done
fi
open "$URL"
[ -n "$SRV" ] && wait $SRV
SH
chmod +x "$APP/Contents/MacOS/launcher"

cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
 <key>CFBundleName</key><string>OpenAlice Hub</string>
 <key>CFBundleDisplayName</key><string>OpenAlice Hub</string>
 <key>CFBundleIdentifier</key><string>com.ericmohlathe.openalice.hub</string>
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
DMG="$HUB/OpenAlice-Hub.dmg"; rm -f "$DMG"
hdiutil create -volname "OpenAlice Hub" -srcfolder "$STAGE" -ov -format UDZO "$DMG" >/dev/null
rm -rf "$STAGE"
echo "DMG: $DMG ($(du -h "$DMG" | cut -f1))"
