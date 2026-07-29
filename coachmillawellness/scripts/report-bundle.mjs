#!/usr/bin/env node
/**
 * Gate G3 — the single-file budget.
 *
 * §6 sets a hard ceiling of 1.2MB gzipped for `CoachMillaWellness.html`, because
 * that file has to open from a phone's Files app and travel through WhatsApp.
 * Reporting the number after every build turns the budget into something visible
 * rather than something discovered late, and exceeding it fails the build.
 */

import { gzipSync } from 'node:zlib';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';

const DIST = resolve(import.meta.dirname, '../apps/single/dist');
const BUDGET_GZIP_BYTES = 1.2 * 1024 * 1024;

function human(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

let entries;
try {
  entries = readdirSync(DIST);
} catch {
  console.error(`No build output at ${DIST}.`);
  process.exit(1);
}

const htmlFiles = entries.filter((f) => f.endsWith('.html'));
if (htmlFiles.length === 0) {
  console.error('Build produced no HTML file.');
  process.exit(1);
}

// The whole point of Build 1 is that it is ONE file. More than one shipped
// asset means the inliner silently let something escape.
const strays = entries.filter((f) => !f.endsWith('.html') && statSync(join(DIST, f)).isFile());

let failed = false;
console.log('\nBuild 1 — single-file budget\n');

for (const file of htmlFiles) {
  const raw = readFileSync(join(DIST, file));
  const gzipped = gzipSync(raw, { level: 9 });
  const pct = ((gzipped.length / BUDGET_GZIP_BYTES) * 100).toFixed(1);
  const ok = gzipped.length <= BUDGET_GZIP_BYTES;
  if (!ok) failed = true;

  console.log(`  ${file}`);
  console.log(`    raw      ${human(raw.length)}`);
  console.log(`    gzipped  ${human(gzipped.length)}  (${pct}% of the 1.2MB budget)`);
  console.log(`    ${ok ? 'within budget' : 'OVER BUDGET'}\n`);
}

if (strays.length > 0) {
  console.error(`  Not a single file — ${strays.length} extra asset(s) emitted:`);
  for (const s of strays) console.error(`    ${s}`);
  console.error('  Everything must be inlined so the file works with zero external requests.\n');
  failed = true;
}

process.exit(failed ? 1 : 0);
