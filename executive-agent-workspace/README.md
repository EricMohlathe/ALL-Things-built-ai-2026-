# Executive Agent Workspace

A self-contained workspace bundling the **Hermes agent** ("the executive") with a
set of **video / image generation Claude skills** and supporting **software**.
Built with Claude Code on 2026-06-05. See [`PROVENANCE.md`](./PROVENANCE.md) for
exact upstream sources and commit SHAs.

> This lives on the orphan branch `executive-agent-workspace` (independent
> history, not mixed into the trading project). To promote it to its own GitHub
> repo: create an empty repo and
> `git push <new-remote> executive-agent-workspace:main`.

## Layout

```
.
├── .claude/skills/                 # 24 Claude skills (auto-discovered by Claude Code)
│   ├── higgsfield-generate/        #   official Higgsfield skills (higgsfield-ai/skills)
│   ├── higgsfield-soul-id/
│   ├── higgsfield-product-photoshoot/
│   ├── higgsfield-marketplace-cards/
│   ├── seedance-cinematic/ … seedance-real-estate/   # AKCodez skill set
│   ├── seedance-auto-generate/  higgsfield-image-auto/
│   ├── ugc-video-auto/  ugc-hot-girl/
│   └── vertex-ai-sdk/              #   authored here for the Vertex AI SDK
├── agents/
│   └── hermes-agent/               # NousResearch/hermes-agent (the "executive")
├── software/
│   ├── remotion-project/           # runnable Remotion 4.x video project
│   ├── seedance2-comfyui/          # ComfyUI custom node (drop into ComfyUI/custom_nodes)
│   ├── gpt-image2-seedance2-workflow/   # GPT-Image-2 → Seedance2 workflow + docs
│   └── python-aiplatform/          # Vertex AI SDK install + quickstart
├── references/
│   └── awesome-seedance/           # curated Seedance link list
├── setup.sh                        # rebuild all live installs in a fresh checkout
└── PROVENANCE.md
```

## Skills (24)

Claude Code auto-discovers every `.claude/skills/*/SKILL.md`. Highlights:

- **Higgsfield (official):** `higgsfield-generate`, `higgsfield-soul-id`,
  `higgsfield-product-photoshoot`, `higgsfield-marketplace-cards`
- **Seedance video styles:** `seedance-cinematic`, `seedance-3d-cgi`,
  `seedance-cartoon`, `seedance-anime-action`, `seedance-fight-scenes`,
  `seedance-music-video`, `seedance-product-360`, … (15 styles)
- **Automation / commerce:** `seedance-auto-generate`, `higgsfield-image-auto`,
  `seedance-ecommerce-ad`, `seedance-real-estate`, `ugc-video-auto`, `ugc-hot-girl`
- **Cloud:** `vertex-ai-sdk` (Google Vertex AI / Gemini)

## Software — what's installed live

| Software | Where | How to run |
|----------|-------|-----------|
| **Hermes agent** | `agents/hermes-agent` | `cd agents/hermes-agent && uv run hermes` (see its README) |
| **Remotion** (4.0.472) | `software/remotion-project` | `cd software/remotion-project && npm run dev` (studio) / `npm run render`† |
| **Vertex AI SDK** (1.156.0) | `software/python-aiplatform` | `source software/python-aiplatform/.venv/bin/activate` then run `examples/quickstart.py` |
| **Seedance2 ComfyUI node** | `software/seedance2-comfyui` | copy into `ComfyUI/custom_nodes/` (host provides torch) |
| **GPT-Image-2 → Seedance2 workflow** | `software/gpt-image2-seedance2-workflow` | follow that folder's README |

† Remotion video **rendering** needs `ffmpeg` on the host (not preinstalled in
this container). The Studio dev server and project build do not.

## Rebuilding from a clean checkout

Dependency trees (`node_modules/`, `.venv/`) are git-ignored. After cloning:

```bash
./setup.sh
```

## Auth / API keys

Several components call paid external APIs and need credentials you supply:
- **Higgsfield / Seedance skills** → Higgsfield API key (see each skill's `SKILL.md`)
- **Hermes agent** → see `agents/hermes-agent/.env.example`
- **Vertex AI** → `GOOGLE_CLOUD_PROJECT` + `gcloud auth application-default login`

No secrets are committed; `.env` files are git-ignored.
