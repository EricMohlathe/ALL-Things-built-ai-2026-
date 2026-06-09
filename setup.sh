#!/usr/bin/env bash
# Rebuild all live installs in a fresh checkout (deps are git-ignored).
# Requires: node>=20, python>=3.11, uv, git.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> [1/6] Hermes agent (uv sync)"
( cd "$ROOT/agents/hermes-agent" && uv sync )

echo "==> [2/6] Remotion project (npm install)"
( cd "$ROOT/software/remotion-project" && npm install --no-audit --no-fund )

echo "==> [3/6] Vertex AI SDK (google-cloud-aiplatform)"
python3 -m venv "$ROOT/software/python-aiplatform/.venv"
"$ROOT/software/python-aiplatform/.venv/bin/pip" install -q --upgrade pip
"$ROOT/software/python-aiplatform/.venv/bin/pip" install -r "$ROOT/software/python-aiplatform/requirements.txt"

echo "==> [4/6] Seedance2 ComfyUI node deps (torch comes from host ComfyUI)"
python3 -m venv "$ROOT/software/seedance2-comfyui/.venv"
"$ROOT/software/seedance2-comfyui/.venv/bin/pip" install -q --upgrade pip
"$ROOT/software/seedance2-comfyui/.venv/bin/pip" install \
  "requests>=2.28.0" "Pillow>=9.0.0" "numpy>=1.23.0" "opencv-python>=4.7.0"

echo "==> [5/6] Agent OS (project install: agent-os/ + .claude/commands/agent-os/)"
( cd "$ROOT" && bash software/agent-os/scripts/project-install.sh )

echo "==> [6/6] Activepieces (generate .env; run with: cd software/activepieces && docker compose up -d)"
AP_DIR="$ROOT/software/activepieces"
if [ ! -f "$AP_DIR/.env" ]; then
  sed -e "s/^AP_ENCRYPTION_KEY=.*/AP_ENCRYPTION_KEY=$(openssl rand -hex 16)/" \
      -e "s/^AP_JWT_SECRET=.*/AP_JWT_SECRET=$(openssl rand -hex 32)/" \
      -e "s/^AP_POSTGRES_PASSWORD=.*/AP_POSTGRES_PASSWORD=$(openssl rand -hex 16)/" \
      "$AP_DIR/.env.example" > "$AP_DIR/.env"
  echo "    wrote $AP_DIR/.env with generated secrets"
fi
if [ "${1:-}" = "--with-activepieces-src" ] && [ ! -d "$AP_DIR/src" ]; then
  git clone --depth 1 https://github.com/activepieces/activepieces.git "$AP_DIR/src"
fi

echo "==> Done. Skills live in .claude/skills/ (loaded automatically by Claude Code)."
