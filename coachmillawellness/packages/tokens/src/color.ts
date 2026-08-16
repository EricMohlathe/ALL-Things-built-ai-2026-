/**
 * FIRST LIGHT — colour tokens (compendium §4.2).
 *
 * Two layers, and components may only ever touch the second one:
 *   `palette` — the raw named ramp. Never referenced from a component.
 *   `themes`  — semantic roles (bg / surface / textHi / accent / success …).
 *               Identical key set in both themes, so a component written
 *               against a role is automatically correct in Dawn and Morning.
 *
 * Morning is designed alongside Dawn, not inverted from it, and every
 * text-bearing role is contrast-verified in `__tests__/contrast.test.ts`.
 */

export const palette = {
  // Indigo-night shell — never pure black.
  ink950: '#0E0F1A',
  ink900: '#161827',
  ink800: '#1F2233',

  // Warm ivory shell for Morning.
  ivory50: '#F7F5F0',
  ivory100: '#EFECE4',
  white: '#FFFFFF',
  night900: '#1A1C2B',

  // Jacaranda violet — the identity accent. Pretoria's signature.
  jacaranda400: '#9A7BFF',
  jacaranda600: '#6E4FE0',

  // Dawn gradient family.
  amber400: '#F5A524',
  amber600: '#C4820E',
  // DECISION: deepened one further step past the compendium's suggestion — the
  // lighter amber missed 4.5:1 on the ivory raised surface.
  amber700: '#8A5A09',
  coral400: '#F87A6D',
  coral600: '#D9503F',
  coral700: '#B23A2E',

  // Health-positive / "Strong" rating.
  sage400: '#5FBF9F',
  sage600: '#2F8F6F',
  sage700: '#26775C',

  textHi: '#F4F2ED',
  textLo: '#9DA0B4',
  slate600: '#55596E',

  error400: '#F0564F',
  error600: '#D8382D',
  error700: '#B3271E',
  info400: '#6FA8F5',
  // DECISION: the compendium's lighter Morning blue landed at 4.32:1 against a
  // tinted chip background — under the floor. Deepened until it clears 4.5:1.
  info700: '#1A5FB4',
} as const;

export type PaletteToken = keyof typeof palette;

/**
 * Semantic roles. `*Text` variants exist because a hue that is legible as a
 * 3:1 fill is not always legible as 4.5:1 body text — most visibly in Morning,
 * where sage-600 carries fills at 3.98:1 but text needs sage-700 at 5.42:1.
 * DECISION: split the role rather than compromise either the palette or §4.7.
 */
export interface ThemeColors {
  bg: string;
  surface: string;
  surfaceRaised: string;
  glass: string;
  glassBorder: string;
  border: string;
  borderStrong: string;
  textHi: string;
  textLo: string;
  textInverse: string;
  accent: string;
  accentText: string;
  /**
   * The soft accent background behind active nav items, badges and accent chips.
   *
   * Opaque on purpose. It was a translucent `rgba()` until an axe run caught it
   * at 4.29:1 on the glass rail: a translucent tint composites over whatever is
   * behind it, and on the rail that is glass over `bg`, not `surface` — lighter
   * than anything a unit test comparing against `surface` would check. Baking in
   * the composited value makes the contrast identical wherever it lands.
   */
  accentQuiet: string;
  success: string;
  successText: string;
  warn: string;
  warnText: string;
  energy: string;
  energyText: string;
  error: string;
  errorText: string;
  info: string;
  infoText: string;
  focus: string;
  shadow: string;
}

export const themes: Record<'dawn' | 'morning', ThemeColors> = {
  dawn: {
    bg: palette.ink950,
    surface: palette.ink900,
    surfaceRaised: palette.ink800,
    glass: 'rgba(255, 255, 255, 0.06)',
    glassBorder: 'rgba(255, 255, 255, 0.08)',
    border: 'rgba(255, 255, 255, 0.10)',
    borderStrong: 'rgba(255, 255, 255, 0.18)',
    textHi: palette.textHi,
    textLo: palette.textLo,
    textInverse: palette.ink950,
    accent: palette.jacaranda400,
    accentText: palette.jacaranda400,
    // Opaque, not translucent — see the note on `accentQuiet` in ThemeColors.
    accentQuiet: '#282645',
    success: palette.sage400,
    successText: palette.sage400,
    warn: palette.amber400,
    warnText: palette.amber400,
    energy: palette.coral400,
    energyText: palette.coral400,
    error: palette.error400,
    errorText: palette.error400,
    info: palette.info400,
    infoText: palette.info400,
    focus: palette.jacaranda400,
    shadow: 'rgba(0, 0, 0, 0.45)',
  },
  morning: {
    bg: palette.ivory50,
    surface: palette.white,
    surfaceRaised: palette.ivory100,
    glass: 'rgba(255, 255, 255, 0.65)',
    glassBorder: 'rgba(26, 28, 43, 0.08)',
    border: 'rgba(26, 28, 43, 0.12)',
    borderStrong: 'rgba(26, 28, 43, 0.22)',
    textHi: palette.night900,
    textLo: palette.slate600,
    textInverse: palette.white,
    accent: palette.jacaranda600,
    accentText: palette.jacaranda600,
    accentQuiet: '#F1EDFC',
    success: palette.sage600,
    successText: palette.sage700,
    warn: palette.amber600,
    warnText: palette.amber700,
    energy: palette.coral600,
    energyText: palette.coral700,
    error: palette.error600,
    errorText: palette.error700,
    info: palette.info700,
    infoText: palette.info700,
    focus: palette.jacaranda600,
    shadow: 'rgba(26, 28, 43, 0.12)',
  },
};

export type ThemeName = keyof typeof themes;
export const themeNames = Object.keys(themes) as ThemeName[];

/**
 * The dawn gradient. §4.2 caps it at ≤10% of any screen — hero, streaks and
 * progress only. `gradientStops` is exposed separately so SVG (which cannot
 * consume a CSS gradient string) renders the identical ramp.
 */
export const dawnGradient = 'linear-gradient(135deg, #F5A524 0%, #F87A6D 50%, #9A7BFF 100%)';

export const gradientStops = [
  { offset: 0, color: palette.amber400 },
  { offset: 0.5, color: palette.coral400 },
  { offset: 1, color: palette.jacaranda400 },
] as const;

/** Wheel-of-Life domain hues, walked around the dawn ramp so the ring reads as one object. */
export const wheelHues = [
  '#F5A524',
  '#F79240',
  '#F87A6D',
  '#EE6F86',
  '#D96FA6',
  '#B873C8',
  '#9A7BFF',
  '#7C93F0',
  '#5FB0D8',
  '#5FBF9F',
] as const;

/**
 * Chips and badges are drawn as a soft tint of their own hue plus `-ink` text,
 * never as a solid fill — a solid sage or amber cannot hold 4.5:1 against
 * either white or ivory. 10% is the ceiling that keeps every semantic hue
 * legible in both themes; `__tests__/contrast.test.ts` proves it per role.
 *
 * The tint mixes with `surface` opaquely rather than sitting on the backdrop as
 * a translucent layer, so a chip reads identically whether it lands on a card,
 * a raised row or a glass panel — one measurable value instead of a different
 * composite everywhere it appears.
 */
export const chipTintPct = 10;

export function chipBackground(role: 'accent' | 'success' | 'warn' | 'energy' | 'error' | 'info'): string {
  return `color-mix(in srgb, var(--cmw-${role}) ${chipTintPct}%, var(--cmw-surface))`;
}

/** Adherence ratings (Appendix B) always pair a hue with an icon/label — never colour alone. */
export const ratingColor = {
  Strong: 'success',
  Adequate: 'info',
  Weak: 'warn',
  Met: 'accent',
  'N/A': 'textLo',
} as const satisfies Record<string, keyof ThemeColors>;
