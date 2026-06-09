# Provenance

Every component in this workspace was cloned/installed from upstream on
**2026-06-05**. Source commit SHAs (default-branch HEAD at clone time):

| Component | Upstream | Commit | Vendored as |
|-----------|----------|--------|-------------|
| Hermes agent (the "executive") | `NousResearch/hermes-agent` | `96cd37e2` | `agents/hermes-agent/` (full source, `.git` stripped) |
| Higgsfield skills (official) | `higgsfield-ai/skills` | `5af02582` | `.claude/skills/higgsfield-*` (4 skills) |
| Higgsfield/Seedance skills | `AKCodez/higgsfield-claude-skills` | `f6698ab7` | `.claude/skills/seedance-*`, `ugc-*`, `higgsfield-image-auto` (19 skills) |
| Awesome Seedance (reference) | `ZeroLu/awesome-seedance` | `540d43d7` | `references/awesome-seedance/` (demo `videos/` removed) |
| GPT-Image-2 → Seedance2 workflow | `EvoLinkAI/GPT-Image-2-Seedance2-Workflow` | `8d934f4c` | `software/gpt-image2-seedance2-workflow/` (demo `images/` removed) |
| Seedance2 ComfyUI node | `Anil-matcha/seedance2-comfyui` | `fd8c17db` | `software/seedance2-comfyui/` (full source) |
| Vertex AI SDK | `googleapis/python-aiplatform` | `0c72b97b` | pip pkg `google-cloud-aiplatform` (not vendored — installed) |
| Remotion | `remotion-dev/remotion` | `46361235` | `software/remotion-project/` (fresh project using `remotion` npm pkg) |
| Agent OS | `buildermethods/agent-os` | `cae8e66` | `software/agent-os/` (full source) + project install: `agent-os/`, `.claude/commands/agent-os/` |
| Activepieces | `activepieces/activepieces` | `4991f3be` | `software/activepieces/` (upstream `docker-compose.yml` + `.env.example`, image `0.83.0`; source not vendored) |

## Decisions / deviations

- **Remotion** is a large monorepo designed to be consumed as an npm dependency,
  not vendored whole. A fresh, runnable Remotion project was created and the
  `remotion` package (v4.0.472) installed into it.
- **python-aiplatform** is a 161 MB SDK with no Claude skills. Rather than vendor
  the source, the package was installed via pip and a `vertex-ai-sdk` skill was
  authored (`.claude/skills/vertex-ai-sdk/`) so it is usable as a skill.
- **seedance2-comfyui** is a ComfyUI custom node. Its `torch` dependency is
  provided by the host ComfyUI install, so only the lightweight deps
  (requests/Pillow/numpy/opencv) were installed here. Drop the folder into
  `ComfyUI/custom_nodes/` to use it.
- **Demo media** (~216 MB of sample `.mp4`/`.png` in the workflow and awesome
  repos) was removed to keep the repo lean; `*_REMOVED.md` notes point to the
  originals.
- All `node_modules/` and `.venv/` are git-ignored and rebuilt by `setup.sh`.
- **Agent OS** (436 K) is vendored whole at `software/agent-os/` and installed
  into the project with its own `scripts/project-install.sh` (run by `setup.sh`),
  yielding `agent-os/standards/` and five `/agent-os` Claude Code commands.
- **Activepieces** is a ~300 MB / 23k-file monorepo — like Remotion, not vendored
  whole. It is deployed from the official Docker image via the upstream compose
  file; `setup.sh` generates `.env` secrets, and `--with-activepieces-src`
  shallow-clones full source to the git-ignored `software/activepieces/src/`.
  Integration with Agent OS: `software/activepieces/ap-bridge.mjs` (zero-dep CLI)
  + the indexed standard `agent-os/standards/activepieces-automation.md`.
