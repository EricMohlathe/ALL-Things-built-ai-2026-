Agent OS Workspace — installer disk image (Apple Silicon)
==========================================================

Contents
  Install Agent OS Workspace.command   one-click installer (double-click)
  agent-os-workspace.tar.gz            the full workspace (offline copy)
  DMG-README.txt                       this file

What the installer does on your M1 MacBook Air
  1. Installs Homebrew if missing (/opt/homebrew)
  2. Installs git, node (>=20), python 3.12, uv, Docker Desktop (cask)
  3. Unpacks the workspace to ~/agent-os-workspace
  4. Runs ./setup.sh  (Hermes agent, Remotion, Vertex AI SDK,
     Agent OS project install, Activepieces .env secrets)
  5. Starts Activepieces via docker compose -> http://localhost:8080

If Gatekeeper blocks the .command: right-click -> Open (first run only).

Manual route (no installer): copy agent-os-workspace.tar.gz somewhere,
  tar -xzf agent-os-workspace.tar.gz && ./setup.sh
