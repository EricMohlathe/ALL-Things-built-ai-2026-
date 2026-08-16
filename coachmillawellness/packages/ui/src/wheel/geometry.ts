/**
 * Wheel geometry — pure maths, no React.
 *
 * Separated from the component so the drag-to-score arithmetic and the petal
 * paths can be unit-tested, and so the same functions build both the on-screen
 * SVG and the standalone PNG export. A wheel that exports differently from how it
 * renders is the classic version of this bug.
 *
 * Angles run clockwise from twelve o'clock, which is how she reads the wheel on
 * paper — Career at the top, then round to the right.
 */

/**
 * Wheel layout, in viewBox units.
 *
 * Shared by the on-screen component and the PNG export so the two cannot drift —
 * an export that lays out differently from what she is looking at is the classic
 * version of this bug.
 *
 * The canvas is deliberately wider than the wheel needs. Rim labels are anchored
 * outward at `LABEL_RADIUS` and the longest of them ("Environment 7") runs about
 * 70 units past its anchor, so a canvas sized to the rim clips the left and right
 * labels — which is exactly what happened at 400.
 */
export const WHEEL_VIEWBOX = 500;
export const WHEEL_CENTRE = WHEEL_VIEWBOX / 2;
export const WHEEL_HUB_RADIUS = 54;
export const WHEEL_RIM_RADIUS = 150;
export const WHEEL_LABEL_RADIUS = WHEEL_RIM_RADIUS + 18;
export const WHEEL_GRID_STEPS = [2, 4, 6, 8, 10] as const;

export interface Spoke {
  /** Degrees, clockwise from top. */
  start: number;
  mid: number;
  end: number;
}

export interface Point {
  x: number;
  y: number;
}

/** Degrees clockwise from twelve o'clock → SVG coordinates. */
export function polar(cx: number, cy: number, radius: number, degrees: number): Point {
  const radians = ((degrees - 90) * Math.PI) / 180;
  return { x: cx + radius * Math.cos(radians), y: cy + radius * Math.sin(radians) };
}

/** Evenly divides the circle, with a hairline gap so petals read as separate. */
export function spokes(count: number, gapDegrees = 1.2): Spoke[] {
  if (count <= 0) return [];
  const step = 360 / count;
  return Array.from({ length: count }, (_, i) => {
    const start = i * step;
    return {
      start: start + gapDegrees / 2,
      mid: start + step / 2,
      end: start + step - gapDegrees / 2,
    };
  });
}

/**
 * Annular sector path — the petal. Drawn from an inner hub outward so the centre
 * stays open for the average score, and so a domain at 0 is still a visible
 * sliver rather than vanishing (a spoke she cannot see is a spoke she cannot
 * drag back up).
 */
export function petalPath(
  cx: number,
  cy: number,
  innerRadius: number,
  outerRadius: number,
  spoke: Spoke,
): string {
  const outerStart = polar(cx, cy, outerRadius, spoke.start);
  const outerEnd = polar(cx, cy, outerRadius, spoke.end);
  const innerEnd = polar(cx, cy, innerRadius, spoke.end);
  const innerStart = polar(cx, cy, innerRadius, spoke.start);
  const largeArc = spoke.end - spoke.start > 180 ? 1 : 0;

  return [
    `M ${round(outerStart.x)} ${round(outerStart.y)}`,
    `A ${round(outerRadius)} ${round(outerRadius)} 0 ${largeArc} 1 ${round(outerEnd.x)} ${round(outerEnd.y)}`,
    `L ${round(innerEnd.x)} ${round(innerEnd.y)}`,
    `A ${round(innerRadius)} ${round(innerRadius)} 0 ${largeArc} 0 ${round(innerStart.x)} ${round(innerStart.y)}`,
    'Z',
  ].join(' ');
}

/** Arc along a single radius — used for the target ghost ring. */
export function arcPath(cx: number, cy: number, radius: number, spoke: Spoke): string {
  const start = polar(cx, cy, radius, spoke.start);
  const end = polar(cx, cy, radius, spoke.end);
  return `M ${round(start.x)} ${round(start.y)} A ${round(radius)} ${round(radius)} 0 0 1 ${round(end.x)} ${round(end.y)}`;
}

/** Maps a 0–10 score onto a drawing radius. */
export function radiusForScore(
  score: number,
  innerRadius: number,
  outerRadius: number,
  max = 10,
): number {
  const clamped = Math.min(max, Math.max(0, score));
  return innerRadius + ((outerRadius - innerRadius) * clamped) / max;
}

/** The inverse — turns a drag distance back into a score. */
export function scoreForRadius(
  distance: number,
  innerRadius: number,
  outerRadius: number,
  max = 10,
): number {
  const span = outerRadius - innerRadius;
  if (span <= 0) return 0;
  const raw = ((distance - innerRadius) / span) * max;
  return Math.min(max, Math.max(0, Math.round(raw)));
}

/** Degrees clockwise from top for a point, normalised to 0–360. */
export function angleFor(cx: number, cy: number, point: Point): number {
  const degrees = (Math.atan2(point.y - cy, point.x - cx) * 180) / Math.PI + 90;
  return ((degrees % 360) + 360) % 360;
}

export function distanceFrom(cx: number, cy: number, point: Point): number {
  return Math.hypot(point.x - cx, point.y - cy);
}

/** Which domain a pointer is over. */
export function indexForAngle(angle: number, count: number): number {
  if (count <= 0) return -1;
  const step = 360 / count;
  return Math.min(count - 1, Math.floor((((angle % 360) + 360) % 360) / step));
}

/**
 * Label anchor just outside the rim. `anchor` flips across the vertical axis so
 * text reads outward on both sides instead of overlapping the wheel.
 */
export function labelPlacement(
  cx: number,
  cy: number,
  radius: number,
  spoke: Spoke,
): Point & { anchor: 'start' | 'middle' | 'end' } {
  const point = polar(cx, cy, radius, spoke.mid);
  const nearVertical = spoke.mid < 12 || spoke.mid > 348 || Math.abs(spoke.mid - 180) < 12;
  const anchor = nearVertical ? 'middle' : spoke.mid < 180 ? 'start' : 'end';
  return { ...point, anchor };
}

function round(value: number): number {
  // Two decimals keeps paths compact without visible drift — worth it when the
  // whole app has to fit in 1.2MB gzipped.
  return Math.round(value * 100) / 100;
}
