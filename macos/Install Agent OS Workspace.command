#!/bin/bash
# Agent OS Workspace installer — Apple Silicon (M1/M2/M3) macOS.
# Double-click from the mounted disk image. Installs to ~/agent-os-workspace.
set -euo pipefail

DEST="$HOME/agent-os-workspace"
VOL="$(cd "$(dirname "$0")" && pwd)"
BREW=/opt/homebrew/bin/brew

say() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }

[ "$(uname -sm)" = "Darwin arm64" ] || {
  echo "This installer targets Apple Silicon Macs (arm64). Detected: $(uname -sm)"; exit 1; }

say "Homebrew"
if [ ! -x "$BREW" ]; then
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
eval "$("$BREW" shellenv)"

say "Prerequisites: git, node>=20, python, uv"
brew list --formula git  >/dev/null 2>&1 || brew install git
brew list --formula node >/dev/null 2>&1 || brew install node
brew list --formula uv   >/dev/null 2>&1 || brew install uv
brew list --formula python@3.12 >/dev/null 2>&1 || brew install python@3.12

say "Docker (needed for Activepieces)"
if ! command -v docker >/dev/null 2>&1; then
  brew install --cask docker
  echo "Docker Desktop installed — launching it once so the daemon initialises…"
  open -a Docker || true
fi

say "Workspace -> $DEST"
mkdir -p "$DEST"
tar -xzf "$VOL/agent-os-workspace.tar.gz" -C "$DEST"

say "setup.sh (Hermes agent, Remotion, Vertex SDK, Agent OS install, Activepieces .env)"
( cd "$DEST" && ./setup.sh )

say "Starting Activepieces (docker compose)"
if docker info >/dev/null 2>&1; then
  ( cd "$DEST/software/activepieces" && docker compose up -d )
  echo "Waiting for http://localhost:8080 …"
  for _ in $(seq 1 60); do
    curl -fsS http://localhost:8080/api/v1/flags >/dev/null 2>&1 && break; sleep 5
  done
  node "$DEST/software/activepieces/ap-bridge.mjs" health || true
  open http://localhost:8080 || true
else
  echo "Docker daemon not running yet. Once Docker Desktop is up, run:"
  echo "  cd $DEST/software/activepieces && docker compose up -d"
fi

say "Done"
echo "Workspace: $DEST  (open it in Claude Code — /agent-os commands + 24 skills auto-load)"
echo "Activepieces: http://localhost:8080   bridge: node software/activepieces/ap-bridge.mjs"
