# OfferPilot — Figma Design File

**Live file:** https://www.figma.com/design/K7QPDGTizYX1n3f5k4ODKf (OfferPilot — Brand & Product UI)

Created via the Figma MCP. It's the source of truth for the visual system and screens,
mirroring [`BRAND_GUIDE.md`](BRAND_GUIDE.md) and the live [`../landing/`](../landing/index.html) page.

> ⚠️ **Status:** the file is created, but the **Figma Starter-plan MCP tool-call limit was
> reached** before the frames could be written in (the sibling ViralForge file used the
> allotment). The frame spec below is ready to build on a plan with more MCP calls — the
> exact code that builds it is the same `use_figma` Plugin-API approach used for
> [`../../README.md`](../../README.md)'s ViralForge file.

## Planned frames (page "OfferPilot")
| Frame | Purpose |
|---|---|
| 00 · Brand Cover | Logo (✈ OfferPilot), tagline "Beat the bots. Land the interview." |
| 01 · Colour System | 8 swatches (Ink → Text) with hex |
| 02 · Typography | Display + body scale |
| 03 · App · Dashboard | ATS score ring (92/100, green) + the 6-tool layout + USD banner |
| 04 · Landing · Hero | "Your CV is rejected by a robot." + before/after ATS score card |

## Brand tokens (mirror as Figma fills/variables)
`Ink #0A0E18 · Surface #131A2A · Surface-2 #1B2436 · Blue #3B82F6 · Cyan #22D3EE ·
Success #22C55E · Danger #EF4444 · Text #EAF0FB · Muted #93A1B8` — gradient
`#3B82F6 → #22D3EE`. Type: Space Grotesk (display) / Inter (UI).

## Design ↔ code workflow
- **Design → code:** `get_design_context` on a frame → implement against `landing/index.html`.
- **Code → design:** `use_figma` (Plugin API) writes screens; `generate_figma_design` for first web import.
- **Code Connect:** map the landing-page components (score card, tool cards, plan cards) to Figma nodes.

> Figma's asset CDN is outside this container's network allowlist, so frame PNGs are
> viewed in-app; this file link is the canonical reference.
