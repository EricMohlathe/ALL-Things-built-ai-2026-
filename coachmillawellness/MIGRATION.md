# Migration — lifting this into its own repo

The whole procedure for moving this build into a repo of its own, written so it
works cold — nothing in it depends on the conversation that produced the code.

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

Two small things:

- **Move the CI workflow in.** It currently sits at the *parent* repo's root as
  `.github/workflows/coachmillawellness-ci.yml`, because GitHub Actions only reads
  workflows from the repository root — a copy inside `coachmillawellness/` looks
  correct and silently never runs. After extraction, move it to
  `.github/workflows/ci.yml` in the new repo and delete its `defaults.run.
  working-directory` block and the `paths:` filters, which exist only to scope it
  to a subdirectory.
- The Playwright config prefers a Chromium already on the machine (a CI-image
  concern). On your own machine run `pnpm exec playwright install chromium` once
  and it will use that instead — the config falls through automatically.

Nothing else is environment-specific. There are no secrets, no `.env`, no
hard-coded paths, and no network calls at build or run time.

---

## Handing this to an agent cold

Point it at `CLAUDE.md` first — that is prompt P0, and it carries the laws, the
gate status and the phase state. Then `docs/COMPENDIUM.md` for the full brief.

The three things an agent most needs to know, which are easy to miss:

1. **`packages/core` is the rulebook.** (`packages/ai` reads from it and adds no
   rules of its own — the AI proposes ratings, `scoreSession` still decides what
   they mean.) Session adherence, the reminders
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
pnpm -r test                                      # 533 unit tests
pnpm --filter @cmw/core test:coverage             # G1: 100% branch
pnpm --filter @cmw/single build                   # G3: reports % of budget used
pnpm --filter @cmw/single exec playwright test    # G2, G5, G6: 25 browser tests
node scripts/gate-no-secrets.mjs                  # G7
```

Then open `apps/single/dist/CoachMillaWellness.html` directly in a browser — no
server. It should load, offer the sample practice, and persist across a reload.
That is the deliverable, and that is how she will open it.

---

## What to build next, and where the seams are

The compendium's phase order is P2 → P3 → P4. Each has a seam already cut:

**P2 · Copilot (`packages/ai`) — built.** Three things about it are worth knowing
before changing anything:

- **The system prompt is rendered, not written.** `methodologyPrompt()` builds
  Appendix A from `packages/core/src/frameworks.ts`, so editing a question bank
  moves the AI's standard with it. A hand-written copy of the prompt would be the
  single fastest way to break the product's core claim.
- **`AiTransport` is the only integration point.** Every test fakes it, and it is
  where the two key strategies diverge: `anthropicTransport` for a key she pastes
  in locally, `proxyTransport` for the Edge Function. §7's rule that the browser
  never sees the key applies to the hosted builds, and `proxyTransport` already
  speaks the wire format that function has to answer.
- **The ledger is the cache.** `latestRun()` reads a stored `ai_run` output back
  through its own contract, which is how the Deck shows Monday's brief on
  Wednesday without a second call or a second table. Stored output is re-validated
  rather than trusted, so a row from an older build renders as absent instead of
  crashing a screen.

**P3 · Website (`apps/web`)**
- Mount the same `CmwApp` with a Supabase-backed `DataStore`. The contract is
  five methods (`packages/data/src/store.ts`).
- `share_link` and `pulse_response` entities and `shareToken()` (128-bit,
  CSPRNG-only, refuses to degrade) are already written and tested.
- `firstName()` in `packages/core/src/people.ts` is the first-name-only default
  for client-facing surfaces — use it rather than formatting names ad hoc.
- The Anthropic key goes in an Edge Function, never the browser. `gate-no-secrets`
  already scans `apps/web/.next` if it exists. The function's request shape is
  fixed by `proxyTransport` in `packages/ai/src/provider.ts` — note that the body
  carries no key field at all, so a misconfigured deployment fails closed rather
  than accepting a credential from a client.

**P4 · Mobile (`apps/mobile`)**
- `packages/core`, `packages/data` and `packages/tokens` port unchanged — they
  have no DOM dependency. `packages/ui` is the part that gets re-skinned in React
  Native primitives.
- The wheel's geometry is pure functions in `packages/ui/src/wheel/geometry.ts`,
  so a Skia or Reanimated wheel can reuse the maths rather than re-deriving it.
- Open the Google Play account early: a new personal account must run a ~14-day
  closed test before production, and that clock is the critical path.
