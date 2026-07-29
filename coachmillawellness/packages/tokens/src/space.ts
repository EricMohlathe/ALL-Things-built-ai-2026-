/** Space, shape and elevation (§4.2). 4-pt scale, no ad-hoc values. */

export const space = {
  '0': '0',
  '1': '0.25rem', // 4
  '2': '0.5rem', // 8
  '3': '0.75rem', // 12
  '4': '1rem', // 16
  '6': '1.5rem', // 24
  '8': '2rem', // 32
  '12': '3rem', // 48
  '16': '4rem', // 64
} as const;

export const radius = {
  sm: '8px',
  md: '14px',
  lg: '20px',
  pill: '999px',
} as const;

/**
 * Elevation is theme-dependent by design (§4.2): Morning layers soft shadows,
 * Dawn steps the surface and adds a 1px inner highlight instead — shadows are
 * close to invisible on an indigo-night shell.
 */
export const elevation = {
  dawn: {
    flat: 'none',
    raised: 'inset 0 1px 0 0 rgba(255, 255, 255, 0.08)',
    overlay: '0 16px 48px -12px rgba(0, 0, 0, 0.65), inset 0 1px 0 0 rgba(255, 255, 255, 0.08)',
  },
  morning: {
    flat: 'none',
    raised: '0 1px 2px 0 rgba(26, 28, 43, 0.06), 0 4px 12px -4px rgba(26, 28, 43, 0.08)',
    overlay: '0 16px 48px -12px rgba(26, 28, 43, 0.18)',
  },
} as const;

export const blur = {
  glass: '16px',
} as const;

/** Minimum interactive target (§4.7). Enforced on every control. */
export const touchTarget = '44px';

/** Breakpoints. Mobile is the design origin, not the fallback. */
export const breakpoint = {
  sm: '480px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
} as const;
