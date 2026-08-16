/**
 * Motion system (§4.4). Kowalski restraint as the default, Krehel polish on
 * every conditional render, Tompkins delight only where §4.4 licenses it.
 *
 * Laws encoded here rather than left to memory:
 *   - animate transform / opacity / filter only
 *   - enters scale from 0.96, never 0
 *   - exits are subtler and faster than enters
 *   - list stagger 30–50ms, capped at 8 items
 *   - prefers-reduced-motion is a global kill-switch
 */

export const duration = {
  instant: 120, // hover, toggles, tab underline
  fast: 200, // dropdowns, tooltips, list items
  base: 300, // modals, drawers, page elements
  slow: 600, // wheel morphs, chart draw-ins
  hero: 1200, // once-per-load orchestration only
} as const;

export const easing = {
  /** Default enter. */
  outExpo: 'cubic-bezier(0.16, 1, 0.3, 1)',
  /** Morphs — wheel snapshot transitions. */
  inOut: 'cubic-bezier(0.65, 0, 0.35, 1)',
  /** Exits: quicker, flatter. */
  outQuad: 'cubic-bezier(0.4, 0, 1, 1)',
} as const;

export const easingArray = {
  outExpo: [0.16, 1, 0.3, 1],
  inOut: [0.65, 0, 0.35, 1],
  outQuad: [0.4, 0, 1, 1],
} as const;

export const spring = {
  /** App-wide: no bounce. Speed reads as quality. */
  app: { type: 'spring', stiffness: 420, damping: 38, mass: 0.9 },
  /** Delight moments only: onboarding, wheel, session-complete, streaks. */
  delight: { type: 'spring', stiffness: 320, damping: 18, mass: 0.8 },
} as const;

export const stagger = {
  step: 0.04, // 40ms
  max: 8, // cap — beyond this the list feels slow, not alive
} as const;

/** Standard enter/exit pair. Exit is deliberately shorter than enter. */
export const transitions = {
  enter: { duration: duration.base / 1000, ease: easingArray.outExpo },
  exit: { duration: duration.fast / 1000, ease: easingArray.outQuad },
  morph: { duration: duration.slow / 1000, ease: easingArray.inOut },
} as const;

export const variants = {
  /** The house enter: fade + 8px rise + a breath of blur. */
  rise: {
    initial: { opacity: 0, y: 8, filter: 'blur(4px)' },
    animate: { opacity: 1, y: 0, filter: 'blur(0px)' },
    exit: { opacity: 0, y: 4, filter: 'blur(2px)' },
  },
  /** Scale-in from 0.96 — never from 0. */
  pop: {
    initial: { opacity: 0, scale: 0.96 },
    animate: { opacity: 1, scale: 1 },
    exit: { opacity: 0, scale: 0.98 },
  },
  fade: {
    initial: { opacity: 0 },
    animate: { opacity: 1 },
    exit: { opacity: 0 },
  },
} as const;

/**
 * Reduced motion collapses every variant to a crossfade and zeroes durations
 * that exist purely for delight. Callers pass the user's preference in so this
 * stays a pure function and remains testable outside a browser.
 */
export function motionFor(reduced: boolean) {
  return {
    variants: reduced ? variants.fade : variants.rise,
    transition: reduced ? { duration: 0.001 } : transitions.enter,
    morph: reduced ? { duration: 0.001 } : transitions.morph,
    stagger: reduced ? 0 : stagger.step,
  };
}
