# COACHMILLAWELLNESS — GODMODE MASTER BUILD COMPENDIUM

**Version 1.1 · July 2026 · Doctoral-grade build brief for Claude Code · ENGAGEMENT-FIRST REVISION**
**Brand:** CoachMillaWellness — official name, final. App display name: **Coach Milla Wellness** · store bundle ids: `com.coachmillawellness.app` · internal shorthand: **CMW**. Wordmark: "Coach Milla" in Gambetta display + "WELLNESS" in General Sans caps, dawn-gradient accent on the M.
**Client:** A stellar health & life coach (solo practice, GROW/GREAT methodology, Wheel of Life practitioner, active short-form content creator).
**Builder:** You + Claude Code. This document is the single source of truth. Feed it section-by-section using the Prompt Pack in §11.
**PRIMARY SURFACES:** the **Mobile app** and the **Website** are co-primary — every client-facing capability ships on both first. Desktop (.exe/.dmg) is the coach's deep-work cockpit; the single HTML is the private offline vault. Operating rhythm: **prepare on desktop → engage from the phone → client receives via web links + WhatsApp.**

---

## §0 — HOW TO USE THIS DOCUMENT

| Rule | Detail |
|---|---|
| One source of truth | Every build (HTML, web, desktop, mobile) derives from §2 features, §3 data model, §4 design tokens. No target invents its own scheme. |
| Feed order | Paste §1–§5 as Claude Code's standing context (CLAUDE.md), then run prompts P1→P9 from §11 in sequence. |
| Phase freeze | A module's scope locks when its phase starts. New ideas go to the ICEBOX list at the bottom, never mid-phase. |
| Definition of done | A phase ships only when its Validation Gate (§12) passes. No exceptions — that's what GODMODE means. |
| Surface primacy | Mobile + Web lead every design and sequencing decision. A client-facing feature counts as done only when it works on BOTH primaries (Gate G10). Desktop inherits; the HTML mirrors what fits offline. |
| Placeholder data | Seed with fictional coachees ("Client A – Naledi M.", "Client B – Thabo K."). Never hard-code real client names into code or repos. |

---

## §1 — MISSION & PRODUCT THESIS

### 1.1 The operator

A professional health/life coach who: runs 60-minute GROW & GREAT framework sessions (solo and joint); uses the Wheel of Life (10 domains, 0–10 scores, targets) as her core diagnostic; already runs post-session analysis through Claude (element-by-element adherence grading — Strong / Adequate / Weak / Met — plus a SMARTER-goals reminders checklist and review-date discipline); and posts videos and stories that must stay coherent with her core coaching messages.

### 1.2 Jobs to be done — in her own words

| # | Her requirement | Translated product job |
|---|---|---|
| J1 | "Track my coaches" (her coachees/clients) | A client constellation: every coachee, their goals, Wheel history, sessions, action items, review dates — one screen per human. |
| J2 | "My videos and stories I post so I start being coherent in messages" | A content studio: calendar + pipeline + message pillars + a coherence map showing whether published content matches her core messages. |
| J3 | (Implied by her current workflow) Session intelligence | Absorb the Claude analysis loop she already does manually: log a session → auto-generate GROW/GREAT adherence scorecard → reminders checklist → next review date. |
| J4 | "There must be delivery timelines" | §10 is a literal quote sheet with weekly deliverables she can hold you to. |
| J5 | Engage clients **between** sessions — where retention is actually won | Mobile + Web co-primary: Share Kit, tokenized Progress Links, Client Pulse check-ins, push nudges → module M8. |

### 1.3 Competitive gap (why build, not buy)

| Platform | Strong at | Missing (CMW's opening) |
|---|---|---|
| Practice Better | Wellness charting, HIPAA telehealth, billing, intake forms | No framework-adherence scoring, no content tracking, subscription forever |
| CoachAccountable | Action plans, habit tracking, metrics dashboards, worksheets | No GROW/GREAT session grading, no Wheel-of-Life-over-time visual, no content coherence |
| Paperbell | Packages, scheduling, payments, contracts | Thin on progress depth; zero content tools |
| Quenza / Simply.Coach | Therapeutic activities / lightweight session mgmt | Same gaps; none integrate an AI session analyst |

Market note: several venture-backed coaching platforms (Practice.do, Profi) have shut down — owning her own tool removes platform risk and monthly fees. **No mainstream platform combines (a) framework-adherence session grading, (b) a living Wheel of Life visual, and (c) a content-coherence engine. That triad is the product.**

### 1.4 North-star differentiators

1. **The Living Wheel** — a Wheel of Life that breathes, morphs across time, and is beautiful enough to screenshot into client reports. The signature element (§4.3).
2. **Coach Growth Curve** — she gets graded too: her own GROW/GREAT adherence scores charted over months. The app coaches the coach.
3. **Coherence Map** — pillars × published-content matrix that exposes message drift at a glance.
4. **AI Copilot native** — the Claude analysis she does manually today becomes one button (§9).
5. **Local-first, hers forever** — works offline, exports everything, no subscription hostage-taking.
6. **An engagement loop that lives where her clients live** — WhatsApp-perfect shares from the phone; zero-login web links for clients (M8).

### 1.5 Engagement doctrine — surface roles (LAW)

| Surface | Role | Client ever touches it? |
|---|---|---|
| **Mobile app** | **PRIMARY №1** — front line: in-session capture, push nudges, one-tap WhatsApp shares | Indirectly (receives every share + nudged outcome) |
| **Website** | **PRIMARY №2** — the only surface clients open directly: tokenized progress pages, Pulse check-ins, booking/credibility | **Yes — zero login, one tap from WhatsApp** |
| Desktop .exe/.dmg | Coach cockpit: deep session analysis, content planning, long-form notes | Never |
| Single HTML | Private offline vault + Week-1 deliverable | Never |

The loop: **coach prepares (desktop) → engages (phone) → client receives (WhatsApp/web link) → client responds (Pulse) → Deck surfaces it → next nudge.** Every roadmap, design and scope decision defers to this loop.

---

## §2 — FEATURE ARCHITECTURE · 9 MODULES

> Navigation shell: left rail (desktop/web) / bottom tab bar ≤5 items (mobile): **Deck · Clients · Sessions · Content · More** (More → Wheel Lab, Insights, Copilot, Engage inbox, Vault). M8 Engage is cross-cutting: share actions live on every client, wheel, session and content card.

### M0 — COMMAND DECK (home)
| Aspect | Spec |
|---|---|
| Purpose | 8-second answer to "what does today need from me?" |
| Widgets | Today's sessions (cards w/ prep links) · Overdue action-item reviews (the Wed/Sat review-date pattern) · Content due today (from calendar) · Streaks (sessions logged, posts published) · "Focus for today" — one AI-generated sentence |
| Hero moment | Greeting keyed to time of day + a slow ambient dawn-gradient sweep behind the header (subtle, 20s loop, pauses on reduced-motion) |
| Empty state | First-run: guided 3-step setup (add a coachee → set pillars → log first session), illustrated, playful |

### M1 — COACHEE CONSTELLATION (client CRM)
| Aspect | Spec |
|---|---|
| Index | Card grid; each card = avatar, name, package, next session, mini-wheel sparkline, status chip (Active/Paused/Alumni), risk flag if a review date slipped |
| Client detail | Tabs: **Overview** (goals + latest Wheel + open actions) · **Wheel** (full Living Wheel + timeline scrub) · **Sessions** (chronological log w/ adherence badges) · **Actions** (kanban: Open → In review → Done, each with due + review date) · **Notes** |
| Goals | SMARTER-flag chips per goal (Specific, Measurable, Achievable, Relevant, Time-bound, Exciting, Rewarded) — the "Exciting/Rewarded weren't explicitly named" gap from her checklist becomes a visible toggle |
| Joint sessions | A session can link 2+ coachees (her real pattern); each participant still gets their own Wheel + actions |

### M2 — SESSION ENGINE
| Aspect | Spec |
|---|---|
| Pre-session | Prep card: last session summary, open actions, last Wheel, suggested opening question |
| Live mode | Full-screen focus: 60-min timer ring · framework stepper **G→R→O→W** or **G→R→E→A→T** · each step surfaces its question bank (Appendix A) · quick-capture notes per step · confidence & commitment sliders (1–10) at close — ≥8/10 triggers the "cement the agreement" closing script |
| Post-session | Paste notes/transcript → AI adherence scorecard: per-element rating (Strong / Adequate / Weak / Met / N/A) + notes — the exact table format she already produces in Claude · Reminders checklist auto-filled (SMARTER met? · low scores flagged? · Will/Take-action step? · review date set?) · one-tap create action items with review dates |
| Manual override | Every AI rating is editable; AI proposes, coach disposes |

### M3 — WHEEL OF LIFE LAB (signature)
| Aspect | Spec |
|---|---|
| Core viz | 10-domain radial (Career, Finances, Health, Family, Romance, Personal Growth, Fun, Environment, Friends, Spirituality — editable list, stored per coachee) |
| Interactions | Drag spokes to score during a session · target overlay (ghost ring) · timeline scrubber morphs the wheel between snapshot dates (animated tween, 600ms, ease-out-expo) · before/after split view for client reports |
| 3D tier | Web + desktop + mobile builds: React Three Fiber "bloom" — petals extrude by score, idle breathing (±2% scale, 4s), particles drift outward on improved domains. HTML Build 1: 2D SVG/canvas version (identical data + interactions, no Three.js — keeps the single file lean). |
| Export | PNG snapshot + animated WebM of a morph — shareable to the client or her stories (content flywheel!) |

### M4 — CONTENT STUDIO
| Aspect | Spec |
|---|---|
| Pillars | 3–6 message pillars (name, color, core message, keywords). These are the coherence backbone. |
| Pipeline | Kanban: **Idea → Script → Filmed → Posted → Analyzed**. Card = title, type (Reel/Story/Video/Post/Short), platform (IG/TikTok/YouTube/WhatsApp Status/LinkedIn), pillar chip, hook, CTA |
| Calendar | Month + week views; drag to schedule; consistency heatmap (GitHub-style) of publish days |
| Coherence Map | Matrix: pillars (rows) × last 30/60/90 days (columns) → cell intensity = posts serving that pillar. Instantly shows a starved pillar or off-message drift. AI check (§9) grades any script against its pillar's core message: **On-message / Drifting / Off-message** + one-line fix. |
| Library | Hooks bank, CTA bank, reusable script templates |

### M5 — INSIGHTS OBSERVATORY
| Aspect | Spec |
|---|---|
| Coach Growth Curve | Her average adherence per element (G/R/O/W, G/R/E/A/T) charted monthly — e.g., "Options was your weak element in June; Strong in 3 of 4 July sessions" |
| Client outcomes | Wheel-score deltas across the book of clients; domains most improved; action-item completion rate |
| Content ↔ Coaching synergy | Posts per pillar vs. new-client inquiries (manual inquiry log v1) |
| Charts | Line (trends) · bar (element adherence) · radar (wheel) · heatmap (calendar consistency) · funnel (content pipeline) · gauge (avg commitment score). Every chart: legend, tooltip, colorblind-safe, never color-only meaning. |

### M6 — AI COPILOT (Claude API — full spec §9)
Session Analyzer · Coherence Checker · Weekly Digest (Monday brief: clients needing attention, content gaps, one coaching-skill tip drawn from her own adherence data) · Prep Whisperer (pre-session brief).

### M7 — VAULT & SETTINGS
JSON + CSV export/import (full round-trip) · encrypted backup file · theme (Dawn dark / Morning light) · framework editor (edit question banks) · Wheel domain editor · API key management (local, never committed) · POPIA data notes (§13).

### M8 — ENGAGE (Share Kit · Progress Links · Client Pulse · Nudges) — CO-PRIMARY FLAGSHIP
| Aspect | Spec |
|---|---|
| Share Kit (mobile-first) | One-tap exports to the native share sheet: Wheel PNG · animated morph WebM · session recap card · action-checklist card. Auto-rendered in WhatsApp-perfect sizes (1080×1920 story + 1080×1080 square), First Light styled, subtle CMW wordmark. |
| Progress Links (web-first) | Tokenized read-only page `/p/<token>` per coachee: Living Wheel + timeline scrub + wins + next review date. 128-bit unguessable token · per-client consent gate before the first link · one-tap revoke · optional expiry · first-name-only default. Dynamic OG image = that client's wheel, so the WhatsApp link preview alone already delights. |
| Client Pulse (web-first) | `/pulse/<token>` — no login: client ticks action items done, optional 60-second mini-wheel self-score, one-line reflection. Lands in her Engage inbox + a Deck widget + an optional push. The between-session heartbeat. |
| Nudge Engine (mobile-first) | Push categories: review-date (the Wed/Sat pattern) · pre-session prep (T-2h) · streak milestones · Pulse received. Per-category toggles; quiet hours default 20:00–07:00. |
| Deep links | Any `coachmillawellness.com` link opens the app when installed (iOS Universal Links + Android App Links), web fallback otherwise — one URL works in every context. |

---

## §3 — DATA MODEL (one schema, four targets)

### 3.1 Entities

| Entity | Key fields | Notes |
|---|---|---|
| `coachee` | id, name, avatar, status(active/paused/alumni), package, start_date, tags[], contact, notes | Soft-delete only |
| `goal` | id, coachee_id, statement, smarter jsonb {S,M,A,R,T,E,Rw: bool}, target_date, status | SMARTER chips render from jsonb |
| `session` | id, date, duration_min, framework('GROW'/'GREAT'), participants[] (coachee_ids), summary, confidence(1–10), commitment(1–10), review_dates[], transcript_ref | Joint sessions via participants[] |
| `session_element_score` | id, session_id, coachee_id, element, rating('Strong'/'Adequate'/'Weak'/'Met'/'N/A'), notes | Mirrors her existing scorecards exactly |
| `session_checklist` | id, session_id, item(smarter_met/low_scores_flagged/will_step/review_date_set), state(pass/fail/na), notes | The ✅ reminders checklist |
| `wheel_snapshot` | id, coachee_id, date, domain, score(0–10), target(0–10) | 10 rows per snapshot |
| `action_item` | id, coachee_id, session_id, title, due_date, review_date, status(open/in_review/done), completed_at | Review-date is first-class, not a tag |
| `pillar` | id, name, color, core_message, keywords[] | Max ~6 |
| `content_item` | id, title, type, platform, pillar_id, status(idea/script/filmed/posted/analyzed), hook, cta, script, publish_date, link, metrics jsonb | metrics = views/likes/saves, manual v1 |
| `inquiry` | id, date, source, pillar_guess, converted(bool) | Feeds synergy chart |
| `ai_run` | id, kind, input_ref, output, model, tokens_in/out, cost_usd, created_at | Cost transparency |
| `share_link` | id, coachee_id, kind('progress'/'pulse'), token(128-bit), consent_at, revoked_at, expires_at, view_count | M8; token never derivable from ids |
| `pulse_response` | id, share_link_id, coachee_id, date, actions_done[], mini_wheel jsonb, reflection | Feeds Engage inbox + Deck widget |
| `nudge` | id, kind, entity_ref, scheduled_at, sent_at, opened_at | Mobile push ledger |
| `settings` | key, value jsonb | Themes, domains, question banks |

Conventions: UUIDv7 ids · ISO-8601 UTC timestamps · `updated_at` on every row (drives sync) · all enums as text with CHECK constraints.

### 3.2 Storage mapping

| Build | Store | Sync |
|---|---|---|
| 1 · Single HTML | IndexedDB via Dexie.js + full JSON export/import | None (manual export = backup) |
| 2 · Website | Supabase Postgres + Row Level Security (auth.uid() = owner) | Realtime channel optional |
| 3 · Desktop | SQLite via tauri-plugin-sql | Pull/push to Supabase, last-write-wins on `updated_at` |
| 3 · Mobile | expo-sqlite (or Tauri SQLite if path B) | Same LWW sync engine from `packages/data` |

Sync doctrine: single-user product → **last-write-wins on `updated_at` is correct engineering, CRDTs are over-engineering.** Offline queue table `outbox(op, entity, payload, ts)` flushed on reconnect. Conflict = newer timestamp wins, loser archived to `conflict_log` for 30 days.

---

## §4 — DESIGN LANGUAGE · "FIRST LIGHT" SYSTEM

### 4.1 Direction & rationale

Grounded in her world: coaching = guiding people from where they are to first light; she works from **Pretoria — the Jacaranda City**. So the system is **dawn over the highveld**: a deep indigo night shell where data glows like sunrise, with jacaranda violet as the identity accent. This deliberately avoids the three AI-default looks (cream + terracotta serif; near-black + acid green; broadsheet hairlines) — the accent family here is a warm dawn *gradient* anchored by a botanical violet that is literally her city's signature.

Primary style commitment: **Glassmorphism-restrained on a dark shell** (one style, committed) with a full **Morning light theme** designed in parallel, not inverted.

### 4.2 Token system

**Color — Dawn (dark, default app shell)**
| Token | Hex | Role |
|---|---|---|
| `ink-950` | `#0E0F1A` | App background (indigo-night, never pure black) |
| `ink-900` | `#161827` | Surface / cards |
| `ink-800` | `#1F2233` | Raised surface, inputs |
| `glass` | `rgba(255,255,255,.06)` + `backdrop-blur(16px)` | Panels, rail |
| `jacaranda-400` | `#9A7BFF` | Primary accent, CTAs, focus rings (identity) |
| `amber-400` | `#F5A524` | Dawn gradient start · warnings/attention |
| `coral-400` | `#F87A6D` | Dawn gradient mid · streaks, energy |
| `sage-400` | `#5FBF9F` | Success, health-positive, "Strong" ratings |
| `text-hi` | `#F4F2ED` | Primary text (warm ivory, 13.9:1 on ink-950) |
| `text-lo` | `#9DA0B4` | Secondary text (≥4.6:1 on surfaces) |
| Semantic | error `#F0564F` · info `#6FA8F5` | Icons + text alongside color, never color-only |

Dawn gradient (hero, streaks, progress): `linear-gradient(135°, #F5A524 → #F87A6D → #9A7BFF)` — use at ≤10% of any screen.

**Color — Morning (light theme)**: bg `#F7F5F0` warm ivory · surface `#FFFFFF` · text `#1A1C2B` · same accents deepened one step (`jacaranda-600 #6E4FE0`, `sage-600 #2F8F6F`) for 4.5:1. Designed together with dark, contrast-tested separately.

**Typography**
| Role | Face | Fallback | Use |
|---|---|---|---|
| Display | **Gambetta** (Fontshare, variable serif) | Fraunces | H1/H2, greetings, Wheel labels — with restraint |
| Body/UI | **General Sans** (Fontshare) | Inter | Everything else, 400/500/600 |
| Data | **Space Grotesk** | JetBrains Mono | Scores, timers, table numerics |

Scale `12·14·16·18·22·28·36·48` · base 16px (never smaller on mobile) · body line-height 1.5, headings 1.15 · `font-display: swap`, preload the two critical weights only.

**Space & shape**: 4-pt scale (4/8/12/16/24/32/48/64) · radius `sm 8 / md 14 / lg 20 / pill 999` · elevation via layered soft shadows on light, via surface-step + 1px `rgba(255,255,255,.08)` inner border on dark.

### 4.3 Signature element — THE LIVING WHEEL

One place to spend all the boldness (everything else stays quiet):
- **App**: client-detail centerpiece. 10 spokes, score = spoke length, target = ghost ring. Idle: breathing ±2% scale, 4s sine. Scrub the timeline → wheel morphs between snapshots (600ms, expo-out), improved domains emit a brief particle drift in `sage-400`.
- **Marketing site hero**: the same wheel as a slowly rotating 3D bloom (R3F), reacting subtly to pointer (≤6° parallax), assembling from particles on load (1.2s orchestrated entrance, once).
- **Reduced motion**: static wheel + crossfade between snapshots. Non-negotiable.

### 4.4 Motion system

Perspective weighting for a daily-use SaaS dashboard: **Primary — Emil Kowalski** (restraint & speed: high-frequency interactions <300ms, no keyboard-triggered animation, scale-in from 0.96 never 0, correct transform-origin on popovers). **Secondary — Jakub Krehel** (production polish: every conditional render wrapped in AnimatePresence — zero motion gaps; enters = opacity + 8px translateY + slight blur; exits subtler and faster than enters; hover transitions ≥150ms; icon swaps = opacity+scale). **Selective — Jhey Tompkins** (delight ONLY in: onboarding, empty states, the Living Wheel, session-complete celebration, streak milestones).

| Token | Value | Use |
|---|---|---|
| `dur-instant` | 120ms | Hover, toggles, tab underline |
| `dur-fast` | 200ms | Dropdowns, tooltips, list items |
| `dur-base` | 300ms | Modals, drawers, page elements |
| `dur-slow` | 600ms | Wheel morphs, chart draw-ins |
| `dur-hero` | 1200ms | Once-per-load hero orchestration only |
| `ease-out-expo` | `cubic-bezier(.16,1,.3,1)` | Default enter |
| `ease-in-out` | `cubic-bezier(.65,0,.35,1)` | Morphs |
| Springs | bounce 0 (app) · bounce 0.25 (delight moments) | Framer Motion configs |

Laws: animate only `transform`/`opacity`/`filter` · stagger lists 30–50ms/item, cap 8 · every animation interruptible · global `prefers-reduced-motion` kill-switch shipped in the base stylesheet · loading states never snap (skeleton → content crossfade).

### 4.5 3D layer spec (web/desktop/mobile only)

Stack: React Three Fiber + drei + postprocessing (bloom, subtle). Philosophy from the current award-winning craft: **atmosphere over spectacle** — WebGL lights the product like a stage (the Iventions pattern: Three.js for lighting/mood, GSAP pacing the reveals), it never becomes a tech demo. Budgets: ≤1 canvas per route · ≤50k particles hero, ≤8k in-app · target 60fps, degrade to 30fps cap on `navigator.hardwareConcurrency ≤ 4` · `<Detailed>` LOD + `frameloop="demand"` when idle · full 2D SVG fallback when WebGL unavailable. Mobile: hero 3D on marketing pages only; in-app wheel uses the lighter bloom variant.

### 4.6 Reference sites — steal like a scholar

| Site | Steal this |
|---|---|
| linear.app | Rail navigation rhythm, keyboard-first speed, restraint |
| lusion.co | Pointer-reactive WebGL that stays elegant |
| igloo.inc | Cohesive 3D world-building, scroll pacing |
| basement.studio | Personality in type + micro-interactions |
| stripe.com | Gradient discipline, docs-grade clarity |
| activetheory.net | Loading sequences as brand moments |
| vercel.com | Dark-shell dashboard legibility |
| rive.app | Micro-animation polish, icon motion |
| awwwards.com/websites/animation | Ongoing scout: filter by GSAP + Three.js, study loaders/hovers/transitions as strategy not decoration |

### 4.7 Accessibility floor (Priority 1, ships in every build)

4.5:1 body / 3:1 large text (both themes tested) · visible 2px `jacaranda-400` focus ring, never removed · full keyboard nav + ESC closes everything · touch targets ≥44×44 · labels always visible (no placeholder-labels) · errors adjacent to fields · semantic HTML + aria on all custom widgets · axe-core: 0 critical issues gate.

---

## §5 — TECH STACK · ONE CORE, FOUR TARGETS

### 5.1 The strategic decision (read this before anything)

| Option | .exe | .dmg | App Store | Play Store | Code reuse | 2026 reality check |
|---|---|---|---|---|---|---|
| Electron + React Native | ✅ | ✅ | ✅ | ✅ | ~50% (two UI stacks) | Works, but 150MB+ binaries and double maintenance |
| Flutter everywhere | ✅ | ✅ | ✅ | ✅ | ~95% | One codebase, but Dart (new language) and weak fit for the award-tier animated *website* |
| **Tauri 2 everywhere** | ✅ | ✅ | ✅ | ✅ | ~95% | Desktop: production-solid (stable since Oct 2024, now on the 2.11 line — 2.11.5 shipped 1 Jul 2026; tiny <10MB binaries; Rust core = your language). Mobile: works and ships to both stores, but is the younger path — expect rough edges in plugin coverage, signing, and WebView quirks |
| **React core + Tauri desktop + Expo mobile** ⭐ | ✅ | ✅ | ✅ | ✅ | ~80% (logic/data/design 100%, UI ~70%) | The 2026 consensus: Expo (New Architecture era) is the battle-tested store pipeline — EAS Build handles signing, TestFlight, and Play submission almost turnkey |

**RECOMMENDED: the ⭐ hybrid.**
- `packages/core`, `packages/data`, `packages/ai`, design tokens → shared 100% across every target.
- **Web + HTML + Desktop** share the exact same React UI (Tauri just wraps it).
- **Mobile** re-skins the same components in React Native primitives via Expo — same brains, native store-grade body.
- **Path B (max-reuse variant):** if you'd rather run one shell everywhere, Tauri 2 mobile is viable — you already write Rust, which removes its biggest adoption barrier. Accept the rough edges consciously. Decide at Phase 4 (Pocket); nothing before then changes.

### 5.2 Monorepo layout

```
coachmillawellness/
├─ CLAUDE.md                     # §1–§5 of this compendium, pasted
├─ apps/
│  ├─ web/                       # Next.js 15 (App Router) — hosted site + full app
│  ├─ single/                    # Vite + vite-plugin-singlefile → CoachMillaWellness.html (Build 1)
│  ├─ desktop/                   # Tauri 2 (wraps packages/ui app shell)
│  └─ mobile/                    # Expo (Router), reuses core/data/ai/tokens
├─ packages/
│  ├─ ui/                        # React components, Tailwind v4, shadcn/ui base re-skinned to First Light
│  ├─ core/                      # Domain logic: scoring, checklist rules, coherence math (pure TS, unit-tested)
│  ├─ data/                      # Schema, Dexie/SQLite/Supabase adapters, LWW sync engine, export/import
│  ├─ ai/                        # Claude prompt templates + client (provider-agnostic wrapper)
│  └─ tokens/                    # §4.2 as CSS vars + Tailwind preset + TS constants (single source)
├─ .github/workflows/            # CI matrix: lint+test → web deploy → tauri-action (exe/dmg) → EAS
└─ turbo.json / pnpm-workspace.yaml
```

Toolchain: **pnpm + Turborepo · TypeScript strict · React 19 · Tailwind v4 · Zustand (client state) + TanStack Query (server state) · Motion (Framer) + GSAP (now fully free) + Lenis (site scroll) · R3F + drei (3D) · Recharts (dashboard charts) + custom SVG Wheel · Dexie / tauri-plugin-sql / expo-sqlite / Supabase-js · Vitest + Playwright.**
Repo: a fresh private `coachmillawellness` repo (recommended — client work stays isolated from your trading builds).

---

## §6 — BUILD 1 · THE SINGLE HTML ARTIFACT (her "always with me" copy)

Your proven hub pattern, evolved: one file, internal JS router, card-grid index → module pages.

| Item | Spec |
|---|---|
| Output | `CoachMillaWellness.html` — ONE file, zero external requests; works from a phone's Files app, a USB stick, or WhatsApp-forwarded |
| Build | `apps/single` → Vite + `vite-plugin-singlefile`; fonts subsetted + base64-inlined (Latin only); icons = inline Lucide SVG sprite |
| Scope | M0 Deck · M1 Clients · M2 Sessions (manual scorecard entry + full question banks) · M3 Wheel (2D SVG version — full interactions, no Three.js) · M4 Content Studio · M7 Vault |
| Excluded | 3D layer, cloud sync, auth (by design — this copy is private + offline) |
| Storage | IndexedDB (Dexie). NOTE for Claude Code: this file runs in a real local browser, so IndexedDB/localStorage are fine here — the "no browser storage" rule applies only to claude.ai artifact previews |
| AI | Optional v1.5: Settings accepts her Anthropic API key (stored locally only) → Session Analyzer calls the API directly. Ship v1 without it |
| Safety net | Vault: one-tap "Download backup (JSON)" + drag-drop restore, round-trip tested; auto-reminder toast every 14 days |
| Budget | ≤1.2MB gzipped · first paint <1s on a mid-range Android · Lighthouse perf ≥95 |

---

## §7 — BUILD 2 · THE HOSTED WEBSITE

| Layer | Choice | Why |
|---|---|---|
| Framework | Next.js 15, App Router, RSC | Marketing pages static + app shell client-side; one deploy |
| Host | Vercel (Hobby → Pro $20/mo when needed) | Zero-ops, preview deploys, edge |
| Backend | Supabase: Postgres + Auth (magic-link + Google) + Storage + RLS everywhere | Free tier carries a solo coach for a long time |
| Domain | Cloudflare Registrar (at-cost, ~$10/yr) or .co.za via a local registrar (~R100/yr). Candidates: `coachmillawellness.com`, `coachmillawellness.co.za`, `coachmilla.co.za` — check availability before P3 | DNS on Cloudflare, full SSL |
| AI proxy | Supabase Edge Function holds the Anthropic key server-side; the browser NEVER sees it | Non-negotiable security rule |
| Analytics | Plausible or Vercel Analytics | Cookie-light |
| Email | Resend (magic links, weekly digest) | Free tier fine |
| OG images | @vercel/og (satori) renders each Progress Link's wheel as its link-preview card | WhatsApp/iMessage unfurls become mini client reports |

Structure: `/` marketing (Living Wheel 3D hero, GSAP-paced scroll story of one coachee's transformation, Lenis smooth scroll — atmosphere over spectacle) · `/app/**` the authenticated dashboard (same `packages/ui` as desktop) · **`/p/<token>` Progress Links + `/pulse/<token>` Client Pulse — the zero-login client surface (M8), designed mobile-viewport-first because clients open these from WhatsApp** · `/privacy` + `/terms` (store submissions require these URLs — write them here once).

Pipeline: push → GitHub Actions (lint, typecheck, Vitest, Playwright smoke) → Vercel preview → merge to `main` = production. Supabase migrations via `supabase db push`, committed to the repo.

---

## §8 — BUILD 3 · DESKTOP + MOBILE APPS

### 8.1 Desktop — Tauri 2 (.exe + .dmg)

| Item | Spec |
|---|---|
| Wrap | `apps/desktop` loads the shared React app; Rust commands for SQLite, native file dialogs (export), system tray, notifications (session reminders) |
| Windows | Bundle NSIS `.exe` + `.msi`. Signing: **Azure Trusted Signing (~$9.99/mo)** = no SmartScreen scare; or ship unsigned for her personal use and sign when distributing publicly |
| macOS | Universal `.dmg` (aarch64 + x86_64). **Notarization is mandatory** on modern macOS → needs the Apple Developer account ($99/yr) + `notarytool` step in CI (tauri-action supports it) |
| Updates | Tauri updater plugin + signed update manifest on GitHub Releases |
| CI | `tauri-action` matrix (windows-latest, macos-latest) builds + attaches artifacts to each tagged release |

### 8.2 Mobile — Path A (recommended): Expo / React Native

`apps/mobile` — **PRIMARY №1**: Expo Router · NativeWind (Tailwind syntax → RN) · Reanimated 3 (wheel morphs) · Skia (2.5D wheel bloom) · expo-sqlite + the shared sync engine · expo-notifications (the full Nudge Engine — a genuine native capability that also defuses Apple's "just a website" objection) · react-native-view-shot + expo-sharing (Share Kit card renders → native share sheet, WhatsApp-optimized) · Universal/App Links so every `coachmillawellness.com` link opens in-app. EAS Build + EAS Submit = managed signing, TestFlight, and Play Console uploads. **Engagement features ship in the FIRST TestFlight build — they are this app's reason to exist.**
**Path B:** `tauri ios init` / `tauri android init` on the desktop app — choose only if Phase 4 testing shows the WebView wheel holds 60fps on her actual phone.

### 8.3 The store gauntlet (plan for this, don't discover it)

| Gate | Apple App Store | Google Play |
|---|---|---|
| Account | Apple Developer Program **$99/yr**; D-U-N-S number only if enrolling as a company (individual is fine to start) | Play Console **$25 once** |
| The big trap | **Guideline 4.2 Minimum Functionality** — apps that feel like wrapped websites get rejected. Mitigation: offline-first SQLite, push notifications, native share sheet, haptics on the wheel | **New personal accounts must run a closed test (~12–20 testers, 14 continuous days) before production access.** Recruit testers (family, coachees, your circles) during Phase 3 so the clock starts Day 1 of Phase 4 |
| Review time | Typically 24–48h per submission; budget 1–2 weeks for one rejection cycle | Hours–days once the testing requirement clears |
| Required assets | Privacy policy URL · privacy "nutrition label" · screenshots (6.7" + 5.5") · icon set | Privacy policy URL · Data Safety form · feature graphic 1024×500 · screenshots |
| Positioning | CoachMillaWellness is a coach's practice tool, **not a medical device** — state this plainly in both listings to avoid health-claims review friction | Same |

---

## §9 — AI COPILOT SPEC (Claude API)

Provider wrapper in `packages/ai`; default model Sonnet-class (cost/quality sweet spot), Haiku-class for the digest. Key location: Build 1 = user-supplied local key · Builds 2/3 = Supabase Edge Function proxy. Every call logged to `ai_run` with token counts + cost.

| Feature | Input | Output contract (JSON mode) | Trigger |
|---|---|---|---|
| Session Analyzer | Framework + session notes/transcript + coachee context | `{elements:[{element,rating,evidence,note}], checklist:{smarter_met,low_scores_flagged,will_step,review_date_set}, suggested_actions:[{title,due,review}], one_growth_tip}` | "Analyze session" button |
| Coherence Checker | Script/caption + pillar core message + last 5 posts | `{verdict:'on'/'drifting'/'off', why, one_line_fix, suggested_hook}` | Button on content card |
| Weekly Digest | Rollup of the week's data | `{clients_needing_attention[], content_gaps[], coach_tip, focus_sentence}` | Monday 06:00 cron (web) / on-open (local) |
| Prep Whisperer | Last session + open actions + wheel | `{recap_3_lines, suggested_opening_question, watchouts[]}` | Session prep card |

Prompt doctrine: the system prompt embeds Appendix A (her exact frameworks + closing rules) so the AI grades against HER methodology, not generic coaching. All outputs editable — AI proposes, coach disposes. Budget guardrail: soft cap ~$15/mo with a warning toast at 80%.

---

## §10 — DELIVERY ROADMAP & QUOTE SHEET (send this table to her)

Anchor Week 1 to your agreed start date. Each phase ends with something she USES, not a promise.

| Phase | Weeks | She receives | Internal milestones |
|---|---|---|---|
| P1 · First Light | Wk 1 | **`CoachMillaWellness.html` v1** on her phone + laptop: clients, sessions (manual scorecards + question banks), 2D Wheel, content studio, backup/restore | Monorepo + tokens + core + Dexie adapter |
| P2 · Copilot | Wk 2 | **v1.5**: AI Session Analyzer + Coherence Checker inside the HTML (her API key) + Coach Growth Curve chart | `packages/ai`, JSON contracts, cost log |
| P3 · Her domain — **PRIMARY №2** | Wk 3–4 | **Website live** on her domain: login, cloud sync, 3D Living Wheel hero, weekly digest — PLUS the client surface: **Progress Links, Client Pulse, WhatsApp-perfect OG previews** | Supabase schema+RLS, edge-function AI proxy, tokenized routes + OG renderer, CI, privacy/terms; recruit Play testers |
| P4 · Pocket — **PRIMARY №1** | Wk 5–7 | **TestFlight (iOS) + Play closed-test (Android) on her phone**: Share Kit, Nudge Engine, deep links, haptic wheel, offline sync. **Google's 14-day clock starts Day 1** | Expo app, EAS pipeline, store assets; Apple + Google accounts opened |
| P5 · Launch | Wk 8–10 | **Live on the App Store + Play Store** | Review cycles, rejection buffer, v1.0 tag |
| P6 · Cockpit | Wk 10–12 | **Windows .exe + macOS .dmg** — the auto-updating deep-work station (tray, desktop notifications) | tauri-action releases; macOS notarization reuses the P4 Apple account |

Rules of engagement for the client: weekly Sunday demo (15 min) · change requests batch to the next phase · the ICEBOX catches everything that isn't in §2.

### Running costs (≈R19/$ — verify rate at purchase)

| Item | Cost | When |
|---|---|---|
| Domain | ~R190/yr (.com) or ~R100/yr (.co.za) | P3 |
| Vercel + Supabase + Resend | R0 (free tiers) → ~R850/mo only at real scale | P3+ |
| Apple Developer | $99/yr ≈ R1,880 | P4 (also covers desktop notarization in P6) |
| Google Play Console | $25 once ≈ R475 | P4 (before the 14-day test) |
| Windows code signing | R0 (personal) → ~$10/mo when public | P6, optional |
| Claude API | ~R100–300/mo at her usage | P2+ |
| **Cash to reach store launch** | **≈ R2,500–3,500 + light subscriptions** | |

---

## §11 — CLAUDE CODE PROMPT PACK (paste in order)

**P0 · Standing context (put in CLAUDE.md):** Paste §1–§5 verbatim, then append:
> You are building CoachMillaWellness per this compendium. Laws: (1) tokens from `packages/tokens` only — never raw hex in components; (2) TypeScript strict, no `any`; (3) every conditional render animated (AnimatePresence) — no motion gaps; (4) `prefers-reduced-motion` respected globally; (5) animate only transform/opacity/filter; (6) all domain logic in `packages/core` with Vitest tests; (7) accessibility floor §4.7 is a merge blocker; (8) never hard-code API keys or real client names; (9) Mobile + Web are the PRIMARY surfaces — every client-facing capability ships on both first, desktop inherits, the HTML mirrors what fits offline. When a spec is ambiguous, choose the simplest option and leave a `// DECISION:` comment.

**P1 · Scaffold (Phase 1, day 1):**
> Initialize the pnpm+Turborepo monorepo exactly per §5.2. Create `packages/tokens` implementing §4.2 as CSS variables + a Tailwind v4 preset + TS constants (both themes). Create `packages/core` with entity types from §3.1 and pure functions: `scoreSession()`, `checklistFromSession()`, `coherenceMatrix()`, `wheelDelta()` — each with Vitest tests. Create `packages/data` with the Dexie adapter + `exportJSON()/importJSON()` round-trip tested. Acceptance: `pnpm test` green; a Ladle/Storybook page renders both themes' full token sheet.

**P2 · Build 1 shell:**
> In `apps/single`, build the single-file app per §6: hash-router shell, bottom-tab mobile nav / rail desktop nav, modules M0/M1/M2/M3(2D SVG wheel)/M4/M7 per §2, Dexie persistence, First Light dark theme default. Seed 2 fictional coachees + 6 content items. Acceptance: `pnpm build` emits ONE html ≤1.2MB gz; Lighthouse ≥95; export→wipe→import restores byte-identical state; axe 0 critical; reduced-motion verified.

**P3 · The Living Wheel (2D):**
> Implement §4.3's wheel as an SVG component in `packages/ui`: drag-to-score spokes, target ghost ring, snapshot timeline scrub with 600ms expo-out morphs, sage particle burst on improvement (CSS/SVG only), PNG export. 60fps on a mid-range phone; static+crossfade under reduced motion.

**P4 · AI Copilot:**
> Build `packages/ai` per §9: prompt templates embedding Appendix A, JSON-mode contracts, cost logging to `ai_run`. Wire Session Analyzer + Coherence Checker into Build 1 behind a Settings-provided key (stored in IndexedDB only). Every AI field editable before save.

**P5 · Website — PRIMARY №2:**
> Build `apps/web` per §7: marketing page with R3F Living Wheel hero (particle assembly entrance, pointer parallax ≤6°, GSAP-paced scroll story, Lenis), then the authed `/app` using `packages/ui`. Supabase schema from §3.1 with RLS `owner_id = auth.uid()`, magic-link auth, edge-function AI proxy, weekly digest cron. Then the CLIENT SURFACE (M8): tokenized `/p/<token>` Progress Link pages (mobile-viewport-first: Living Wheel + timeline + wins + next review date), `/pulse/<token>` check-in flow writing to `pulse_response`, consent + revoke UI inside client detail, and @vercel/og dynamic previews rendering each client's wheel. Acceptance: §12 gates incl. G10 unfurl + token security.

**P6 · Sync engine:**
> In `packages/data`, implement the LWW sync per §3.2: `outbox` queue, `updated_at` comparison, `conflict_log`, exponential-backoff retry. Property-based tests: 1,000 random op interleavings across 2 simulated devices converge to identical state.

**P7 · Mobile — PRIMARY №1:**
> Create `apps/mobile` (Expo) per §8.2: Expo Router tabs (Deck/Clients/Sessions/Content/More), NativeWind on tokens, Reanimated+Skia wheel, expo-sqlite + sync engine, offline-first. The ENGAGEMENT CORE ships in the first TestFlight: Share Kit (react-native-view-shot card renders → expo-sharing; 1080×1920 + 1080×1080 templates), full Nudge Engine with per-category toggles + quiet hours, haptics on wheel interactions, Universal/App Links opening `/p/*` and `/pulse/*` in-app. EAS profiles dev/preview/production; closed-test builds submitted Day 1. Acceptance: G10 in full.

**P8 · Desktop (cockpit):**
> Create `apps/desktop` (Tauri 2) wrapping the app shell: tauri-plugin-sql storage, native export dialog, tray, notification scheduling for review dates, updater. GitHub Actions via tauri-action producing signed/notarized artifacts per §8.1 (the Apple account already exists from P7).

**P9 · Store prep:**
> Generate both store listings: descriptions (coach practice tool, not medical), keyword sets, privacy-label answers derived from §3 (what we collect: coach-entered client notes; where: user's own account; no ads/tracking), screenshot scripts (Deck, Wheel morph, Scorecard, Coherence Map, Content calendar), Data Safety form answers, and the P4→P5 submission checklist including Google's 14-day closed test.

---

## §12 — VALIDATION GATES (GODMODE QA — a phase ships only when green)

| # | Gate | Standard |
|---|---|---|
| G1 | Unit tests | `packages/core` 100% branch on scoring/checklist/coherence; sync property tests pass |
| G2 | Round-trip | Export → wipe → import = deep-equal state (every build) |
| G3 | Performance | Lighthouse ≥95 (single + web) · wheel morph 60fps trace on mid-range Android · desktop cold start <2s |
| G4 | Motion audit | Zero motion gaps (grep conditional renders → AnimatePresence) · durations within §4.4 tokens · reduced-motion full pass |
| G5 | Accessibility | axe-core 0 critical · full keyboard walkthrough · both themes contrast-checked |
| G6 | Cross-platform smoke | Matrix: Chrome/Safari/Firefox · Win11 + macOS · one physical Android + one iPhone — 12-step script (add client → session → analyze → wheel → content → export) |
| G7 | Security | No key in any bundle (grep dist) · RLS verified with a second test account · deps audited |
| G8 | Data safety | 14-day backup nudge fires · conflict_log captures a forced conflict |
| G9 | Store pre-flight | 4.2-defense checklist (offline ✓ push ✓ native share ✓ haptics ✓) · listing assets complete |
| G10 | **Engagement (co-primary)** | WhatsApp unfurl of a Progress Link renders that client's wheel OG image · Share Kit PNG/WebM crisp on a real device · push delivered to a locked phone · tokens unguessable + revoke kills the page instantly · deep link opens the installed app · Pulse round-trip lands in the Engage inbox <10s |

---

## §13 — RISK REGISTER & REALITY ANCHORS

| Risk | Likelihood | Mitigation |
|---|---|---|
| Apple 4.2 rejection ("wrapped website") | Medium | Native capabilities baked in (§8.2); appeal letter drafted in advance highlighting offline + notifications + haptics |
| Google 14-day closed-test stalls launch | High if forgotten | Start the clock Day 1 of P4; tester list recruited during P3 |
| 3D tanks on older Androids | Medium | 2D fallback is first-class, not an afterthought; `frameloop="demand"`; device test on HER phone at P4 start |
| Scope creep (family client!) | High | Phase freeze + ICEBOX + the §10 table as the contract |
| Coachee data privacy — **POPIA** (she's processing clients' personal info in SA) | Certain obligation | Local-first by default; consent line in her client agreement; export/delete per client built into M7; wellness notes ≠ medical records — keep it that way in copy |
| API key leakage | Low if disciplined | Edge-function proxy (Builds 2/3); grep gate G7 |
| Progress/Pulse links expose client data | Medium | Per-client consent gate before the first link · first-name-only default · 128-bit tokens · one-tap revoke · optional expiry · view logging — plus the POPIA consent line in her client agreement |
| Single-dev bus factor | — | Everything in Git; releases tagged; her data always exportable without you |
| Platform shutdown risk (the reason to build) | — | Zero third-party coaching platform in the stack; Supabase is swappable Postgres |

**ICEBOX (v2+, do not build now):** FULL client portal (accounts, messaging, homework uploads — Pulse lite ships in v1 instead) · scheduling/payments · WhatsApp check-in bot · voice-note transcription · multi-coach teams · public template marketplace.

---

## APPENDIX A — HER METHODOLOGY (embed verbatim in AI prompts + Session Engine)

**Frameworks:** GROW = Goal → Reality → Options → Will. GREAT = Goals → Reality & Rapport → Explore → Achieve (the HOW + obstacles) → Take action.

**Question banks (from her live practice):**
- Goal: "What would you like to take out of this session?" · "What's your number one goal for today?" · content-goal pass: "What does success look like?" (the deeper goal must get its own explicit pass — her known gap)
- Reality: Wheel of Life scores across 10 domains → "Is there anything that stands out to you?" · emotional reality: "How does that make you feel?" · current state: "If I recall… what's happening now?" · reflective listening: "What I'm hearing you say…"
- Options/Explore: "What would you do with no constraints?" · "What would those close to you suggest?" · "Pros and cons of each option?" (historically skipped — the Session Engine surfaces these prominently)
- Achieve: negotiate the HOW (targeted vs spray-and-pray) · obstacle-proofing: "Is there anything that could stop you?" — push past dismissive answers
- Will/Take action: confidence 1–10 + commitment 1–10 → **both ≥8 = "cement the agreement" closing script (use it — historically skipped)** · week-by-week dated actions · **specific review date set before closing (e.g., Wed + next Sat)**

**Reminders checklist (auto-graded per session):** ✅ SMARTER goals met (incl. Exciting + Rewarded explicitly named) · ✅ Low Wheel scores flagged as a good sign (when present) · ✅ Ended with a Will/Take-action step · ✅ Review date set before closing.
**Joint-session rule:** each participant gets their own full GROW/GREAT cycle — a shared session must not collapse into one cycle.

**Wheel domains (default, editable):** Career · Finances · Health · Family · Romance/Partner · Personal Growth · Fun & Recreation · Physical Environment · Friends & Community · Spirituality/Purpose.

## APPENDIX B — ADHERENCE RATING RUBRIC (for `session_element_score`)

| Rating | Meaning |
|---|---|
| Strong | Element fully executed with her signature moves (e.g., heavy reflective listening in Rapport) |
| Adequate | Present but partial (e.g., goal front-loaded only, no success-definition pass) |
| Weak | Attempted but thin (e.g., obstacle question accepted a dismissive answer) |
| Met | Threshold behaviors satisfied (e.g., 8/10 trigger honored) even if script unused |
| N/A | Conditions didn't arise (e.g., no low scores to flag) |

---

*CoachMillaWellness · GODMODE Master Build Compendium v1.1 · Built to be handed to Claude Code section-by-section. Phase freeze is law; the Living Wheel is the soul; mobile + web are the front line; her data is hers forever.*
