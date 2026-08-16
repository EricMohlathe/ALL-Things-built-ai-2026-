/**
 * @cmw/tokens — the First Light design system (compendium §4).
 *
 * The single source of truth for colour, type, space, shape and motion across
 * all four targets. Law #1 from the prompt pack: components import from here,
 * never a raw hex.
 */

export {
  palette,
  themes,
  themeNames,
  dawnGradient,
  gradientStops,
  wheelHues,
  ratingColor,
  chipTintPct,
  chipBackground,
  type PaletteToken,
  type ThemeColors,
  type ThemeName,
} from './color.js';

export {
  contrastRatio,
  relativeLuminance,
  meetsContrast,
  parseHex,
  parseColor,
  compositeOver,
  tintOver,
  isOpaqueHex,
  WCAG,
  type Rgb,
  type Rgba,
} from './contrast.js';

export {
  fontFamily,
  fontSize,
  fontWeight,
  lineHeight,
  letterSpacing,
} from './typography.js';

export { space, radius, elevation, blur, touchTarget, breakpoint } from './space.js';

export {
  duration,
  easing,
  easingArray,
  spring,
  stagger,
  transitions,
  variants,
  motionFor,
} from './motion.js';

/** CSS custom-property name for a semantic colour role. */
export function cssVar(role: string): string {
  const kebab = role.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`);
  return `var(--cmw-${kebab})`;
}
