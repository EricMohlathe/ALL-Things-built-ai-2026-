# Migration — lifting this into its own repo

You said you'll want to move this build to your main Claude at some point. This
is the whole procedure, written so it works cold — nothing in it depends on the
conversation that produced the code.

## Why it lifts cleanly

The compendium recommends a fresh private `coachmillawellness` repo so client
work stays isolated from your trading builds. That is the right call, and this
build was written for it: everything lives under one directory, with no imports
reaching outside it and no shared config with the parent repo. `coachmillawellness/`
*is* the monorepo root — its own `package.json`, `pnpm-workspace.yaml`,
`tsconfig.base.json` and `.gitignore`.

So the move is a copy, not a refactor.

---

## Option A — new repo, history preserved (recommended)

Keeps the commits, which matter here because several of them record *why* a
colour or a type shape is what it is.

```bash
# 1. From a clone of this repo, extract the subdirectory into its own history.
#    git-filter-repo is the maintained tool; `git subtree split` also works.
git clone <this-repo> cmw-extract && cd cmw-extract
git filter-repo --subdirectory-filter coachmillawellness

# 2. Point it at the new empty private repo and push.
git remote remove origin
git remote add origin git@github.com:<you>/coachmillawellness.git
git push -u origin main

# 3. Verify from scratch.
pnpm install
pnpm -r test
pnpm --filter @cmw/single build
pnpm --filter @cmw/single exec playwright test
```

If `git filter-repo` isn't available:

```bash
git subtree split --prefix=coachmillawellness -b cmw-only
git push git@github.com:<you>/coachmillawellness.git cmw-only:main
```

## Option B — clean slate

If you'd rather start the history fresh:

```bash
cp -r coachmillawellness /path/to/coachmillawellness
cd /path/to/coachmillawellness
rm -rf node_modules apps/single/dist apps/single/test-results .turbo
git init && git add -A && git commit -m "CoachMillaWellness — Phase 1"
```

## After the move

Two small things, neither urgent:

- `apps/single/shots.mjs` is a screenshot helper used while building. Keep it or
  delete it; nothing imports it.
- The Playwright config prefers a Chromium already on the machine (a CI-image
  concern). On your own machine `pnpm exec playwright install chromium` once, and
  it will use that instead — the config falls through automatically.

Nothing else is environment-specific. There are no secrets, no `.env`, no
hard-coded paths, and no network calls at build or run time.

---

## Handing this to an agent cold

Point it at `CLAUDE.md` first — that is prompt P0, and it carries the laws, the
gate status and the phase state. Then `docs/COMPENDIUM.md` for the full brief.

The three things an agent most needs to know, which are easy to miss:

1. **`packages/core` is the rulebook.** Session adherence, the reminders
   checklist, coherence maths and the wheel deltas are all pure functions there,
   at 100% branch coverage. A screen that re-implements one of those rules is a
   bug even if it renders correctly.
2. **`packages/tokens` is self-verifying.** The TypeScript constants, the CSS
   custom properties and the Tailwind bridge hold three copies of every value; a
   parity test fails the build if they disagree, and a contrast test enforces the
   accessibility floor. Change a colour in one place and the test will tell you
   about the other two.
3. **The gates are runnable commands, not a checklist.** See CLAUDE.md.

## Verifying the move worked

```bash
pnpm install
pnpm -r test                                      # 408 unit tests
pnpm --filter @cmw/core test:coverage             # G1: 100% branch
pnpm --filter @cmw/single build                   # G3: reports % of budget used
pnpm --filter @cmw/single exec playwright test    # G2, G5, G6: 19 browser tests
node scripts/gate-no-secrets.mjs                  # G7
```

Then open `apps/single/dist/CoachMillaWellness.html` directly in a browser — no
server. It should load, offer the sample practice, and persist across a reload.
That is the deliverable, and that is how she will open it.

---

## What to build next, and where the seams are

The compendium's phase order is P2 → P3 → P4. Each has a seam already cut:

**P2 · Copilot (`packages/ai`)**
- The `ai_run` entity exists in `packages/core/src/types.ts` with token and cost
  fields, so cost transparency is a matter of writing rows.
- `SETTING_KEYS.anthropicApiKey` exists and is excluded from exports by
  `UNEXPORTED_SETTING_KEYS` — a backup she forwards will not carry her key.
- `frameworks.ts` holds Appendix A as data. Embed it in the system prompt from
  there rather than re-typing it; that is what makes the AI grade against *her*
  methodology.
- `scoreSession` already accepts hand-entered ratings, so the Analyzer only needs
  to *propose* ratings. Nothing downstream changes.
- The Deck's `focus` sentence is the natural first swap — it is deterministic
  today and marked in `deck.ts`.

**P3 · Website (`apps/web`)**
- Mount the same `CmwApp` with a Supabase-backed `DataStore`. The contract is
  five methods (`packages/data/src/store.ts`).
- `share_link` and `pulse_response` entities and `shareToken()` (128-bit,
  CSPRNG-only, refuses to degrade) are already written and tested.
- `firstName()` in `packages/core/src/people.ts` is the first-name-only default
  for client-facing surfaces — use it rather than formatting names ad hoc.
- The Anthropic key goes in an Edge Function, never the browser. `gate-no-secrets`
  already scans `apps/web/.next` if it exists.

**P4 · Mobile (`apps/mobile`)**
- `packages/core`, `packages/data` and `packages/tokens` port unchanged — they
  have no DOM dependency. `packages/ui` is the part that gets re-skinned in React
  Native primitives.
- The wheel's geometry is pure functions in `packages/ui/src/wheel/geometry.ts`,
  so a Skia or Reanimated wheel can reuse the maths rather than re-deriving it.
- Open the Google Play account early: a new personal account must run a ~14-day
  closed test before production, and that clock is the critical path.
