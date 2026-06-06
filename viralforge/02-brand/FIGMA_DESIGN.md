# ViralForge — Figma Design File

**Live file:** https://www.figma.com/design/1Dxd7McRyAxuDaYiwkoa7q (ViralForge — Brand & Product UI)

Built directly in Figma via the Figma MCP (Plugin API). It's the single source of truth
for the visual system and the screen designs, and it mirrors the brand tokens used in
[`BRAND_GUIDE.md`](BRAND_GUIDE.md) and the live [`landing/`](../landing/index.html) page.

## What's in the file (page "ViralForge")
| Frame | Node | Purpose |
|---|---|---|
| **00 · Brand Cover** | `1:2` | Logo, tagline, signature gradient bar |
| **01 · Colour System** | `1:10` | All 8 brand swatches with hex (Ink → Good) |
| **02 · Typography** | `1:36` | Display + body type scale |
| **03 · App · Dashboard** | `1:42` | The phone product UI: USD banner + the 5-tool money system |
| **04 · Landing · Hero** | `1:73` | Marketing hero: headline, CTAs, 5-tool phone preview |

## Brand tokens (mirrored as Figma fills)
`Ink #0B0B0F · Surface #15151D · Surface-2 #1E1E29 · Forge Orange #FF6A2C ·
Orange-2 #FF9A3D · Ember #FFD166 · Text #F4F4F6 · Good #37D399` — signature gradient
`#FF6A2C → #FF9A3D`. Type: Space Grotesk (display) / Inter (UI).

## Design ↔ code workflow
- **Design → code:** use the Figma MCP `get_design_context` on a frame node to pull
  layout + tokens, then implement against the existing `landing/index.html` system.
- **Code → design:** `use_figma` (Plugin API) writes new screens/components into the
  file; `generate_figma_design` captures a web page pixel-perfect for first import.
- **Code Connect:** map the landing-page components (buttons, plan cards, tool cards)
  to their Figma nodes so design and code stay in sync.

## Next design steps (in Figma)
1. Convert the tool cards + plan cards into **components/variants**.
2. Add **Figma Variables** for the colour + spacing tokens (light/dark ready).
3. Build the remaining product screens (each of the 5 tools' input + result states).
4. Add the **carousel template** as a component (mirrors [`../05-ads/carousel-finance/`](../05-ads/carousel-finance/)).

> Note: Figma's asset CDN sits outside this container's network allowlist, so frame PNGs
> are viewed in-app rather than committed; the file link above is the canonical reference.
