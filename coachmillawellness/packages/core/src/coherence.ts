/**
 * Content coherence maths (§2 M4) — the third leg of the product triad.
 *
 * The Coherence Map answers one question at a glance: is what she is actually
 * publishing serving the messages she says she stands for? Everything here
 * counts *published* work by default. Counting ideas and drafts would let a
 * starved pillar look healthy because she has been meaning to post about it,
 * which is precisely the self-deception the map exists to break.
 */

import { addDays, toIsoDate } from './dates.js';
import type { ContentItem, ContentStatus, IsoDate, Pillar, Uuid } from './types.js';

/** Work that actually reached an audience. */
export const PUBLISHED_STATUSES: ContentStatus[] = ['posted', 'analyzed'];

export const DEFAULT_WINDOWS = [30, 60, 90] as const;

export interface CoherenceCell {
  window_days: number;
  count: number;
  /** 0–1 against the busiest pillar in the same window — drives cell opacity. */
  intensity: number;
}

export interface CoherenceRow {
  pillar_id: Uuid;
  name: string;
  color: string;
  core_message: string;
  cells: CoherenceCell[];
  /** Count within the widest window. */
  total: number;
  /** Share of all attributed posts in the widest window, 0–1. */
  share: number;
  /** Nothing published for this pillar inside the narrowest window. */
  starved: boolean;
}

export interface CoherenceMatrix {
  windows: number[];
  rows: CoherenceRow[];
  /** Published items carrying no pillar — invisible to the coherence story. */
  unassigned: number;
  total_published: number;
  /** Normalised entropy of the pillar distribution, 0–1. 1 = perfectly even. */
  balance: number;
  /** `1 - balance`. High drift means one message is crowding out the others. */
  drift: number;
  starved_pillars: string[];
  dominant_pillar: string | null;
}

export interface CoherenceOptions {
  /** Defaults to today. Injected so tests are not time-dependent. */
  now?: IsoDate;
  windows?: readonly number[];
  statuses?: ContentStatus[];
}

export function coherenceMatrix(
  pillars: Pillar[],
  items: ContentItem[],
  options: CoherenceOptions = {},
): CoherenceMatrix {
  const now = options.now ?? toIsoDate(new Date());
  const windows = [...(options.windows ?? DEFAULT_WINDOWS)].sort((a, b) => a - b);
  const statuses = options.statuses ?? PUBLISHED_STATUSES;
  const livePillars = pillars.filter((p) => !p.deleted_at);

  const published = items.filter(
    (i) => !i.deleted_at && statuses.includes(i.status) && Boolean(i.publish_date),
  );

  const widest = windows.at(-1) ?? 90;
  const narrowest = windows[0] ?? 30;

  const withinWindow = (item: ContentItem, days: number): boolean => {
    const cutoff = addDays(now, -days);
    const date = item.publish_date!;
    return date >= cutoff && date <= now;
  };

  const inWidest = published.filter((i) => withinWindow(i, widest));
  const attributed = inWidest.filter((i) => i.pillar_id);
  const attributedTotal = attributed.length;

  /**
   * Count every pillar × window pair once, then take each column's maximum from
   * those counts. Intensity is relative within a column, so a quiet 90-day
   * column never makes a busy 30-day column look pale — and doing it in one pass
   * avoids filtering the whole content list twice per cell.
   */
  const columns = windows.map((days) => {
    const counts = livePillars.map(
      (pillar) =>
        published.filter((i) => i.pillar_id === pillar.id && withinWindow(i, days)).length,
    );
    return { days, counts, max: counts.reduce((m, c) => Math.max(m, c), 0) };
  });

  const rows: CoherenceRow[] = livePillars.map((pillar, pillarIndex) => {
    const cells: CoherenceCell[] = columns.map((column) => {
      const count = column.counts[pillarIndex]!;
      return {
        window_days: column.days,
        count,
        intensity: column.max === 0 ? 0 : count / column.max,
      };
    });

    const total = cells.find((c) => c.window_days === widest)?.count ?? 0;
    const narrow = cells.find((c) => c.window_days === narrowest)?.count ?? 0;

    return {
      pillar_id: pillar.id,
      name: pillar.name,
      color: pillar.color,
      core_message: pillar.core_message,
      cells,
      total,
      share: attributedTotal === 0 ? 0 : total / attributedTotal,
      starved: narrow === 0,
    };
  });

  const counts = rows.map((r) => r.total);
  const balance = distributionBalance(counts);
  const withPosts = rows.filter((r) => r.total > 0);
  const dominant = withPosts.length
    ? withPosts.reduce((top, r) => (r.total > top.total ? r : top))
    : null;

  return {
    windows,
    rows,
    unassigned: inWidest.length - attributedTotal,
    total_published: inWidest.length,
    balance,
    drift: Number((1 - balance).toFixed(4)),
    starved_pillars: rows.filter((r) => r.starved).map((r) => r.name),
    dominant_pillar: dominant?.name ?? null,
  };
}

/**
 * Normalised Shannon entropy, 0–1.
 *
 * Chosen over a simpler max/total ratio because it responds to the whole shape
 * of the distribution: three pillars at 10/10/0 and 10/5/5 have the same
 * dominant pillar but very different coherence stories, and entropy tells them
 * apart. Returns 1 (perfectly balanced) when there is nothing to compare —
 * fewer than two pillars, or no posts at all — since "unbalanced" is
 * meaningless there and 0 would read as an alarm.
 */
export function distributionBalance(counts: number[]): number {
  const total = counts.reduce((a, b) => a + b, 0);
  if (total === 0 || counts.length < 2) return 1;
  const entropy = counts.reduce((sum, count) => {
    if (count === 0) return sum;
    const p = count / total;
    return sum - p * Math.log(p);
  }, 0);
  return Number((entropy / Math.log(counts.length)).toFixed(4));
}

// ── Calendar consistency (§2 M4) ──────────────────────────────────────────

export interface HeatmapDay {
  date: IsoDate;
  count: number;
  /** 0–1 against the busiest day in the window. */
  intensity: number;
}

/** GitHub-style publish-consistency strip, oldest day first. */
export function consistencyHeatmap(
  items: ContentItem[],
  options: { now?: IsoDate; days?: number; statuses?: ContentStatus[] } = {},
): HeatmapDay[] {
  const now = options.now ?? toIsoDate(new Date());
  const days = options.days ?? 90;
  const statuses = options.statuses ?? PUBLISHED_STATUSES;

  const counts = new Map<IsoDate, number>();
  for (const item of items) {
    if (item.deleted_at || !statuses.includes(item.status) || !item.publish_date) continue;
    counts.set(item.publish_date, (counts.get(item.publish_date) ?? 0) + 1);
  }

  const strip: HeatmapDay[] = [];
  for (let i = days - 1; i >= 0; i -= 1) {
    const date = addDays(now, -i);
    strip.push({ date, count: counts.get(date) ?? 0, intensity: 0 });
  }
  const max = strip.reduce((m, d) => Math.max(m, d.count), 0);
  return strip.map((d) => ({ ...d, intensity: max === 0 ? 0 : d.count / max }));
}

/** Longest run of consecutive publishing days ending at `now`, and the best ever. */
export function publishStreak(
  items: ContentItem[],
  options: { now?: IsoDate; statuses?: ContentStatus[] } = {},
): { current: number; longest: number } {
  const statuses = options.statuses ?? PUBLISHED_STATUSES;
  const dates = new Set(
    items
      .filter((i) => !i.deleted_at && statuses.includes(i.status) && i.publish_date)
      .map((i) => i.publish_date!),
  );
  if (dates.size === 0) return { current: 0, longest: 0 };

  const now = options.now ?? toIsoDate(new Date());
  let current = 0;
  for (let i = 0; ; i += 1) {
    if (!dates.has(addDays(now, -i))) break;
    current += 1;
  }

  const sorted = [...dates].sort();
  let longest = 0;
  let run = 0;
  let previous: IsoDate | null = null;
  for (const date of sorted) {
    run = previous !== null && addDays(previous, 1) === date ? run + 1 : 1;
    if (run > longest) longest = run;
    previous = date;
  }

  return { current, longest };
}

// ── Pipeline (§2 M4) ──────────────────────────────────────────────────────

export const PIPELINE_ORDER: ContentStatus[] = [
  'idea',
  'script',
  'filmed',
  'posted',
  'analyzed',
];

export function pipelineFunnel(items: ContentItem[]): Array<{ status: ContentStatus; count: number }> {
  const live = items.filter((i) => !i.deleted_at);
  return PIPELINE_ORDER.map((status) => ({
    status,
    count: live.filter((i) => i.status === status).length,
  }));
}
