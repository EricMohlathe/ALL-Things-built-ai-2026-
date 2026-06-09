#!/usr/bin/env bash
# Build the Agent OS Workspace installer .dmg (Apple Silicon target).
#   macOS: native hdiutil -> compressed UDZO dmg
#   Linux: xorriso -> hybrid ISO9660+HFS+ image (macOS mounts it fine)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-$HOME/Desktop/AgentOS-Workspace-arm64.dmg}"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

bash "$ROOT/macos/build-app.sh" "$STAGE"
ln -s /Applications "$STAGE/Applications"
install -m 0644 "$ROOT/macos/DMG-README.txt" "$STAGE/"

if [ "$(uname -s)" = "Darwin" ]; then
  hdiutil create -volname "Agent OS Workspace" -srcfolder "$STAGE" \
    -ov -format UDZO "$OUT"
else
  xorriso -as mkisofs \
    -V "Agent OS Workspace" \
    -r -J -joliet-long \
    -hfsplus \
    -o "$OUT" "$STAGE"
fi

ls -lh "$OUT"
