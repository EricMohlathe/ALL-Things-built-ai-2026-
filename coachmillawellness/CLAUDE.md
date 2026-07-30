# CoachMillaWellness — standing context

This is prompt **P0** from the compendium's Prompt Pack: the context any agent
working on this repo should hold before touching a file. The full brief lives in
`docs/COMPENDIUM.md`; this is the operating summary plus the laws.

---

## What this is

A coaching practice platform for a solo health/life coach. One core, four
targets: a single offline HTML file, a hosted website, desktop, and mobile.

The product is one specific triad that no mainstream platform combines:

1. **Framework-adherence session grading** — her GROW/GREAT sessions scored
   against her own methodology, per element.
2. **A living Wheel of Life** — 10 domains over time, beautiful enough to
   screenshot into a client report.
3. **A content-coherence engine** — message pillars × published work, exposing
   drift at a glance.

Everything else is table stakes. If a change weakens one of those three, it is
the wrong change.

## Surface primacy

**Mobile and Web are co-primary.** Every client-facing capability ships on both
first. Desktop inherits the same React UI. The single HTML file mirrors what
fits offline.

The loop the whole product serves:
**prepare on desktop → engage from the phone → client receives via a web link →
client responds → the Deck surfaces it → next nudge.**

## Repository layout

```
coachmillawellness/
├─ apps/single/          Build 1 — CoachMillaWellness.html (one file, offline)
├─ packages/tokens/      First Light design system, single source of truth
├─ packages/core/        Domain logic. Pure TS, no I/O, no dependencies
├─ packages/data/        DataStore contract + Dexie/memory adapters + transfer
├─ packages/ui/          The shared React UI — primitives, wheel, all screens
└─ scripts/              Gate scripts (bundle budget, secret scan)
```

Packages are consumed as TypeScript source via Vite aliases and tsconfig paths —
there is no build step between them. One typecheck, one bundle.

---

## Laws

These are not preferences. A change that breaks one of them is wrong even if it
works.

1. **Tokens only.** Colour, type, space, radius and motion come from
   `@cmw/tokens`. A raw hex in a component is a review failure. Contrast is
   enforced by a test, not by eye.
2. **TypeScript strict, no `any`.** `noUncheckedIndexedAccess` is on.
3. **Every conditional render is animated.** Wrap in `AnimatePresence`; §4.4
   forbids motion gaps. Enters rise 8px and scale from 0.96, never 0. Exits are
   shorter and flatter than enters.
4. **`prefers-reduced-motion` is respected globally.** The kill-switch ships in
   the base stylesheet, and delight animations are omitted entirely rather than
   merely shortened.
5. **Animate only `transform`, `opacity`, `filter`.**
6. **All domain logic lives in `packages/core`, with tests.** Screens are
   renderers. If a screen computes a rule, the rule is in the wrong place.
7. **The accessibility floor (§4.7) is a merge blocker.** 4.5:1 body text in both
   themes, visible focus ring never removed, ≥44px targets, full keyboard
   operation, axe clean.
8. **Never hard-code an API key or a real client name.** Seed data uses
   fictional coachees ("Naledi M.", "Thabo K.").
9. **Mobile and Web are primary.** Desktop inherits; the HTML mirrors.

When a spec is ambiguous, choose the simplest option and leave a `// DECISION:`
comment explaining the choice.

## Two habits worth keeping

**Derived state is never stored.** Adherence, checklists, coherence and risk are
computed from `@cmw/core` at render time. There is one implementation of each
rule and no cache to go stale.

**Comments explain the decision, not the mechanism.** The code says what it
does. A comment earns its place by saying why this and not the obvious
alternative — especially where a plausible-looking approach was rejected.

---

## Commands

```bash
pnpm install                    # once
pnpm --filter @cmw/single dev   # dev server for Build 1
pnpm --filter @cmw/single build # emits apps/single/dist/CoachMillaWellness.html
pnpm -r test                    # unit tests, all packages
pnpm --filter @cmw/core test:coverage   # gate G1 — 100% branch on the rules
pnpm --filter @cmw/single exec playwright test   # gates G2, G5, G6
node scripts/gate-no-secrets.mjs        # gate G7
```

## Validation gates

A phase ships when its gates are green. Current state:

| Gate | What | Status |
|---|---|---|
| G1 | 100% branch coverage on scoring/checklist/coherence/wheel | green |
| G2 | Export → wipe → import round-trips exactly | green |
| G3 | Single file ≤1.2MB gzipped | green, ~191KB |
| G4 | Motion audit — no gaps, reduced-motion pass | green |
| G5 | axe: no critical or serious, both themes | green |
| G6 | 12-step smoke script over `file://` | green |
| G7 | No credential in any shipped file | green (script) |
| G8 | 14-day backup nudge | green |
| G9 | Store pre-flight | not started (P4/P5) |
| G10 | Engagement — Progress Links, Share Kit, push | not started (P3/P4) |

## Where the phases stand

- **P1 · First Light — done.** Monorepo, tokens, core, data, and the single-file
  app with modules M0/M1/M2/M3/M4/M7.
- **P2 · Copilot — next.** `packages/ai`, Session Analyzer, Coherence Checker,
  Coach Growth Curve chart. The core functions and the `ai_run` cost table
  already exist; the seams are marked.
- **P3 · Website (co-primary №2)** — `apps/web`, Supabase, and the M8 client
  surface: Progress Links, Client Pulse, OG previews.
- **P4 · Pocket (co-primary №1)** — `apps/mobile` (Expo), Share Kit, Nudge
  Engine. Google's 14-day closed test starts day 1.
- **P5 · Launch**, **P6 · Desktop cockpit**.

## What is deliberately not built yet

Not oversights — sequencing:

- **AI (M6).** §6 says ship Build 1 without it. The Deck's focus sentence is
  deterministic so it works offline and with no key; the Copilot replaces it in
  P2 and has a quality bar to beat.
- **Insights Observatory (M5).** Excluded from Build 1 by §6. `coachGrowthCurve`
  is written and tested; it has no screen yet.
- **Engage (M8).** Schema, share-token minting and `firstName` privacy helper
  are in place. The surfaces are web and mobile work.
- **Webfonts.** Build 1 must make zero network requests, so Gambetta and General
  Sans need subsetting and base64 inlining as a build step. Until then the
  fallback chain carries the typography.
- **Sync engine (P6 in the prompt pack).** The `DataStore` contract and the
  `outbox`/`conflict_log` shape are designed for it.
