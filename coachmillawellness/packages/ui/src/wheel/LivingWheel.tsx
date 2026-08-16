/**
 * THE LIVING WHEEL (§4.3) — the signature element, and the one place the design
 * system spends all of its boldness.
 *
 * A Wheel of Life that breathes, morphs across time, and is worth screenshotting
 * into a client report. Everything else in the app stays quiet so this can be
 * loud.
 *
 * Behaviour that matters:
 *  - Score is spoke length; target is a ghost ring. Colour is identity only, and
 *    every spoke carries its name and numeral, so nothing is read from hue alone.
 *  - Drag a spoke to score it during a session. Keyboard works too — a wheel you
 *    can only operate with a pointer fails §4.7, and she scores these live.
 *  - Snapshot changes tween over 600ms with ease-out-expo, and improved domains
 *    emit a brief sage particle drift.
 *  - Reduced motion removes the breathing and the tween, and crossfades instead.
 *
 * This is the 2D SVG build (§6): identical data and interactions to the 3D tier,
 * no Three.js, so the single file stays lean.
 */

import { duration, easingArray, wheelHues } from '@cmw/tokens';
import { useReducedMotion } from 'motion/react';
import {
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
} from 'react';

import {
  WHEEL_CENTRE,
  WHEEL_GRID_STEPS,
  WHEEL_HUB_RADIUS,
  WHEEL_LABEL_RADIUS,
  WHEEL_RIM_RADIUS,
  WHEEL_VIEWBOX,
  angleFor,
  arcPath,
  distanceFrom,
  indexForAngle,
  labelPlacement,
  petalPath,
  radiusForScore,
  scoreForRadius,
  spokes,
  type Spoke,
} from './geometry.js';

export interface WheelDomainValue {
  domain: string;
  score: number;
  target: number;
}

export interface LivingWheelProps {
  domains: WheelDomainValue[];
  /** Pixel size of the square viewport. */
  size?: number;
  /** Allows drag and keyboard scoring. */
  editable?: boolean;
  onScoreChange?: (domain: string, score: number) => void;
  /** Domains that improved since the previous snapshot — these emit particles. */
  improved?: string[];
  showLabels?: boolean;
  showTargets?: boolean;
  /** Changes whenever the underlying snapshot changes, so a morph can be keyed. */
  snapshotKey?: string;
  className?: string;
  /** Accessible summary. Defaults to a readout of every domain. */
  ariaLabel?: string;
}

// Layout comes from geometry.ts so the PNG export renders identically.
const VIEWBOX = WHEEL_VIEWBOX;
const CENTRE = WHEEL_CENTRE;
const HUB_RADIUS = WHEEL_HUB_RADIUS;
const RIM_RADIUS = WHEEL_RIM_RADIUS;
const LABEL_RADIUS = WHEEL_LABEL_RADIUS;
const GRID_STEPS = WHEEL_GRID_STEPS;

/**
 * Tweens scores toward their target over `dur`, easing with ease-out-expo.
 *
 * Hand-rolled on requestAnimationFrame rather than handed to a spring library
 * because the thing being animated is the *number* behind ten SVG path strings —
 * paths cannot be interpolated by CSS, and recomputing them per frame from the
 * geometry helpers keeps the morph exact and cheap.
 */
function useTweenedScores(
  targets: WheelDomainValue[],
  reduced: boolean,
  dur: number,
): WheelDomainValue[] {
  const [values, setValues] = useState<WheelDomainValue[]>(targets);
  const fromRef = useRef<WheelDomainValue[]>(targets);
  const frameRef = useRef<number | null>(null);

  // A signature over the values, so a tween starts when the data changes rather
  // than on every parent render.
  const signature = targets.map((d) => `${d.domain}:${d.score}:${d.target}`).join('|');

  useEffect(() => {
    if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);

    const from = fromRef.current;
    const to = targets;

    if (reduced || from.length !== to.length) {
      fromRef.current = to;
      setValues(to);
      return;
    }

    const start = performance.now();
    const [c1, c2, c3, c4] = easingArray.outExpo;

    const step = (stamp: number): void => {
      const t = Math.min(1, (stamp - start) / dur);
      const eased = cubicBezier(t, c1, c2, c3, c4);

      setValues(
        to.map((target, i) => {
          const previous = from[i];
          // A domain that did not exist before animates from its own value, so
          // adding one does not read as the wheel collapsing.
          const base = previous?.domain === target.domain ? previous : target;
          return {
            domain: target.domain,
            score: base.score + (target.score - base.score) * eased,
            target: base.target + (target.target - base.target) * eased,
          };
        }),
      );

      if (t < 1) frameRef.current = requestAnimationFrame(step);
      else {
        fromRef.current = to;
        frameRef.current = null;
      }
    };

    frameRef.current = requestAnimationFrame(step);
    return () => {
      if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signature, reduced, dur]);

  return values;
}

/** Newton-iterated cubic-bezier easing — enough precision for a 600ms tween. */
function cubicBezier(t: number, x1: number, y1: number, x2: number, y2: number): number {
  if (t <= 0) return 0;
  if (t >= 1) return 1;

  const bezier = (a: number, b: number, u: number): number => {
    const v = 1 - u;
    return 3 * v * v * u * a + 3 * v * u * u * b + u * u * u;
  };

  let low = 0;
  let high = 1;
  let guess = t;
  for (let i = 0; i < 18; i += 1) {
    const x = bezier(x1, x2, guess);
    if (Math.abs(x - t) < 0.0005) break;
    if (x < t) low = guess;
    else high = guess;
    guess = (low + high) / 2;
  }
  return bezier(y1, y2, guess);
}

export function LivingWheel({
  domains,
  size = 400,
  editable = false,
  onScoreChange,
  improved = [],
  showLabels = true,
  showTargets = true,
  snapshotKey,
  className,
  ariaLabel,
}: LivingWheelProps) {
  const reduced = useReducedMotion() ?? false;
  const gradientId = useId().replace(/:/g, '');
  const svgRef = useRef<SVGSVGElement>(null);
  const [dragging, setDragging] = useState<number | null>(null);
  const [focused, setFocused] = useState<number | null>(null);

  const shown = useTweenedScores(domains, reduced, duration.slow);
  const layout = useMemo(() => spokes(domains.length), [domains.length]);

  const average =
    domains.length === 0
      ? null
      : domains.reduce((sum, d) => sum + d.score, 0) / domains.length;

  /** Turns a pointer position into a score for the domain under it. */
  const scoreFromPointer = useCallback(
    (event: ReactPointerEvent<SVGSVGElement>, forcedIndex: number | null) => {
      const svg = svgRef.current;
      if (!svg || !onScoreChange) return;

      const rect = svg.getBoundingClientRect();
      // Map client pixels into the fixed viewBox so scoring behaves identically
      // at any rendered size.
      const scale = VIEWBOX / rect.width;
      const point = {
        x: (event.clientX - rect.left) * scale,
        y: (event.clientY - rect.top) * scale,
      };

      const index =
        forcedIndex ?? indexForAngle(angleFor(CENTRE, CENTRE, point), domains.length);
      const domain = domains[index];
      if (!domain) return;

      const score = scoreForRadius(
        distanceFrom(CENTRE, CENTRE, point),
        HUB_RADIUS,
        RIM_RADIUS,
      );
      if (score !== domain.score) onScoreChange(domain.domain, score);
      return index;
    },
    [domains, onScoreChange],
  );

  const handlePointerDown = (event: ReactPointerEvent<SVGSVGElement>): void => {
    if (!editable) return;
    const svg = svgRef.current;
    const rect = svg?.getBoundingClientRect();
    if (!rect) return;

    const scale = VIEWBOX / rect.width;
    const point = {
      x: (event.clientX - rect.left) * scale,
      y: (event.clientY - rect.top) * scale,
    };
    // The hub is not a scoring surface — it shows the average.
    if (distanceFrom(CENTRE, CENTRE, point) < HUB_RADIUS * 0.8) return;

    const index = indexForAngle(angleFor(CENTRE, CENTRE, point), domains.length);
    setDragging(index);
    setFocused(index);
    svg?.setPointerCapture(event.pointerId);
    scoreFromPointer(event, index);
  };

  const handlePointerMove = (event: ReactPointerEvent<SVGSVGElement>): void => {
    if (!editable || dragging === null) return;
    // Locked to the spoke the drag started on, so sweeping outward cannot
    // accidentally rescore a neighbour.
    scoreFromPointer(event, dragging);
  };

  const endDrag = (event: ReactPointerEvent<SVGSVGElement>): void => {
    if (dragging === null) return;
    setDragging(null);
    svgRef.current?.releasePointerCapture?.(event.pointerId);
  };

  const nudge = (index: number, delta: number): void => {
    const domain = domains[index];
    if (!domain || !onScoreChange) return;
    const next = Math.min(10, Math.max(0, domain.score + delta));
    if (next !== domain.score) onScoreChange(domain.domain, next);
  };

  const readout =
    ariaLabel ??
    `Wheel of Life. ${domains.map((d) => `${d.domain} ${d.score} out of 10`).join('. ')}`;

  return (
    <div className={className}>
      <svg
        ref={svgRef}
        viewBox={`0 0 ${VIEWBOX} ${VIEWBOX}`}
        width={size}
        height={size}
        role="img"
        aria-label={readout}
        className={cnWheel(editable, dragging !== null)}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        style={{ maxWidth: '100%', height: 'auto', touchAction: 'none' }}
      >
        <defs>
          <radialGradient id={`${gradientId}-hub`} cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="var(--cmw-accent)" stopOpacity="0.22" />
            <stop offset="100%" stopColor="var(--cmw-accent)" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/*
          The breathing group. ±2% over 4s, paused by the global reduced-motion
          kill-switch in tokens.css, which lands it back at scale 1.
        */}
        <g
          className={reduced ? undefined : 'cmw-wheel-breathe'}
          style={{ transformOrigin: `${CENTRE}px ${CENTRE}px` }}
        >
          {/* Grid rings — the 0–10 reference she reads scores against. */}
          {GRID_STEPS.map((step) => (
            <circle
              key={step}
              cx={CENTRE}
              cy={CENTRE}
              r={radiusForScore(step, HUB_RADIUS, RIM_RADIUS)}
              fill="none"
              stroke="var(--cmw-border)"
              strokeWidth={step === 10 ? 1.5 : 1}
            />
          ))}

          {shown.map((value, index) => {
            const spoke = layout[index];
            if (!spoke) return null;
            const hue = wheelHues[index % wheelHues.length]!;
            const outer = radiusForScore(value.score, HUB_RADIUS, RIM_RADIUS);
            const isActive = dragging === index || focused === index;

            return (
              <g key={value.domain}>
                <path
                  d={petalPath(CENTRE, CENTRE, HUB_RADIUS, outer, spoke)}
                  fill={hue}
                  fillOpacity={isActive ? 0.95 : 0.8}
                  stroke={hue}
                  strokeWidth={isActive ? 2 : 1}
                />
                {showTargets ? (
                  <path
                    d={arcPath(
                      CENTRE,
                      CENTRE,
                      radiusForScore(value.target, HUB_RADIUS, RIM_RADIUS),
                      spoke,
                    )}
                    fill="none"
                    stroke="var(--cmw-text-lo)"
                    strokeWidth={2}
                    strokeDasharray="4 4"
                    strokeLinecap="round"
                    opacity={0.8}
                  />
                ) : null}
              </g>
            );
          })}

          {/* Sage particle drift on improved domains (§4.3). */}
          {!reduced
            ? improved.map((domain) => {
                const index = domains.findIndex((d) => d.domain === domain);
                const spoke = layout[index];
                const value = domains[index];
                if (!spoke || !value) return null;
                return (
                  <ImprovementParticles
                    key={`${snapshotKey ?? ''}-${domain}`}
                    spoke={spoke}
                    score={value.score}
                  />
                );
              })
            : null}

          {/* Hub — average score, and the reason the centre stays open. */}
          <circle cx={CENTRE} cy={CENTRE} r={HUB_RADIUS} fill={`url(#${gradientId}-hub)`} />
          <circle
            cx={CENTRE}
            cy={CENTRE}
            r={HUB_RADIUS}
            fill="var(--cmw-surface)"
            fillOpacity={0.72}
            stroke="var(--cmw-border)"
          />
          <text
            x={CENTRE}
            y={CENTRE - 2}
            textAnchor="middle"
            className="cmw-numeric"
            fontSize={30}
            fontWeight={600}
            fill="var(--cmw-text-hi)"
          >
            {average === null ? '—' : average.toFixed(1)}
          </text>
          <text
            x={CENTRE}
            y={CENTRE + 18}
            textAnchor="middle"
            fontSize={11}
            fill="var(--cmw-text-lo)"
            letterSpacing="0.1em"
          >
            AVERAGE
          </text>
        </g>

        {/* Labels sit outside the breathing group so text never scales. */}
        {showLabels
          ? shown.map((value, index) => {
              const spoke = layout[index];
              if (!spoke) return null;
              const place = labelPlacement(CENTRE, CENTRE, LABEL_RADIUS, spoke);
              const domain = domains[index];
              return (
                <text
                  key={value.domain}
                  x={place.x}
                  y={place.y}
                  textAnchor={place.anchor}
                  dominantBaseline="middle"
                  fontSize={11}
                  fill={focused === index ? 'var(--cmw-text-hi)' : 'var(--cmw-text-lo)'}
                >
                  {shortLabel(value.domain)}
                  <tspan className="cmw-numeric" fill="var(--cmw-text-hi)" fontWeight={600}>
                    {'  '}
                    {Math.round(domain?.score ?? value.score)}
                  </tspan>
                </text>
              );
            })
          : null}
      </svg>

      {/*
        Keyboard scoring. Presented as a real control list rather than hidden
        affordances on the SVG: it gives every spoke a focusable target, a live
        value, and arrow-key adjustment, which is what makes the wheel operable
        without a pointer.
      */}
      {editable ? (
        <div className="mt-4 grid grid-cols-1 gap-1.5 sm:grid-cols-2">
          {domains.map((domain, index) => (
            <div
              key={domain.domain}
              className="flex items-center gap-2 rounded-md px-2 py-1.5 transition-colors duration-150 hover:bg-raised"
            >
              <span
                aria-hidden="true"
                className="size-2.5 shrink-0 rounded-pill"
                style={{ backgroundColor: wheelHues[index % wheelHues.length] }}
              />
              <span className="flex-1 truncate text-sm text-hi">{domain.domain}</span>
              <input
                type="range"
                min={0}
                max={10}
                step={1}
                value={domain.score}
                aria-label={`${domain.domain} score, target ${domain.target}`}
                onFocus={() => setFocused(index)}
                onBlur={() => setFocused((current) => (current === index ? null : current))}
                onKeyDown={(event) => {
                  if (event.key === 'ArrowUp' || event.key === 'ArrowRight') {
                    event.preventDefault();
                    nudge(index, 1);
                  }
                  if (event.key === 'ArrowDown' || event.key === 'ArrowLeft') {
                    event.preventDefault();
                    nudge(index, -1);
                  }
                }}
                onChange={(event) => onScoreChange?.(domain.domain, Number(event.target.value))}
                className="h-11 w-28 accent-[var(--cmw-accent)]"
              />
              <span className="cmw-numeric w-12 shrink-0 text-right text-sm text-hi">
                {domain.score}
                <span className="text-lo">/{domain.target}</span>
              </span>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function ImprovementParticles({ spoke, score }: { spoke: Spoke; score: number }) {
  const base = radiusForScore(score, HUB_RADIUS, RIM_RADIUS);
  return (
    <g className="cmw-wheel-particles" style={{ transformOrigin: `${CENTRE}px ${CENTRE}px` }}>
      {[0, 1, 2].map((i) => {
        const angle = spoke.start + ((spoke.end - spoke.start) * (i + 1)) / 4;
        const point = polarPoint(base + 6 + i * 5, angle);
        return (
          <circle
            key={i}
            cx={point.x}
            cy={point.y}
            r={2.5 - i * 0.4}
            fill="var(--cmw-success)"
            style={{ animationDelay: `${i * 90}ms` }}
          />
        );
      })}
    </g>
  );
}

function polarPoint(radius: number, degrees: number): { x: number; y: number } {
  const radians = ((degrees - 90) * Math.PI) / 180;
  return { x: CENTRE + radius * Math.cos(radians), y: CENTRE + radius * Math.sin(radians) };
}

/** Keeps rim labels from colliding — the full name still lives in the aria text. */
function shortLabel(domain: string): string {
  const shortened: Record<string, string> = {
    'Romance/Partner': 'Romance',
    'Personal Growth': 'Growth',
    'Fun & Recreation': 'Fun',
    'Physical Environment': 'Environment',
    'Friends & Community': 'Friends',
    'Spirituality/Purpose': 'Purpose',
  };
  return shortened[domain] ?? domain;
}

function cnWheel(editable: boolean, dragging: boolean): string {
  return [
    'select-none',
    editable ? (dragging ? 'cursor-grabbing' : 'cursor-grab') : '',
  ]
    .filter(Boolean)
    .join(' ');
}
