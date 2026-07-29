#!/usr/bin/env node
/**
 * Gate G7 — no key in any bundle.
 *
 * The compendium states this as "grep dist", so it is wired as a real command
 * that fails a build rather than a habit someone has to remember. Runs over
 * every built artifact and looks for the shapes an Anthropic or Supabase
 * credential actually takes, plus anything that looks like a committed .env.
 *
 * Build 1 legitimately stores a user-supplied API key at runtime (in IndexedDB,
 * on her own device). That is fine. What must never happen is a key baked into
 * a shipped file.
 */

import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';

const ROOT = resolve(import.meta.dirname, '..');

const SEARCH_ROOTS = ['apps/single/dist', 'apps/web/.next', 'apps/web/out', 'apps/desktop/dist'];

const TEXT_EXTENSIONS = new Set(['.html', '.js', '.mjs', '.cjs', '.css', '.json', '.map', '.txt']);

/**
 * Each pattern targets a real credential format. Deliberately not a generic
 * "40+ chars of base64" rule — that fires on minified code and sourcemaps, and a
 * gate that cries wolf gets switched off.
 */
const PATTERNS = [
  { name: 'Anthropic API key', re: /sk-ant-[A-Za-z0-9_-]{20,}/ },
  { name: 'OpenAI-style API key', re: /\bsk-[A-Za-z0-9]{32,}\b/ },
  { name: 'Supabase service-role JWT', re: /eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\./ },
  { name: 'AWS access key id', re: /\bAKIA[0-9A-Z]{16}\b/ },
  { name: 'Google API key', re: /\bAIza[0-9A-Za-z_-]{35}\b/ },
  { name: 'GitHub token', re: /\bgh[pousr]_[A-Za-z0-9]{36,}\b/ },
  { name: 'Private key block', re: /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/ },
];

function* walk(dir) {
  let entries;
  try {
    entries = readdirSync(dir, { withFileTypes: true });
  } catch {
    return; // Target not built in this run — nothing to check.
  }
  for (const entry of entries) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) yield* walk(path);
    else if (entry.isFile()) yield path;
  }
}

const findings = [];
let scanned = 0;

for (const searchRoot of SEARCH_ROOTS) {
  const absolute = join(ROOT, searchRoot);
  try {
    statSync(absolute);
  } catch {
    continue;
  }

  for (const file of walk(absolute)) {
    const dot = file.lastIndexOf('.');
    const extension = dot === -1 ? '' : file.slice(dot);
    if (!TEXT_EXTENSIONS.has(extension)) continue;

    scanned += 1;
    const contents = readFileSync(file, 'utf8');
    for (const { name, re } of PATTERNS) {
      const match = re.exec(contents);
      if (match) {
        findings.push({ file: relative(ROOT, file), name, sample: match[0].slice(0, 12) });
      }
    }
  }
}

if (scanned === 0) {
  console.log('G7: no built artifacts found. Run a build first — nothing was checked.');
  process.exit(0);
}

if (findings.length > 0) {
  console.error(`G7 FAILED — ${findings.length} possible secret(s) in shipped output:\n`);
  for (const f of findings) {
    console.error(`  ${f.file}\n    ${f.name} (starts "${f.sample}…")`);
  }
  console.error('\nMove the credential behind the Edge Function proxy, or out of the bundle.');
  process.exit(1);
}

console.log(`G7 passed — ${scanned} shipped file(s) scanned, no credentials found.`);
