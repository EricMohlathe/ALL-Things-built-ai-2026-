/**
 * Charts.
 *
 * Hand-rolled SVG rather than a charting library. Two reasons, both about the
 * product rather than about taste: Build 1 has a 1.2MB gzipped ceiling and a
 * general-purpose chart library is a large fraction of it, and none of these
 * shapes are generic — a wheel sparkline and a pillar-coherence matrix are not
 * in anybody's chart catalogue.
 *
 * House rules, applied to every chart here (§2 M5): a legend or inline labels,
 * a tooltip via `title`, colourblind-safe hues, and never colour as the only
 * carrier of meaning — every value is also printed or labelled.
 */

import { wheelHues } from '@cmw/tokens';
import type { ReactNode } from 'react';

import { petalPath, radiusForScore, spokes } from '../wheel/geometry.js';
import { Numeric, cn } from '../primitives/index.js';

// ── Mini wheel ────────────────────────────────────────────────────────────

/** The wheel at card size (§2 M1) — shape only, no labels. */
export function MiniWheel({
  scores,
  size = 44,
  title,
}: {
  scores: number[];
  size?: number;
  title?: string;
}) {
  const box = 100;
  const centre = box / 2;
  const hub = 10;
  const rim = 44;
  const layout = spokes(scores.length, 2);

  return (
    <svg
      viewBox={`0 0 ${box} ${box}`}
      width={size}
      height={size}
      aria-hidden="true"
      className="shrink-0"
    >
      {title ? <title>{title}</title> : null}
      <circle cx={centre} cy={centre} r={rim} fill="none" stroke="var(--cmw-border)" />
      {scores.map((score, index) => {
        const spoke = layout[index];
        if (!spoke) return null;
        return (
          <path
            key={index}
            d={petalPath(centre, centre, hub, radiusForScore(score, hub, rim), spoke)}
            fill={wheelHues[index % wheelHues.length]}
            fillOpacity={0.85}
          />
        );
      })}
    </svg>
  );
}

// ── Trend line ────────────────────────────────────────────────────────────

export interface TrendPoint {
  label: string;
  value: number;
}

/**
 * Score trend over time. Draws a dot per point because a two-point "trend" is a
 * line with no information in its middle, and the dots stop it reading as more
 * data than there is.
 */
export function TrendLine({
  points,
  max = 10,
  height = 90,
  tone = 'accent',
  suffix = '',
}: {
  points: TrendPoint[];
  max?: number;
  height?: number;
  tone?: 'accent' | 'success';
  suffix?: string;
}) {
  if (points.length === 0) {
    return <p className="py-6 text-center text-sm text-lo">Nothing charted yet.</p>;
  }

  const width = 320;
  const padX = 6;
  const padY = 10;
  const usableW = width - padX * 2;
  const usableH = height - padY * 2;
  const colour = `var(--cmw-${tone})`;

  const x = (i: number): number =>
    points.length === 1 ? width / 2 : padX + (usableW * i) / (points.length - 1);
  const y = (value: number): number =>
    padY + usableH * (1 - Math.min(max, Math.max(0, value)) / max);

  const path = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${x(i)} ${y(p.value)}`).join(' ');

  return (
    <div>
      <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} role="img">
        <title>
          {points.map((p) => `${p.label}: ${p.value}${suffix}`).join(', ')}
        </title>
        {[0, 0.5, 1].map((fraction) => (
          <line
            key={fraction}
            x1={padX}
            x2={width - padX}
            y1={padY + usableH * fraction}
            y2={padY + usableH * fraction}
            stroke="var(--cmw-border)"
            strokeWidth={1}
          />
        ))}
        <path d={path} fill="none" stroke={colour} strokeWidth={2} strokeLinecap="round" />
        {points.map((p, i) => (
          <circle key={p.label} cx={x(i)} cy={y(p.value)} r={3.5} fill={colour}>
            <title>{`${p.label}: ${p.value}${suffix}`}</title>
          </circle>
        ))}
      </svg>
      <div className="mt-1 flex justify-between text-xs text-lo">
        <span>{points[0]!.label}</span>
        {points.length > 1 ? <span>{points[points.length - 1]!.label}</span> : null}
      </div>
    </div>
  );
}

// ── Consistency heatmap ───────────────────────────────────────────────────

/** GitHub-style publish consistency (§2 M4). Weeks as columns, days as rows. */
export function ConsistencyHeatmap({
  days,
}: {
  days: ReadonlyArray<{ date: string; count: number; intensity: number }>;
}) {
  const weeks: Array<Array<{ date: string; count: number; intensity: number }>> = [];
  for (let i = 0; i < days.length; i += 7) weeks.push(days.slice(i, i + 7));

  return (
    <div>
      <div className="cmw-scroll-x flex gap-1 pb-1">
        {weeks.map((week, index) => (
          <div key={index} className="flex flex-col gap-1">
            {week.map((day) => (
              <span
                key={day.date}
                title={`${day.date}: ${day.count} post${day.count === 1 ? '' : 's'}`}
                className="size-3 rounded-[3px] border border-edge"
                style={{
                  backgroundColor:
                    day.count === 0
                      ? 'transparent'
                      : `color-mix(in srgb, var(--cmw-success) ${Math.round(
                          25 + day.intensity * 75,
                        )}%, var(--cmw-surface))`,
                }}
              />
            ))}
          </div>
        ))}
      </div>
      {/* A legend, because intensity alone is not a quantity. */}
      <div className="mt-2 flex items-center gap-2 text-xs text-lo">
        <span>Quieter</span>
        {[0, 0.35, 0.7, 1].map((step) => (
          <span
            key={step}
            className="size-3 rounded-[3px] border border-edge"
            style={{
              backgroundColor:
                step === 0
                  ? 'transparent'
                  : `color-mix(in srgb, var(--cmw-success) ${Math.round(25 + step * 75)}%, var(--cmw-surface))`,
            }}
          />
        ))}
        <span>Busier</span>
      </div>
    </div>
  );
}

// ── Coherence matrix ──────────────────────────────────────────────────────

/**
 * Pillars × time windows (§2 M4). Cell intensity shows volume, but the count is
 * printed in every cell — the whole point is spotting a starved pillar, and a
 * pale square is ambiguous where a `0` is not.
 */
export function CoherenceGrid({
  rows,
  windows,
}: {
  rows: ReadonlyArray<{
    pillar_id: string;
    name: string;
    color: string;
    starved: boolean;
    cells: ReadonlyArray<{ window_days: number; count: number; intensity: number }>;
  }>;
  windows: readonly number[];
}) {
  if (rows.length === 0) {
    return <p className="text-sm text-lo">Add a message pillar to see coherence.</p>;
  }

  return (
    <div className="cmw-scroll-x">
      <table className="w-full min-w-[22rem] border-collapse text-sm">
        <thead>
          <tr>
            <th scope="col" className="pb-2 text-left font-medium text-lo">
              Pillar
            </th>
            {windows.map((days) => (
              <th key={days} scope="col" className="pb-2 text-right font-medium text-lo">
                {days}d
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.pillar_id} className="border-t border-edge">
              <th scope="row" className="py-2 pr-3 text-left font-normal">
                <span className="flex items-center gap-2">
                  <span
                    aria-hidden="true"
                    className="size-2.5 shrink-0 rounded-pill"
                    style={{ backgroundColor: row.color }}
                  />
                  <span className="truncate text-hi">{row.name}</span>
                  {row.starved ? (
                    <span className="shrink-0 text-xs text-warn-ink">starved</span>
                  ) : null}
                </span>
              </th>
              {row.cells.map((cell) => (
                <td key={cell.window_days} className="py-1.5 pl-2 text-right">
                  <span
                    title={`${row.name}, last ${cell.window_days} days: ${cell.count}`}
                    className="cmw-numeric inline-flex min-w-9 justify-center rounded-sm px-2 py-1 text-hi"
                    style={{
                      backgroundColor:
                        cell.count === 0
                          ? 'transparent'
                          : `color-mix(in srgb, ${row.color} ${Math.round(
                              12 + cell.intensity * 28,
                            )}%, var(--cmw-surface))`,
                    }}
                  >
                    {cell.count}
                  </span>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Bar meter ─────────────────────────────────────────────────────────────

/** Horizontal bars for element adherence. Value always printed alongside. */
export function BarMeter({
  rows,
  max = 100,
  suffix = '%',
}: {
  rows: ReadonlyArray<{ label: string; value: number; note?: string; tone?: string }>;
  max?: number;
  suffix?: string;
}) {
  return (
    <ul className="flex flex-col gap-2.5">
      {rows.map((row) => (
        <li key={row.label}>
          <div className="mb-1 flex items-baseline justify-between gap-3">
            <span className="text-sm text-hi">{row.label}</span>
            <span className="flex items-baseline gap-2">
              {row.note ? <span className="text-xs text-lo">{row.note}</span> : null}
              <Numeric className="text-sm text-hi">
                {Math.round(row.value)}
                {suffix}
              </Numeric>
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-pill bg-raised">
            <div
              className="h-full rounded-pill transition-[width] duration-500"
              style={{
                width: `${Math.min(100, (row.value / max) * 100)}%`,
                backgroundColor: `var(--cmw-${row.tone ?? 'accent'})`,
              }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}

// ── Pipeline funnel ───────────────────────────────────────────────────────

export function PipelineFunnel({
  stages,
  onSelect,
}: {
  stages: ReadonlyArray<{ status: string; count: number }>;
  onSelect?: (status: string) => void;
}) {
  const max = stages.reduce((m, s) => Math.max(m, s.count), 0);

  return (
    <ul className="flex flex-col gap-1.5">
      {stages.map((stage) => {
        const width = max === 0 ? 0 : (stage.count / max) * 100;
        const content = (
          <>
            <span className="w-20 shrink-0 text-sm capitalize text-lo">{stage.status}</span>
            <span className="h-7 flex-1 overflow-hidden rounded-sm bg-raised">
              <span
                className="flex h-full items-center rounded-sm bg-accent-quiet px-2 transition-[width] duration-500"
                style={{ width: `${Math.max(width, stage.count > 0 ? 12 : 0)}%` }}
              >
                {stage.count > 0 ? (
                  <Numeric className="text-xs font-semibold text-accent-ink">
                    {stage.count}
                  </Numeric>
                ) : null}
              </span>
            </span>
            {stage.count === 0 ? <span className="text-xs text-lo">0</span> : null}
          </>
        );

        return (
          <li key={stage.status}>
            {onSelect ? (
              <button
                type="button"
                onClick={() => onSelect(stage.status)}
                className="flex min-h-11 w-full items-center gap-3 rounded-md px-1 text-left transition-colors duration-150 hover:bg-raised"
              >
                {content}
              </button>
            ) : (
              <div className="flex min-h-11 items-center gap-3 px-1">{content}</div>
            )}
          </li>
        );
      })}
    </ul>
  );
}

// ── Stat tile ─────────────────────────────────────────────────────────────

export function StatTile({
  label,
  value,
  hint,
  tone = 'hi',
  icon,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  tone?: 'hi' | 'success-ink' | 'warn-ink' | 'danger-ink' | 'accent-ink';
  icon?: ReactNode;
}) {
  return (
    <div className="rounded-md border border-edge bg-surface p-3">
      <div className="flex items-center gap-1.5 text-xs text-lo">
        {icon}
        <span>{label}</span>
      </div>
      <div className={cn('cmw-numeric mt-1 text-2xl font-semibold', `text-${tone}`)}>{value}</div>
      {hint ? <p className="mt-0.5 text-xs text-lo">{hint}</p> : null}
    </div>
  );
}
