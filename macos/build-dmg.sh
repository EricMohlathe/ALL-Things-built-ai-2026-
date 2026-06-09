#!/usr/bin/env bash
# Build the Agent OS Workspace installer .dmg (Apple Silicon target).
#
# On Linux (this container): xorriso emits a hybrid ISO9660+HFS+ image —
# macOS mounts it like any disk image. On macOS you can build a native
# UDZO instead:  hdiutil create -volname "Agent OS Workspace" \
#   -srcfolder <staging> -ov -format UDZO AgentOS-Workspace.dmg
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-/tmp/AgentOS-Workspace-arm64.dmg}"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

git -C "$ROOT" archive --format=tar.gz -o "$STAGE/agent-os-workspace.tar.gz" HEAD
install -m 0755 "$ROOT/macos/Install Agent OS Workspace.command" "$STAGE/"
install -m 0644 "$ROOT/macos/DMG-README.txt" "$STAGE/"

xorriso -as mkisofs \
  -V "Agent OS Workspace" \
  -r -J -joliet-long \
  -hfsplus \
  -o "$OUT" "$STAGE"

ls -lh "$OUT"
