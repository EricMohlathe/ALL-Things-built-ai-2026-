/**
 * WCAG 2.1 relative-luminance and contrast maths.
 *
 * Lives in the token package on purpose: the accessibility floor (§4.7) is a
 * merge blocker, so the numbers that prove it have to ship with the colours
 * they judge rather than in a throwaway script.
 */

export interface Rgb {
  r: number;
  g: number;
  b: number;
}

export function parseHex(hex: string): Rgb {
  const raw = hex.trim().replace(/^#/, '');
  const full =
    raw.length === 3
      ? raw
          .split('')
          .map((c) => c + c)
          .join('')
      : raw;
  if (!/^[0-9a-fA-F]{6}$/.test(full)) {
    throw new Error(`Not an opaque hex colour: "${hex}"`);
  }
  return {
    r: Number.parseInt(full.slice(0, 2), 16),
    g: Number.parseInt(full.slice(2, 4), 16),
    b: Number.parseInt(full.slice(4, 6), 16),
  };
}

export function isOpaqueHex(value: string): boolean {
  return /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(value.trim());
}

export interface Rgba extends Rgb {
  a: number;
}

/** Parses `#rgb`, `#rrggbb`, `rgb(...)` and `rgba(...)`. */
export function parseColor(value: string): Rgba {
  const input = value.trim();
  const fn = /^rgba?\(\s*([^)]+)\)$/i.exec(input);
  if (fn) {
    const parts = fn[1]!.split(/[,/\s]+/).filter(Boolean);
    const [r, g, b, a] = parts;
    if (r === undefined || g === undefined || b === undefined) {
      throw new Error(`Malformed colour function: "${value}"`);
    }
    return {
      r: Number.parseFloat(r),
      g: Number.parseFloat(g),
      b: Number.parseFloat(b),
      a: a === undefined ? 1 : Number.parseFloat(a),
    };
  }
  return { ...parseHex(input), a: 1 };
}

/**
 * Composites a translucent colour over an opaque backdrop, which is what the
 * eye actually receives. Glass panels and chip tints are only honest to test
 * once flattened this way.
 */
export function compositeOver(foreground: string, backdrop: string): Rgb {
  const fg = parseColor(foreground);
  const bd = parseColor(backdrop);
  const a = Math.min(Math.max(fg.a, 0), 1);
  return {
    r: fg.r * a + bd.r * (1 - a),
    g: fg.g * a + bd.g * (1 - a),
    b: fg.b * a + bd.b * (1 - a),
  };
}

/** The chip recipe: `percent`% of a hue laid over a surface. Mirrors `color-mix()`. */
export function tintOver(hue: string, backdrop: string, percent: number): Rgb {
  const { r, g, b } = parseColor(hue);
  return compositeOver(`rgba(${r}, ${g}, ${b}, ${percent / 100})`, backdrop);
}

function channelLuminance(value8Bit: number): number {
  const c = value8Bit / 255;
  return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}

export function relativeLuminance(color: string | Rgb): number {
  const { r, g, b } = typeof color === 'string' ? parseHex(color) : color;
  return (
    0.2126 * channelLuminance(r) + 0.7152 * channelLuminance(g) + 0.0722 * channelLuminance(b)
  );
}

/** Contrast ratio, 1–21. Order of arguments does not matter. */
export function contrastRatio(a: string | Rgb, b: string | Rgb): number {
  const la = relativeLuminance(a);
  const lb = relativeLuminance(b);
  const lighter = Math.max(la, lb);
  const darker = Math.min(la, lb);
  return (lighter + 0.05) / (darker + 0.05);
}

export const WCAG = {
  /** Body text and anything below 18.66px/24px bold. */
  bodyText: 4.5,
  /** Large text — ≥24px, or ≥18.66px bold. */
  largeText: 3,
  /** Icons, borders that carry meaning, and component boundaries. */
  nonText: 3,
} as const;

export function meetsContrast(
  foreground: string,
  background: string,
  threshold: number = WCAG.bodyText,
): boolean {
  return contrastRatio(foreground, background) >= threshold;
}
