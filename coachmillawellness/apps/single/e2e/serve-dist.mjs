#!/usr/bin/env node
/**
 * Serves `dist/` with the headers `netlify.toml` sets in production.
 *
 * The point is not to emulate Netlify — it is to make the deployed *contract*
 * testable. The Content-Security-Policy in particular is the kind of thing that
 * looks harmless in a config file and silently blanks the app in a browser, and
 * a header set only in production is a header nobody has run the test suite
 * against. This server is deliberately hard-coded rather than parsing the TOML:
 * a test that derives its expectations from the file it is checking cannot fail.
 *
 * Any static host with equivalent headers will behave the same, which is what
 * makes "deployable anywhere" a claim rather than a hope.
 */

import { createReadStream, existsSync, statSync } from 'node:fs';
import { createServer } from 'node:http';
import { extname, join, normalize, resolve } from 'node:path';

const DIST = resolve(import.meta.dirname, '../dist');
const PORT = Number(process.env.PORT ?? 4173);

/** Kept in step with netlify.toml by hand, and asserted against by the tests. */
export const CSP = [
  "default-src 'none'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self' data:",
  "connect-src 'self' https://api.anthropic.com",
  "base-uri 'none'",
  "form-action 'none'",
  "frame-ancestors 'none'",
  "object-src 'none'",
].join('; ');

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8',
};

const server = createServer((request, response) => {
  const url = new URL(request.url ?? '/', 'http://localhost');

  // `/app` and `/download` are the two redirects netlify.toml declares.
  if (url.pathname === '/app') {
    response.writeHead(302, { location: '/#/deck' });
    response.end();
    return;
  }
  if (url.pathname === '/download') {
    response.writeHead(302, { location: '/CoachMillaWellness.html' });
    response.end();
    return;
  }

  // `normalize` before joining, so `..` cannot escape the publish directory.
  const requested = normalize(decodeURIComponent(url.pathname)).replace(/^(\.\.[/\\])+/, '');
  const candidate = join(DIST, requested === '/' ? 'index.html' : requested);

  if (!candidate.startsWith(DIST) || !existsSync(candidate) || !statSync(candidate).isFile()) {
    response.writeHead(404, { 'content-type': 'text/plain' });
    response.end('Not found');
    return;
  }

  const headers = {
    'content-type': TYPES[extname(candidate)] ?? 'application/octet-stream',
    'content-security-policy': CSP,
    'x-content-type-options': 'nosniff',
    'referrer-policy': 'no-referrer',
    'x-frame-options': 'DENY',
    'permissions-policy': 'camera=(), microphone=(), geolocation=(), payment=(), usb=()',
    'cache-control': 'public, max-age=0, must-revalidate',
  };

  if (candidate.endsWith('CoachMillaWellness.html')) {
    headers['content-disposition'] = 'attachment; filename="CoachMillaWellness.html"';
  }

  response.writeHead(200, headers);
  createReadStream(candidate).pipe(response);
});

server.listen(PORT, () => {
  console.log(`serving ${DIST} on http://localhost:${PORT}`);
});
