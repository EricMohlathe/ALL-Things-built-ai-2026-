# ViralForge — Product Spec

## The live app
A working web app is being built with **Base44** (AI app builder).

- **App ID:** `6a2243d7d34da1f16e577f02`
- **Editor / preview:** https://app.base44.com/apps/6a2243d7d34da1f16e577f02/editor/preview
- **Status:** built + a South-Africa/global localization pass applied (ZAR default with
  USD toggle, PayFast/Yoco/Ozow mentions, "get paid in USD" banner, POPIA footer).

> The Base44 app is the interactive product. The [`landing/`](../landing/index.html)
> page is the marketing site, and [`06-product-digital/`](../06-product-digital/)
> is the sellable tripwire product. Together they are the full funnel.

## Core concept
An **opinionated, end-to-end money engine** for faceless creators. The user answers a
few questions; the app produces everything they post and everything they say to sell.
It is explicitly *not* a blank chatbot — it decides for the user.

## Information architecture
```
Dashboard (progress through the 5 steps + "get paid in USD" banner)
├─ 1. Niche Finder        interests/skills/platform → 5 niches + best offer each
├─ 2. Content OS          niche → 5 pillars × 3 series + 30-day calendar (topic+hook)
├─ 3. Viral Script Writer topic → 12 hooks → 35–45s script + on-screen text + CTA
├─ 4. Carousel Builder    topic → 7 slides + 120–150w caption + 10 hashtags
├─ 5. DM Money Funnel     offer/keyword → CTA line + 5 DMs + 3 follow-ups
└─ Content Vault          every output saved, searchable, one-click copy
```

## Key screens & UX rules
- **Dashboard:** 5-step progress tracker; "Resume where you left off"; the USD banner.
- **Each tool:** 2–4 inputs max → one big generate button → result with **Copy**,
  **Save to Vault**, and **Regenerate** actions. Never a wall of options.
- **Speed-to-win:** a first usable output must be reachable in < 10 minutes / 3 clicks.
- **Mobile-first:** the audience is phone-first; everything works one-handed.

## Design system
🎨 Designed in **Figma**: https://www.figma.com/design/1Dxd7McRyAxuDaYiwkoa7q (frame
"03 · App · Dashboard" is the product UI; "04 · Landing · Hero" the marketing screen).
See [`../02-brand/FIGMA_DESIGN.md`](../02-brand/FIGMA_DESIGN.md).

Dark, premium, high-contrast. Background `#0B0B0F`, surfaces `#15151D/#1E1E29`,
accent **Forge Orange `#FF6A2C`** with a `#FF9A3D` gradient. Display font Space
Grotesk, UI font Inter. Rounded corners, soft glow on primary CTAs, orange used
sparingly as energy. Full tokens in [`../02-brand/BRAND_GUIDE.md`](../02-brand/BRAND_GUIDE.md).

## Monetization in-product
- Free tier gates generations/day + watermark; Pro unlocks unlimited + Vault.
- In-tool upsell at limits ("Out of free generations — go Pro").
- Affiliate "Tools I use" module in the Vault.
- Multi-currency billing (USD/ZAR/GBP/INR/NGN + PPP) — see
  [`../01-strategy/OFFER_AND_PRICING.md`](../01-strategy/OFFER_AND_PRICING.md).

## Build roadmap (post-MVP)
1. Stripe + PayFast/Paystack billing & metering.
2. Content Vault persistence + brand-voice memory.
3. Outcome feedback ("did this post do well?") → generation flywheel.
4. Scheduling/integration exports; Studio multi-workspace + seats.

## How to iterate the app
Use the Base44 editor (link above) or the `edit_base44_app` tool with a plain-English
change request. All app changes happen in Base44, not in this repo.
