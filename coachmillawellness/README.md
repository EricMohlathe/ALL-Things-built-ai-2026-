# Coach Milla Wellness

A coaching practice platform for a solo health & life coach. Local-first, hers
forever — no account, no subscription, and her data exports whole at any time.

**Phases 1–2 are complete**: `CoachMillaWellness.html` — one file, zero external
requests, opens from a phone's Files app or a WhatsApp forward, with the AI
Copilot inside it and optional.

```bash
pnpm install
pnpm --filter @cmw/single build
# → apps/single/dist/CoachMillaWellness.html   (248 KB gzipped)
```

Open that file directly in a browser. No server.

---

## What it does

| Module | What she gets |
|---|---|
| **Command Deck** | An 8-second answer to "what does today need from me?" — today's sessions, slipped reviews, coachees drifting, content due, streaks |
| **Coachee Constellation** | One screen per human: goals with SMARTER flags, wheel history, sessions, an action kanban with review dates, private notes |
| **Session Engine** | GROW and GREAT graded per element against her own question banks, with the reminders checklist auto-graded and the closing script surfaced exactly when it is owed |
| **Wheel of Life Lab** | The Living Wheel — drag or keyboard to score, timeline scrub between snapshots, before/after split view, PNG export |
| **Content Studio** | Message pillars, pipeline, publishing consistency, and the coherence map that shows whether what she posts matches what she stands for |
| **Insights Observatory** | The Coach Growth Curve — her adherence per element, month by month — plus client movement and what the Copilot has cost |
| **AI Copilot** | Session Analyzer, Coherence Checker, Weekly Digest and Prep Whisperer, graded against her own frameworks. Optional: no key, no nagging |
| **Vault** | One-tap backup, drag-and-drop restore, CSV export, the 14-day backup nudge, AI key and budget, and a plain-language POPIA note |

## Three things it does that bought platforms do not

1. **It grades the coach.** Every session is scored per framework element, so her
   own pattern becomes visible over months — the compendium notes Options and the
   obstacle question as the steps she tends to skip, and the app marks them.
2. **The wheel is alive.** Ten domains, a ghost target ring, and a scrubber that
   morphs between snapshot dates. Exportable as a PNG she can send a client.
3. **It catches message drift.** Pillars × published work, with starved pillars
   named in words rather than implied by a pale square.

And the Copilot does the one thing a general chat assistant cannot: it grades
against *her* methodology, because the system prompt is rendered from the same
`frameworks.ts` the Session Engine reads. Edit a question bank and the AI's
standard moves with it.

## Architecture

One core, four targets. `packages/core` is pure TypeScript with no I/O and no
dependencies, so the same rules run in a browser, a Tauri webview, React Native
and Node. `packages/ui` is the React app that the single file, the website and
the desktop shell all mount — only the storage adapter differs.

See **CLAUDE.md** for the operating context and laws, **MIGRATION.md** for lifting
this into its own repo, and **docs/COMPENDIUM.md** for the full build brief.

## Quality

Not aspirations — commands.

```bash
pnpm -r test                                      # 533 unit tests
pnpm --filter @cmw/core test:coverage             # 100% branch on the rules
pnpm --filter @cmw/single exec playwright test    # 25 browser tests over file://
node scripts/gate-no-secrets.mjs                  # no credential in any bundle
```

The design system verifies itself: the token package holds three copies of every
value (TypeScript, CSS variables, Tailwind theme) and a parity test fails the
build if they disagree. A contrast test enforces the 4.5:1 floor in both themes
and has already caught three colours that looked fine and were not.

## Costs to date

R0. No domain, no hosting, no store accounts, no subscriptions — Phase 1 is a
file. Spending starts at Phase 3 (domain ~R190/yr) and Phase 4 (Apple $99/yr,
Google $25 once).
