/**
 * Typography (§4.2). Three faces, each with a job:
 *   Display — Gambetta, used with restraint: H1/H2, greetings, wheel labels.
 *   Body/UI — General Sans, everything else.
 *   Data    — Space Grotesk, for scores, timers and table numerics.
 *
 * The single-file build inlines subsetted Latin faces; every target keeps the
 * fallback chain so a missing webfont degrades in shape, never in legibility.
 */

export const fontFamily = {
  display: "'Gambetta', 'Fraunces', 'Iowan Old Style', Georgia, serif",
  body: "'General Sans', 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif",
  data: "'Space Grotesk', 'JetBrains Mono', ui-monospace, 'SFMono-Regular', monospace",
} as const;

/** Scale from §4.2. Base is 16px and never smaller on mobile. */
export const fontSize = {
  xs: '0.75rem', // 12 — chips, table meta. Never body copy.
  sm: '0.875rem', // 14 — secondary text, labels
  base: '1rem', // 16 — body, the mobile floor
  lg: '1.125rem', // 18 — lead paragraphs
  xl: '1.375rem', // 22 — card titles
  '2xl': '1.75rem', // 28 — section headings
  '3xl': '2.25rem', // 36 — page headings
  '4xl': '3rem', // 48 — hero
} as const;

export const fontWeight = {
  regular: '400',
  medium: '500',
  semibold: '600',
} as const;

export const lineHeight = {
  heading: '1.15',
  body: '1.5',
  tight: '1.25',
} as const;

export const letterSpacing = {
  wordmark: '0.14em',
  heading: '-0.015em',
  normal: '0',
} as const;
