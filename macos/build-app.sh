#!/usr/bin/env bash
# Assemble Agent OS.app (script-based bundle — no compilation, runs on any
# Apple Silicon macOS >= 12). Usage: build-app.sh <output-dir>
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${1:?usage: build-app.sh <output-dir>}/Agent OS.app"

rm -rf "$DEST"
mkdir -p "$DEST/Contents/MacOS" "$DEST/Contents/Resources"
install -m 0644 "$ROOT/macos/app/Info.plist" "$DEST/Contents/"
install -m 0755 "$ROOT/macos/app/AgentOS" "$DEST/Contents/MacOS/"
install -m 0755 "$ROOT/macos/Install Agent OS Workspace.command" \
  "$DEST/Contents/Resources/install.sh"
git -C "$ROOT" archive --format=tar.gz \
  -o "$DEST/Contents/Resources/agent-os-workspace.tar.gz" HEAD
echo "built: $DEST"
