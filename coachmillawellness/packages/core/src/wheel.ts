/**
 * Wheel of Life maths (§2 M3, §4.3) — the signature element's brain.
 *
 * The wheel is stored as one row per domain per date (§3.1) because that is the
 * right shape for Postgres and for sync. It is *used* as a snapshot of ten
 * domains, so grouping happens here, once, rather than in every screen.
 *
 * The domain list is editable per coachee, which means two snapshots of the same
 * person can legitimately disagree about which domains exist. Every function
 * here handles that instead of assuming ten fixed spokes.
 */

import type { IsoDate, Uuid, WheelSnapshot, WheelSnapshotRow } from './types.js';

export const WHEEL_MIN = 0;
export const WHEEL_MAX = 10;

export function clampScore(value: number): number {
  if (Number.isNaN(value)) return WHEEL_MIN;
  return Math.min(WHEEL_MAX, Math.max(WHEEL_MIN, value));
}

/** Groups flat rows into dated snapshots, oldest first. */
export function groupWheelRows(rows: WheelSnapshotRow[], coacheeId?: Uuid): WheelSnapshot[] {
  const relevant = rows.filter(
    (r) => !r.deleted_at && (coacheeId === undefined || r.coachee_id === coacheeId),
  );

  const byKey = new Map<string, WheelSnapshot>();
  for (const row of relevant) {
    const key = `${row.coachee_id}|${row.date}`;
    let snapshot = byKey.get(key);
    if (!snapshot) {
      snapshot = { coachee_id: row.coachee_id, date: row.date, domains: [] };
      byKey.set(key, snapshot);
    }
    // A re-scored domain on the same date replaces the earlier value.
    const existing = snapshot.domains.findIndex((d) => d.domain === row.domain);
    const entry = {
      domain: row.domain,
      score: clampScore(row.score),
      target: clampScore(row.target),
    };
    if (existing === -1) snapshot.domains.push(entry);
    else snapshot.domains[existing] = entry;
  }

  return [...byKey.values()].sort(
    (a, b) => a.date.localeCompare(b.date) || a.coachee_id.localeCompare(b.coachee_id),
  );
}

export function latestSnapshot(
  rows: WheelSnapshotRow[],
  coacheeId: Uuid,
): WheelSnapshot | null {
  const snapshots = groupWheelRows(rows, coacheeId);
  return snapshots.at(-1) ?? null;
}

export function snapshotOn(
  rows: WheelSnapshotRow[],
  coacheeId: Uuid,
  date: IsoDate,
): WheelSnapshot | null {
  return groupWheelRows(rows, coacheeId).find((s) => s.date === date) ?? null;
}

export function wheelAverage(snapshot: WheelSnapshot | null): number | null {
  if (!snapshot || snapshot.domains.length === 0) return null;
  const total = snapshot.domains.reduce((sum, d) => sum + d.score, 0);
  return Number((total / snapshot.domains.length).toFixed(2));
}

export function domainsBelow(snapshot: WheelSnapshot | null, threshold: number): string[] {
  return (snapshot?.domains ?? []).filter((d) => d.score <= threshold).map((d) => d.domain);
}

export interface TargetGap {
  domain: string;
  score: number;
  target: number;
  /** Positive means the target is still ahead. */
  gap: number;
}

export function gapToTarget(snapshot: WheelSnapshot | null): TargetGap[] {
  return (snapshot?.domains ?? [])
    .map((d) => ({ domain: d.domain, score: d.score, target: d.target, gap: d.target - d.score }))
    .sort((a, b) => b.gap - a.gap);
}

// ── Delta ─────────────────────────────────────────────────────────────────

export interface DomainDelta {
  domain: string;
  /** `null` when the domain did not exist in that snapshot. */
  from: number | null;
  to: number | null;
  /** `null` when the domain is only present on one side. */
  delta: number | null;
  improved: boolean;
  declined: boolean;
  unchanged: boolean;
  target: number | null;
  gap: number | null;
}

export interface WheelDeltaResult {
  from_date: IsoDate | null;
  to_date: IsoDate | null;
  domains: DomainDelta[];
  average_from: number | null;
  average_to: number | null;
  average_delta: number | null;
  improved: string[];
  declined: string[];
  unchanged: string[];
  biggest_gain: DomainDelta | null;
  biggest_drop: DomainDelta | null;
  /** Domains she added to or removed from the wheel between the two dates. */
  domains_added: string[];
  domains_removed: string[];
}

/**
 * Compares two snapshots. Powers the before/after split view for client reports
 * and the sage particle burst on improved domains (§4.3).
 *
 * Both arguments are nullable because a first-ever snapshot has nothing to
 * compare against, and the UI should render that case rather than guard it.
 */
export function wheelDelta(
  from: WheelSnapshot | null,
  to: WheelSnapshot | null,
): WheelDeltaResult {
  const fromMap = new Map((from?.domains ?? []).map((d) => [d.domain, d]));
  const toMap = new Map((to?.domains ?? []).map((d) => [d.domain, d]));

  // Preserve the newer snapshot's domain order — it is the current wheel.
  const names = [
    ...(to?.domains ?? []).map((d) => d.domain),
    ...(from?.domains ?? []).map((d) => d.domain).filter((n) => !toMap.has(n)),
  ];

  const domains: DomainDelta[] = names.map((domain) => {
    const before = fromMap.get(domain);
    const after = toMap.get(domain);
    // `names` is assembled from the two maps, so at least one side always holds
    // this domain — which is what lets the target fall back without a null case.
    const present = (after ?? before)!;
    const delta =
      before !== undefined && after !== undefined
        ? Number((after.score - before.score).toFixed(2))
        : null;
    return {
      domain,
      from: before?.score ?? null,
      to: after?.score ?? null,
      delta,
      improved: delta !== null && delta > 0,
      declined: delta !== null && delta < 0,
      unchanged: delta === 0,
      target: present.target,
      gap: after !== undefined ? Number((after.target - after.score).toFixed(2)) : null,
    };
  });

  // Narrowing `delta` to a number here removes the `?? 0` guards the movers
  // below would otherwise need for a case the filter already excluded.
  type Moved = DomainDelta & { delta: number };
  const moved = domains.filter((d): d is Moved => d.delta !== null);
  const gains = moved.filter((d) => d.improved);
  const drops = moved.filter((d) => d.declined);

  const averageFrom = wheelAverage(from);
  const averageTo = wheelAverage(to);

  return {
    from_date: from?.date ?? null,
    to_date: to?.date ?? null,
    domains,
    average_from: averageFrom,
    average_to: averageTo,
    average_delta:
      averageFrom !== null && averageTo !== null
        ? Number((averageTo - averageFrom).toFixed(2))
        : null,
    improved: gains.map((d) => d.domain),
    declined: drops.map((d) => d.domain),
    unchanged: moved.filter((d) => d.unchanged).map((d) => d.domain),
    biggest_gain: gains.length ? gains.reduce((top, d) => (d.delta > top.delta ? d : top)) : null,
    biggest_drop: drops.length ? drops.reduce((low, d) => (d.delta < low.delta ? d : low)) : null,
    domains_added: [...toMap.keys()].filter((n) => !fromMap.has(n)),
    domains_removed: [...fromMap.keys()].filter((n) => !toMap.has(n)),
  };
}

// ── Morph ─────────────────────────────────────────────────────────────────

/**
 * Interpolates between two snapshots for the timeline scrubber (§4.3, 600ms
 * expo-out morph). Kept pure and here — not inside the component — so the
 * tween is unit-testable and the same maths can drive a WebM export frame by
 * frame.
 *
 * A domain missing from one side animates from its own value rather than from
 * zero, so adding a domain does not make the wheel appear to collapse.
 */
export function interpolateSnapshots(
  from: WheelSnapshot | null,
  to: WheelSnapshot | null,
  t: number,
): Array<{ domain: string; score: number; target: number }> {
  const clampedT = Math.min(1, Math.max(0, t));
  const fromMap = new Map((from?.domains ?? []).map((d) => [d.domain, d]));
  const toMap = new Map((to?.domains ?? []).map((d) => [d.domain, d]));
  const names = [
    ...(to?.domains ?? []).map((d) => d.domain),
    ...(from?.domains ?? []).map((d) => d.domain).filter((n) => !toMap.has(n)),
  ];

  return names.map((domain) => {
    const a = fromMap.get(domain) ?? toMap.get(domain)!;
    const b = toMap.get(domain) ?? fromMap.get(domain)!;
    return {
      domain,
      score: Number((a.score + (b.score - a.score) * clampedT).toFixed(3)),
      target: Number((a.target + (b.target - a.target) * clampedT).toFixed(3)),
    };
  });
}

/** Builds the ten rows that make up one snapshot, ready to persist. */
export function snapshotToRows(
  snapshot: WheelSnapshot,
  makeId: () => string,
  updatedAt: string,
): WheelSnapshotRow[] {
  return snapshot.domains.map((d) => ({
    id: makeId(),
    coachee_id: snapshot.coachee_id,
    date: snapshot.date,
    domain: d.domain,
    score: clampScore(d.score),
    target: clampScore(d.target),
    updated_at: updatedAt,
  }));
}
