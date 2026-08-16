import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

import { themes, type ThemeColors, type ThemeName } from '../color.js';
import { parseColor } from '../contrast.js';
import { duration } from '../motion.js';
import { radius, space } from '../space.js';
import { fontSize } from '../typography.js';

/**
 * The token package claims to be a single source of truth, but it physically
 * holds two copies of every value: TypeScript constants (for SVG, canvas and
 * anything that computes) and CSS custom properties (for the DOM). This test is
 * what makes the claim true — the copies are compared value-by-value, so they
 * cannot silently diverge.
 *
 * Colours are compared numerically rather than as strings, so `0.1` vs `0.10`
 * and `#FFF` vs `#ffffff` are correctly treated as the same colour.
 */

const here = dirname(fileURLToPath(import.meta.url));
const css = readFileSync(resolve(here, '../tokens.css'), 'utf8');

/** Pulls the declaration body of a specific selector out of the stylesheet. */
function blockFor(selector: string): string {
  const index = css.indexOf(selector);
  if (index === -1) throw new Error(`Selector not found in tokens.css: ${selector}`);
  const open = css.indexOf('{', index);
  const close = css.indexOf('\n}', open);
  if (open === -1 || close === -1) throw new Error(`Unterminated block for ${selector}`);
  return css.slice(open + 1, close);
}

function declarationsIn(block: string): Map<string, string> {
  const out = new Map<string, string>();
  // Strip comments so a commented-out value can never be read as live.
  const clean = block.replace(/\/\*[\s\S]*?\*\//g, '');
  for (const match of clean.matchAll(/(--cmw-[a-z0-9-]+)\s*:\s*([^;]+);/g)) {
    out.set(match[1]!, match[2]!.trim().replace(/\s+/g, ' '));
  }
  return out;
}

const dawnBlock = declarationsIn(blockFor(':root {'));
const morningBlock = declarationsIn(blockFor(":root[data-theme='morning'] {"));

function varName(role: string): string {
  return `--cmw-${role.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`)}`;
}

const themeBlocks: Record<ThemeName, Map<string, string>> = {
  dawn: dawnBlock,
  morning: morningBlock,
};

describe('tokens.css mirrors the TypeScript constants', () => {
  it('parses both theme blocks', () => {
    expect(dawnBlock.size).toBeGreaterThan(20);
    expect(morningBlock.size).toBeGreaterThan(20);
  });

  describe.each(Object.keys(themes) as ThemeName[])('%s', (themeName) => {
    const roles = Object.keys(themes[themeName]) as Array<keyof ThemeColors>;

    it.each(roles)('%s matches', (role) => {
      const declared = themeBlocks[themeName].get(varName(role));
      expect(declared, `${varName(role)} missing from the ${themeName} block`).toBeDefined();

      const fromCss = parseColor(declared!);
      const fromTs = parseColor(themes[themeName][role]);

      expect(fromCss.r).toBeCloseTo(fromTs.r, 5);
      expect(fromCss.g).toBeCloseTo(fromTs.g, 5);
      expect(fromCss.b).toBeCloseTo(fromTs.b, 5);
      expect(fromCss.a).toBeCloseTo(fromTs.a, 5);
    });
  });

  it('declares every Morning role that Dawn declares', () => {
    // A role present in one theme but not the other means a component styled
    // against it silently falls back to the Dawn value on a light background.
    const dawnRoles = [...dawnBlock.keys()].filter((k) => !k.startsWith('--cmw-wheel-'));
    const missing = dawnRoles.filter(
      (k) => !morningBlock.has(k) && !isSharedAcrossThemes(k),
    );
    expect(missing).toEqual([]);
  });
});

/**
 * Identity, type, space and motion are intentionally theme-independent — they
 * are declared once in `:root` and inherited by Morning.
 */
function isSharedAcrossThemes(name: string): boolean {
  return (
    name.startsWith('--cmw-font-') ||
    name.startsWith('--cmw-text-') ||
    name.startsWith('--cmw-space-') ||
    name.startsWith('--cmw-radius-') ||
    name.startsWith('--cmw-dur-') ||
    name.startsWith('--cmw-ease-') ||
    name.startsWith('--cmw-leading-') ||
    name.startsWith('--cmw-gradient-') ||
    name.startsWith('--cmw-blur-') ||
    name === '--cmw-touch-target'
  );
}

describe('scale tokens mirror the TypeScript constants', () => {
  it.each(Object.entries(duration))('duration %s', (name, ms) => {
    expect(dawnBlock.get(`--cmw-dur-${name}`)).toBe(`${ms}ms`);
  });

  it.each(Object.entries(radius))('radius %s', (name, value) => {
    expect(dawnBlock.get(`--cmw-radius-${name}`)).toBe(value);
  });

  it.each(Object.entries(fontSize))('font size %s', (name, value) => {
    expect(dawnBlock.get(`--cmw-text-${name}`)).toBe(value);
  });

  it.each(Object.entries(space).filter(([name]) => name !== '0'))(
    'space %s',
    (name, value) => {
      expect(dawnBlock.get(`--cmw-space-${name}`)).toBe(value);
    },
  );
});

describe('the accessibility floor is present in the base stylesheet', () => {
  it('ships the global reduced-motion kill-switch', () => {
    // §4.4 calls this non-negotiable, so its absence should break the build.
    expect(css).toMatch(/@media \(prefers-reduced-motion: reduce\)/);
  });

  it('never removes the focus ring', () => {
    expect(css).toMatch(/:focus-visible/);
    expect(css).toMatch(/outline:\s*2px solid var\(--cmw-focus\)/);
    expect(css).not.toMatch(/outline:\s*(none|0)/);
  });
});
