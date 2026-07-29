import { describe, expect, it } from 'vitest';

import {
  chipTintPct,
  palette,
  themeNames,
  themes,
  wheelHues,
  type ThemeColors,
} from '../color.js';
import { contrastRatio, tintOver, WCAG } from '../contrast.js';

/**
 * Gate G5 / §4.7, as executable code rather than a promise.
 *
 * "both themes tested" in the compendium means exactly this: every pairing the
 * UI can actually produce is measured here, and a token change that breaks the
 * floor fails the build instead of shipping. Two colours in the compendium's
 * own suggested palette did not survive this test and were deepened — see the
 * DECISION comments in color.ts.
 */

/** Backdrops a piece of text can legitimately land on. */
const textBackdrops: Array<keyof ThemeColors> = ['bg', 'surface', 'surfaceRaised'];

/** Roles that carry words, and therefore owe 4.5:1. */
const textRoles: Array<keyof ThemeColors> = ['textHi', 'textLo'];

/** Semantic families: the `-ink` member is text, the bare member is a fill. */
const semanticFamilies = [
  { fill: 'accent', ink: 'accentText' },
  { fill: 'success', ink: 'successText' },
  { fill: 'warn', ink: 'warnText' },
  { fill: 'energy', ink: 'energyText' },
  { fill: 'error', ink: 'errorText' },
  { fill: 'info', ink: 'infoText' },
] as const satisfies ReadonlyArray<{ fill: keyof ThemeColors; ink: keyof ThemeColors }>;

function ratio(fg: string, bg: string): number {
  return Number(contrastRatio(fg, bg).toFixed(2));
}

describe('contrast maths', () => {
  it('brackets the WCAG range', () => {
    expect(ratio('#FFFFFF', '#000000')).toBe(21);
    expect(ratio('#FFFFFF', '#FFFFFF')).toBe(1);
  });

  it('is symmetric', () => {
    expect(ratio(palette.jacaranda400, palette.ink950)).toBe(
      ratio(palette.ink950, palette.jacaranda400),
    );
  });

  it('accepts shorthand hex', () => {
    expect(ratio('#fff', '#000')).toBe(21);
  });
});

describe.each(themeNames)('%s theme — accessibility floor', (themeName) => {
  const t = themes[themeName];

  it.each(textRoles)('%s clears 4.5:1 on every surface it can land on', (role) => {
    for (const backdrop of textBackdrops) {
      expect(
        ratio(t[role], t[backdrop]),
        `${themeName}: ${role} on ${backdrop}`,
      ).toBeGreaterThanOrEqual(WCAG.bodyText);
    }
  });

  it.each(semanticFamilies)('$ink is legible as text on every surface', ({ ink }) => {
    for (const backdrop of textBackdrops) {
      expect(
        ratio(t[ink], t[backdrop]),
        `${themeName}: ${ink} on ${backdrop}`,
      ).toBeGreaterThanOrEqual(WCAG.bodyText);
    }
  });

  it.each(semanticFamilies)('$fill holds 3:1 as a fill or icon on a card', ({ fill }) => {
    expect(
      ratio(t[fill], t.surface),
      `${themeName}: ${fill} fill on surface`,
    ).toBeGreaterThanOrEqual(WCAG.nonText);
  });

  // The chip recipe: hue mixed into the surface at 10%, `-ink` text on top.
  it.each(semanticFamilies)('$ink stays legible on its own $fill chip', ({ fill, ink }) => {
    const chipBg = tintOver(t[fill], t.surface, chipTintPct);
    expect(
      Number(contrastRatio(t[ink], chipBg).toFixed(2)),
      `${themeName}: ${ink} on ${fill} chip`,
    ).toBeGreaterThanOrEqual(WCAG.bodyText);
  });

  it('keeps the focus ring visible against every surface', () => {
    for (const backdrop of textBackdrops) {
      expect(
        ratio(t.focus, t[backdrop]),
        `${themeName}: focus ring on ${backdrop}`,
      ).toBeGreaterThanOrEqual(WCAG.nonText);
    }
  });

  it('keeps label text legible on a filled accent button', () => {
    // The one solid-filled control in the system, so the one that needs this.
    expect(ratio(t.textInverse, t.accent)).toBeGreaterThanOrEqual(WCAG.bodyText);
  });

  it('separates primary from secondary text', () => {
    // If these converge the hierarchy stops working, regardless of the floor.
    expect(ratio(t.textHi, t.textLo)).toBeGreaterThanOrEqual(1.6);
  });
});

describe('wheel domain hues', () => {
  /**
   * Score is carried by spoke length and a printed numeral; hue is identity
   * only, and every spoke is labelled. That keeps the wheel clear of "colour as
   * the only visual means" (§4.7) without forcing ten hues to each hold 3:1 on
   * both an indigo and an ivory ground — which would flatten the ramp into mud.
   * What must hold is that no two domains share a colour.
   */
  it('gives all ten domains a distinct hue', () => {
    expect(new Set(wheelHues).size).toBe(wheelHues.length);
    expect(wheelHues).toHaveLength(10);
  });

  it('keeps neighbouring spokes visually separable', () => {
    for (let i = 1; i < wheelHues.length; i += 1) {
      const separation = contrastRatio(wheelHues[i]!, wheelHues[i - 1]!);
      expect(separation, `wheel ${i} vs ${i - 1}`).toBeGreaterThan(1.05);
    }
  });
});
