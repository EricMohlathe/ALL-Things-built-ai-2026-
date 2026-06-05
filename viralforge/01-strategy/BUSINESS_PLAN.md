# ViralForge — Business Plan (Lean)

## 1. Problem
Millions of beginners want to make money with faceless AI content. They fail at
**step zero**: they don't know what niche to pick, what to post, or how to turn
attention into money. Existing solutions are *courses and gurus* that explain the
"what" but never hand over a working "how." Result: overwhelm, no posting, no income.

## 2. Solution
A web app that **executes the money system end-to-end**. The user answers a few
prompts; ViralForge returns niches, a 30-day plan, scripts, carousels, and a DM
sales flow — ready to post today. It compresses "watch 40 hours of YouTube" into
"click five buttons."

## 3. Who it's for
See [`NICHE_AND_ICP.md`](NICHE_AND_ICP.md). Primary: the **Overwhelmed Starter** —
18–34, phone-first, wants a side income with AI, will pay ~$29/mo if it removes
the guesswork.

## 4. Product
5 tools + dashboard + Content Vault. Spec in
[`../03-product/PRODUCT_SPEC.md`](../03-product/PRODUCT_SPEC.md). Live build in Base44.

## 5. Business model
| Tier | Price | What they get | Job it does |
|---|---|---|---|
| Free | $0 | 3 generations/day, all 5 tools (limited) | Acquisition + proof |
| **Pro** | **$29/mo** | Unlimited tools, 30-day plans, Content Vault | Core revenue |
| Studio | $79/mo | Multi-niche, brand voice memory, bulk export, priority AI | Power users/agencies |
| Starter Kit | $19 one-time | Templates + 30-day plan PDF (tripwire) | Convert cold traffic |
| Affiliate | rev-share | TTS, stock, schedulers recommended in-app | Margin without churn |

## 6. Unit economics (target, conservative)
- Blended price/paying user ≈ **$34/mo**; gross margin ≈ **80%** (AI + infra the main COGS).
- Target CAC via content-led + tripwire-funded ads: **< $25**.
- Payback **< 1 month**; LTV at ~6-month avg retention ≈ **$200+**.
- **"$500/week" north-star for the *customer*** = our best marketing engine (they post wins).

## 7. Go-to-market
Content-led. We use our own product to run a faceless ViralForge channel across
TikTok/IG/X, prove the method in public, and funnel via DM + email.
Full plan: [`GO_TO_MARKET.md`](GO_TO_MARKET.md).

## 8. Moat (over time)
1. **Outcome data flywheel** — we learn which hooks/niches actually convert and feed
   that back into generations (gets better than a generic chatbot prompt).
2. **Workflow lock-in** — Content Vault + brand-voice memory makes switching costly.
3. **Brand** — owning "faceless content, but it makes money" in the beginner's mind.

## 9. Roadmap
- **0–30 days:** ship MVP (5 tools), landing page, launch content engine, first 100 users.
- **30–90 days:** Stripe billing, Content Vault, brand-voice memory, affiliate links, 1k users.
- **90–180 days:** scheduling integrations, team/agency Studio features, paid ads at scale.

## 10. Key risks & mitigations
| Risk | Mitigation |
|---|---|
| "It's just a ChatGPT wrapper" | Outcome flywheel + opinionated system + vault + UX no chatbot matches |
| Platform/algorithm shifts | Multi-platform; we sell the *system*, not one channel |
| Churn after first wins | Studio features, streaks, new monthly playbooks, community |
| AI cost spikes | Tiered limits, caching, cheaper models for low-stakes steps |
