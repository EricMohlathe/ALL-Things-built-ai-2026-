# OfferPilot — Product Spec

## The live app
Built with **Base44**.
- **App ID:** `6a22530928ccea0d20780c9e`
- **Editor / preview:** https://app.base44.com/apps/6a22530928ccea0d20780c9e/editor/preview
- Localized: ZAR default + USD toggle, PayFast/Yoco/Ozow, "land remote jobs paid in USD" banner.

> The Base44 app is the interactive product. [`../landing/`](../landing/index.html) is the
> marketing site, [`../06-product-digital/`](../06-product-digital/) is the sellable kit,
> and [`../07-service/`](../07-service/) is the done-for-you service.

## Core concept
An **AI career co-pilot** that diagnoses why a CV is invisible to the ATS and fixes it,
then carries the user to interview-ready. The free ATS score is the wedge.

## Information architecture
```
Dashboard (current ATS score ring + progress + "paid in USD" banner)
├─ 1. ATS Résumé Scanner   paste/upload CV → score/100 + prioritised fixes
├─ 2. AI Bullet Rewriter   weak duty → strong, metric-driven achievement bullet
├─ 3. Job Match & Tailor   paste JD → tailored CV + match score + missing keywords
├─ 4. Cover Letter Gen     role + CV → tailored cover letter
├─ 5. Interview Prep       role → likely questions + strong sample answers
└─ Application Tracker     company · role · status · next step
```

## Key UX rules
- **Free scan in < 30 seconds**, no signup, instant emotional payoff (the score ring).
- Each tool: minimal input → one primary action → result with **Copy / Save / Improve**.
- Mobile-first; reassuring tone; green when something improves.
- Privacy-forward (CVs are sensitive): clear consent, easy delete (POPIA/GDPR).

## Design system
🎨 Brand tokens in [`../02-brand/BRAND_GUIDE.md`](../02-brand/BRAND_GUIDE.md): deep navy
`#0A0E18`, blue→cyan accent `#3B82F6→#22D3EE`, success green `#22C55E`. Space Grotesk /
Inter. (See [`../02-brand/FIGMA_DESIGN.md`](../02-brand/FIGMA_DESIGN.md) if a Figma file is attached.)

## Monetization in-product
- Free scan gated to 1/day; Pro unlocks unlimited + rewriter + tailor + tracker.
- Upsell to the **service** from the scan result ("Want us to do it for you? →").
- Multi-currency billing — see [`../01-strategy/OFFER_AND_PRICING.md`](../01-strategy/OFFER_AND_PRICING.md).

## Roadmap
1. Billing + metering (Stripe/PayFast).
2. Real ATS parser (keyword/format/section scoring) + JD keyword diffing.
3. LinkedIn import; PDF/DOCX export of the optimised CV.
4. B2B dashboard (universities/bootcamps) with cohort analytics.
