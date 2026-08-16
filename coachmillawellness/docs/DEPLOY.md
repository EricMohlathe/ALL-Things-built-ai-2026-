# Deploying CoachMillaWellness

The build emits **one self-contained HTML document, twice**:

| File | For |
|---|---|
| `index.html` | The hosted site — static hosts serve this at `/` |
| `CoachMillaWellness.html` | The copy she keeps and opens offline |

They are byte-identical, and gate G3 fails the build if they ever aren't. That is
the whole deployment story: the site *is* the app, the app is downloadable from
the site, and neither can drift from the other.

```bash
cd coachmillawellness
pnpm install
pnpm --filter @cmw/single build
# → apps/single/dist/{index.html, CoachMillaWellness.html}
```

Because it is one document with zero external requests, **any static host works
with no configuration at all** — upload `apps/single/dist` and it runs. There is
no server, no API, no build-time secret and no runtime environment variable.
Everything below is hardening and convenience, not requirement.

---

## Netlify — the configured path

`netlify.toml` lives at the **repository root**, because that is the only place
Netlify reads it from, while the app is a monorepo one level down. `base` bridges
the two.

**Connect the repo and it just builds.** No dashboard settings are needed; the
file specifies base, command, publish directory, Node and pnpm versions.

For a one-off deploy without connecting Git:

```bash
cd coachmillawellness
pnpm --filter @cmw/single build
npx netlify-cli deploy --prod --dir apps/single/dist
```

Note that a CLI deploy uploads the folder but does **not** read `netlify.toml`'s
headers — those come from the build plugin during a Git-connected build. For a
CLI-only workflow, copy the headers into a `_headers` file in the publish
directory instead.

### If the build fails on Netlify

- **"No lockfile found" / installs nothing** — `base` is not set to
  `coachmillawellness`. Netlify installs dependencies in the base directory.
- **Wrong pnpm version** — `PNPM_VERSION` is pinned in `[build.environment]`;
  the lockfile is `lockfileVersion` from pnpm 10.
- **Published an empty site** — `publish` is relative to `base`, so it is
  `apps/single/dist`, not `coachmillawellness/apps/single/dist`.

## Vercel

`vercel.json` at the repository root configures the same build, the same headers
and the same redirects. It exists because this repository is already connected to
a Vercel project; without it that project deploys the repo root, which is not a
site.

## Cloudflare Pages

No config file is committed, because Cloudflare takes these from the dashboard:

- **Build command:** `cd coachmillawellness && pnpm --filter @cmw/single build`
- **Build output directory:** `coachmillawellness/apps/single/dist`
- **Environment:** `NODE_VERSION=22`

To get the same headers, add a `_headers` file to the publish directory as a
build step. It is deliberately not committed into `dist`: gate G3 fails on any
non-HTML file there, which is what keeps the "one file" promise honest.

## GitHub Pages, S3, nginx, a USB stick

Upload `apps/single/dist`. There is nothing else to do.

The router is **hash-based** (§6 — the file must work over `file://`, where no
server exists to answer a path), so **no SPA rewrite rule is needed anywhere**.
Every route is already served by the one document. If a host's documentation
tells you to add a catch-all rewrite to `/index.html`, you can skip it here.

---

## The headers, and why these

Set by `netlify.toml` and `vercel.json`, and asserted by
`apps/single/e2e/hosted.spec.ts` against a local server that mirrors them.

**`Content-Security-Policy`** — `default-src 'none'`, opened only where the app
genuinely needs it. `script-src`/`style-src` allow `'unsafe-inline'`, which is not
a concession but the direct consequence of §6: everything is inlined into the
document, so there is no external origin to allow and nothing to hash against.
What the policy still buys is real — no other origin can be contacted, framed or
loaded from. `connect-src` names exactly one destination, `https://api.anthropic.com`,
which is the only outbound request the app can ever make and only when she has
pasted in a key.

**`Cache-Control: max-age=0, must-revalidate`** — the document *is* the
application, so a stale cache is a stale app. At ~249KB gzipped the revalidation
costs nothing worth saving.

**`Content-Disposition: attachment`** on `CoachMillaWellness.html` — that URL is
the copy she keeps, so clicking it should put a file on her device rather than
open a second copy in the tab. The in-app download button does not rely on this
header (it uses an anchor with `download`), so hosts that ignore it still work.

**`X-Frame-Options`/`frame-ancestors`** — her coachees' notes are on the page.
Nothing should be able to frame it.

## Verifying a deployment

The hosted shape has its own gate, because every other browser test runs over
`file://` and cannot see these failures:

```bash
pnpm --filter @cmw/single build
pnpm --filter @cmw/single exec playwright test --project=hosted
```

That starts a local server sending the production headers and asserts the root
URL is the app, the CSP does not blank it, IndexedDB persists across a reload on
an http origin, no third-party request is made, the download is byte-identical to
the page being served, and both redirects resolve.

Against a real deployment:

```bash
CMW_HOSTED_BASE=https://your-site.netlify.app \
  pnpm --filter @cmw/single exec playwright test --project=hosted
```

## What is not here

**No PWA manifest, and no service worker.** Both are tempting for a
"install to home screen" story and both are the wrong shape for this product:
a manifest is a second file, which the downloaded artefact would reference and
fail to find, and a service worker caching a document that is already local is
machinery with nothing to do. The real mobile answer is `apps/mobile` in P4 —
a native app with notifications, the share sheet and haptics, which is also what
defuses Apple's Guideline 4.2 (see `docs/STORE-PREP.md`).

**No environment variables.** Her Anthropic key is pasted into Settings and lives
in her browser's IndexedDB; it is never a build input. When the hosted build
moves to the Edge Function proxy (P3), the key lives in Supabase secrets and
still never reaches the client — see `supabase/README.md`.
