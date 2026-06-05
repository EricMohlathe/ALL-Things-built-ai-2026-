#!/usr/bin/env bash
# Rebuild all live installs in a fresh checkout (deps are git-ignored).
# Requires: node>=20, python>=3.11, uv, git.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> [1/4] Hermes agent (uv sync)"
( cd "$ROOT/agents/hermes-agent" && uv sync )

echo "==> [2/4] Remotion project (npm install)"
( cd "$ROOT/software/remotion-project" && npm install --no-audit --no-fund )

echo "==> [3/4] Vertex AI SDK (google-cloud-aiplatform)"
python3 -m venv "$ROOT/software/python-aiplatform/.venv"
"$ROOT/software/python-aiplatform/.venv/bin/pip" install -q --upgrade pip
"$ROOT/software/python-aiplatform/.venv/bin/pip" install -r "$ROOT/software/python-aiplatform/requirements.txt"

echo "==> [4/4] Seedance2 ComfyUI node deps (torch comes from host ComfyUI)"
python3 -m venv "$ROOT/software/seedance2-comfyui/.venv"
"$ROOT/software/seedance2-comfyui/.venv/bin/pip" install -q --upgrade pip
"$ROOT/software/seedance2-comfyui/.venv/bin/pip" install \
  "requests>=2.28.0" "Pillow>=9.0.0" "numpy>=1.23.0" "opencv-python>=4.7.0"

echo "==> Done. Skills live in .claude/skills/ (loaded automatically by Claude Code)."
