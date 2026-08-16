/**
 * Last-write-wins sync (§3.2, prompt P6).
 *
 * The engine two devices and a server all agree on. Three pieces:
 *
 *  - an **outbox** of local writes waiting to go up,
 *  - a **last-write-wins merge** on `updated_at`, which every row already
 *    carries because §3.1 put it there for exactly this,
 *  - a **conflict log**, so a losing edit is recorded rather than vanished.
 *
 * The one subtle requirement is *convergence*: after any interleaving of
 * operations, every device must end up with byte-identical state. LWW gives that
 * only if the tie-break is total and deterministic — two devices editing the same
 * row in the same millisecond must independently pick the same winner. Comparing
 * the canonical JSON of the two rows does that; comparing device ids would need a
 * device registry, and "whoever synced last" is not a function of the data and so
 * does not converge at all.
 *
 * Neither the outbox nor the conflict log is part of `CmwDataset`. They are
 * device-local plumbing, not her practice — a backup she forwards should carry
 * her coachees, not this device's retry queue.
 */

import {
  toIsoDateTime,
  uuidv7,
  type DatasetTable,
  type IsoDateTime,
} from '@cmw/core';

import { keyOfRow } from './schema.js';

/** A row on the wire. The table and key travel with it so batches can mix. */
export interface SyncRow {
  table: DatasetTable;
  key: string;
  row: Record<string, unknown>;
}

/** A local write waiting to go up. */
export interface OutboxEntry extends SyncRow {
  id: string;
  queued_at: IsoDateTime;
  attempts: number;
  last_error: string | null;
  /** Earliest instant this may be retried. Set by the backoff on failure. */
  retry_after: IsoDateTime | null;
}

export type ConflictWinner = 'local' | 'remote';

export interface ConflictEntry {
  id: string;
  table: DatasetTable;
  key: string;
  local_updated_at: IsoDateTime;
  remote_updated_at: IsoDateTime;
  winner: ConflictWinner;
  /** The version that lost, kept whole. Nothing is silently destroyed. */
  loser: Record<string, unknown>;
  detected_at: IsoDateTime;
}

// ── The merge rule ────────────────────────────────────────────────────────

/**
 * Canonical JSON — keys sorted at every depth.
 *
 * Used only as a tie-break, but it has to be exact: two devices comparing the
 * same pair of rows must produce the same two strings, and `JSON.stringify`
 * preserves insertion order, which differs between a row that was created
 * locally and the same row parsed back off the wire.
 */
export function canonicalJson(value: unknown): string {
  return JSON.stringify(sortKeysDeep(value));
}

function sortKeysDeep(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortKeysDeep);
  if (value !== null && typeof value === 'object') {
    const source = value as Record<string, unknown>;
    const out: Record<string, unknown> = {};
    for (const key of Object.keys(source).sort()) out[key] = sortKeysDeep(source[key]);
    return out;
  }
  return value;
}

function updatedAt(row: Record<string, unknown>): string {
  const stamp = row.updated_at;
  // A row with no stamp loses to any row that has one, rather than throwing.
  // Sync must not be the thing that refuses to run because one row is odd.
  return typeof stamp === 'string' ? stamp : '';
}

/**
 * Which of two versions wins.
 *
 * Returns `0` only when the rows are genuinely identical, so a caller can skip
 * writing — and so the conflict log records disagreements rather than echoes.
 */
export function lwwCompare(
  local: Record<string, unknown>,
  remote: Record<string, unknown>,
): number {
  const byTime = updatedAt(local).localeCompare(updatedAt(remote));
  if (byTime !== 0) return byTime;
  const localJson = canonicalJson(local);
  const remoteJson = canonicalJson(remote);
  if (localJson === remoteJson) return 0;
  return localJson < remoteJson ? -1 : 1;
}

export interface MergeOutcome {
  winner: Record<string, unknown>;
  /** `null` when the two versions were identical — nothing was in conflict. */
  conflict: { winner: ConflictWinner; loser: Record<string, unknown> } | null;
}

export function mergeRow(
  local: Record<string, unknown> | undefined,
  remote: Record<string, unknown> | undefined,
): MergeOutcome {
  if (!local) return { winner: remote ?? {}, conflict: null };
  if (!remote) return { winner: local, conflict: null };

  const order = lwwCompare(local, remote);
  if (order === 0) return { winner: local, conflict: null };
  return order > 0
    ? { winner: local, conflict: { winner: 'local', loser: remote } }
    : { winner: remote, conflict: { winner: 'remote', loser: local } };
}

// ── Backoff ───────────────────────────────────────────────────────────────

export const BACKOFF_BASE_MS = 1000;
export const BACKOFF_CAP_MS = 5 * 60 * 1000;

/**
 * Exponential backoff, capped at five minutes.
 *
 * Jitter is injected rather than drawn from `Math.random` so the property tests
 * are reproducible — and so a caller that wants a thundering herd of one device
 * can simply not spread it.
 */
export function backoffMs(attempts: number, jitter = 0): number {
  const exponential = BACKOFF_BASE_MS * 2 ** Math.max(0, attempts - 1);
  const capped = Math.min(BACKOFF_CAP_MS, exponential);
  return Math.round(capped * (1 + Math.max(-0.5, Math.min(0.5, jitter))));
}

// ── The outbox ────────────────────────────────────────────────────────────

/**
 * Pending local writes, newest-per-row.
 *
 * Coalesced by `table:key` on purpose: five edits to one session before the next
 * sync are one row to send, not five. LWW makes the intermediate versions
 * unobservable anyway, so queueing them would cost bandwidth to reach the same
 * state.
 */
export class Outbox {
  private entries = new Map<string, OutboxEntry>();

  constructor(initial: readonly OutboxEntry[] = []) {
    for (const entry of initial) this.entries.set(`${entry.table}:${entry.key}`, entry);
  }

  get size(): number {
    return this.entries.size;
  }

  all(): OutboxEntry[] {
    // Queue order, which is creation order — uuidv7 sorts chronologically.
    return [...this.entries.values()].sort((a, b) => a.id.localeCompare(b.id));
  }

  enqueue(table: DatasetTable, row: Record<string, unknown>, now = new Date()): OutboxEntry {
    const key = keyOfRow(table, row);
    const mapKey = `${table}:${key}`;
    const existing = this.entries.get(mapKey);

    const entry: OutboxEntry = {
      // The id is kept across a coalesce so a long-queued row does not jump to
      // the back of the queue every time she touches it again.
      id: existing?.id ?? uuidv7({ now: now.getTime() }),
      table,
      key,
      row,
      queued_at: existing?.queued_at ?? toIsoDateTime(now),
      attempts: 0,
      last_error: null,
      retry_after: null,
    };
    this.entries.set(mapKey, entry);
    return entry;
  }

  /** Entries eligible to send now — everything not held back by a backoff. */
  ready(now = new Date()): OutboxEntry[] {
    const stamp = toIsoDateTime(now);
    return this.all().filter((entry) => entry.retry_after === null || entry.retry_after <= stamp);
  }

  /**
   * Removes an entry after a successful send — unless she edited the row while
   * it was in flight, in which case the newer version stays queued.
   */
  settle(entry: OutboxEntry): void {
    const mapKey = `${entry.table}:${entry.key}`;
    const current = this.entries.get(mapKey);
    if (current && current.row === entry.row) this.entries.delete(mapKey);
  }

  fail(entry: OutboxEntry, error: string, now = new Date(), jitter = 0): void {
    const mapKey = `${entry.table}:${entry.key}`;
    const current = this.entries.get(mapKey);
    if (!current) return;
    const attempts = current.attempts + 1;
    this.entries.set(mapKey, {
      ...current,
      attempts,
      last_error: error,
      retry_after: toIsoDateTime(new Date(now.getTime() + backoffMs(attempts, jitter))),
    });
  }

  clear(): void {
    this.entries.clear();
  }
}

// ── The remote ────────────────────────────────────────────────────────────

/**
 * What a server has to offer.
 *
 * Two methods, and neither knows about Supabase. The same seam as the AI
 * transport: the engine is testable against an in-memory server, and the real
 * adapter is a thin translation written once in P3.
 */
export interface RemoteAdapter {
  /** Rows changed at or after `since`. `null` means "everything". */
  fetchSince(since: IsoDateTime | null): Promise<SyncRow[]>;
  /**
   * Applies rows server-side under the same LWW rule and returns what the server
   * holds afterwards — which is how a device learns it lost a race without a
   * second round trip.
   */
  push(rows: readonly SyncRow[]): Promise<SyncRow[]>;
}

export interface SyncResult {
  pushed: number;
  pulled: number;
  conflicts: ConflictEntry[];
  /** Rows the caller must write locally — the merge already picked winners. */
  apply: SyncRow[];
  /** Entries still queued: either they failed, or she edited them mid-flight. */
  pending: number;
  /** Pass to the next `sync()` — the server's clock, never this device's. */
  cursor: IsoDateTime | null;
  error: string | null;
}

export interface SyncOptions {
  now?: () => Date;
  /** 0 by default so runs are reproducible; spread it in production. */
  jitter?: () => number;
}

/**
 * Push, then pull, then merge.
 *
 * Push first because a device that pulls first would merge the server's older
 * copy of a row it is about to overwrite, log a conflict against itself, and
 * report a disagreement that never existed.
 */
export class SyncEngine {
  readonly outbox: Outbox;
  private readonly now: () => Date;
  private readonly jitter: () => number;

  constructor(outbox = new Outbox(), options: SyncOptions = {}) {
    this.outbox = outbox;
    this.now = options.now ?? (() => new Date());
    this.jitter = options.jitter ?? (() => 0);
  }

  queue(table: DatasetTable, rows: readonly Record<string, unknown>[]): void {
    for (const row of rows) this.outbox.enqueue(table, row, this.now());
  }

  async sync(
    remote: RemoteAdapter,
    local: (table: DatasetTable, key: string) => Record<string, unknown> | undefined,
    since: IsoDateTime | null = null,
  ): Promise<SyncResult> {
    const conflicts: ConflictEntry[] = [];
    const apply: SyncRow[] = [];
    let pushed = 0;

    const ready = this.outbox.ready(this.now());

    if (ready.length > 0) {
      try {
        const settled = await remote.push(ready);
        pushed = ready.length;
        for (const entry of ready) this.outbox.settle(entry);

        // The server may have applied a newer version than the one just sent.
        for (const row of settled) {
          const mine = local(row.table, row.key);
          const outcome = mergeRow(mine, row.row);
          if (outcome.conflict) {
            conflicts.push(this.logConflict(row, mine, outcome.conflict));
          }
          if (!mine || lwwCompare(mine, outcome.winner) !== 0) {
            apply.push({ table: row.table, key: row.key, row: outcome.winner });
          }
        }
      } catch (cause) {
        const message = cause instanceof Error ? cause.message : String(cause);
        for (const entry of ready) {
          this.outbox.fail(entry, message, this.now(), this.jitter());
        }
        return {
          pushed: 0,
          pulled: 0,
          conflicts,
          apply,
          pending: this.outbox.size,
          cursor: since,
          error: message,
        };
      }
    }

    let incoming: SyncRow[];
    try {
      incoming = await remote.fetchSince(since);
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : String(cause);
      return {
        pushed,
        pulled: 0,
        conflicts,
        apply,
        pending: this.outbox.size,
        cursor: since,
        error: message,
      };
    }

    let cursor = since;
    for (const row of incoming) {
      const stamp = updatedAt(row.row);
      if (stamp && (cursor === null || stamp > cursor)) cursor = stamp;

      const mine = local(row.table, row.key);
      const outcome = mergeRow(mine, row.row);
      if (outcome.conflict) conflicts.push(this.logConflict(row, mine, outcome.conflict));

      if (!mine || lwwCompare(mine, outcome.winner) !== 0) {
        apply.push({ table: row.table, key: row.key, row: outcome.winner });
      }

      // A local row that won against the server has to go back up, or the two
      // sides stay disagreeing forever with neither noticing.
      if (outcome.conflict?.winner === 'local') {
        this.outbox.enqueue(row.table, outcome.winner, this.now());
      }
    }

    return {
      pushed,
      pulled: incoming.length,
      conflicts,
      apply: dedupe(apply),
      pending: this.outbox.size,
      cursor,
      error: null,
    };
  }

  private logConflict(
    row: SyncRow,
    mine: Record<string, unknown> | undefined,
    conflict: NonNullable<MergeOutcome['conflict']>,
  ): ConflictEntry {
    const at = this.now();
    return {
      id: uuidv7({ now: at.getTime() }),
      table: row.table,
      key: row.key,
      local_updated_at: mine ? updatedAt(mine) : '',
      remote_updated_at: updatedAt(row.row),
      winner: conflict.winner,
      loser: conflict.loser,
      detected_at: toIsoDateTime(at),
    };
  }
}

/** Last write per row wins within one batch, so callers apply each row once. */
function dedupe(rows: readonly SyncRow[]): SyncRow[] {
  const byKey = new Map<string, SyncRow>();
  for (const row of rows) byKey.set(`${row.table}:${row.key}`, row);
  return [...byKey.values()];
}

/**
 * An in-memory server applying the same merge rule.
 *
 * Not a test double kept in a test file: it is the executable specification of
 * what the Supabase side must do, and the property tests assert that a device
 * and this server converge. P3's Postgres trigger has to match it.
 */
export class MemoryRemote implements RemoteAdapter {
  private rows = new Map<string, SyncRow>();

  snapshot(): SyncRow[] {
    return [...this.rows.values()].sort((a, b) =>
      `${a.table}:${a.key}`.localeCompare(`${b.table}:${b.key}`),
    );
  }

  fetchSince(since: IsoDateTime | null): Promise<SyncRow[]> {
    const rows = this.snapshot().filter(
      (row) => since === null || updatedAt(row.row) >= since,
    );
    return Promise.resolve(rows.map((row) => ({ ...row, row: { ...row.row } })));
  }

  push(rows: readonly SyncRow[]): Promise<SyncRow[]> {
    const touched: SyncRow[] = [];
    for (const incoming of rows) {
      const mapKey = `${incoming.table}:${incoming.key}`;
      const existing = this.rows.get(mapKey);
      const outcome = mergeRow(incoming.row, existing?.row);
      const stored: SyncRow = {
        table: incoming.table,
        key: incoming.key,
        row: { ...outcome.winner },
      };
      this.rows.set(mapKey, stored);
      touched.push({ ...stored, row: { ...stored.row } });
    }
    return Promise.resolve(touched);
  }
}
