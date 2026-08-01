import type { DatasetTable } from '@cmw/core';
import { describe, expect, it } from 'vitest';

import {
  BACKOFF_CAP_MS,
  MemoryRemote,
  Outbox,
  SyncEngine,
  backoffMs,
  canonicalJson,
  lwwCompare,
  mergeRow,
  type RemoteAdapter,
  type SyncRow,
} from '../sync.js';

const TABLE: DatasetTable = 'coachees';

function row(id: string, updated: string, extra: Record<string, unknown> = {}) {
  return { id, name: 'Naledi M.', updated_at: updated, ...extra };
}

describe('canonicalJson', () => {
  it('is insertion-order independent, which is what makes the tie-break agree', () => {
    // The same row created locally and parsed off the wire have different key
    // orders. If the tie-break saw that difference the two devices would pick
    // different winners and never converge.
    expect(canonicalJson({ a: 1, b: 2 })).toBe(canonicalJson({ b: 2, a: 1 }));
    expect(canonicalJson({ x: { p: 1, q: 2 } })).toBe(canonicalJson({ x: { q: 2, p: 1 } }));
  });

  it('does not reorder arrays, which carry meaning', () => {
    expect(canonicalJson({ tags: ['b', 'a'] })).not.toBe(canonicalJson({ tags: ['a', 'b'] }));
  });
});

describe('lwwCompare', () => {
  it('prefers the later updated_at', () => {
    expect(lwwCompare(row('c1', '2099-03-02T00:00:00.000Z'), row('c1', '2099-03-01T00:00:00.000Z'))).toBeGreaterThan(0);
    expect(lwwCompare(row('c1', '2099-03-01T00:00:00.000Z'), row('c1', '2099-03-02T00:00:00.000Z'))).toBeLessThan(0);
  });

  it('reports identical rows as equal so nothing is written or logged', () => {
    expect(lwwCompare(row('c1', '2099-03-01T00:00:00.000Z'), row('c1', '2099-03-01T00:00:00.000Z'))).toBe(0);
  });

  it('breaks a same-millisecond tie the same way from either side', () => {
    const a = row('c1', '2099-03-01T00:00:00.000Z', { note: 'alpha' });
    const b = row('c1', '2099-03-01T00:00:00.000Z', { note: 'beta' });
    // Antisymmetric: whichever device evaluates it reaches the same winner.
    expect(Math.sign(lwwCompare(a, b))).toBe(-Math.sign(lwwCompare(b, a)));
    expect(lwwCompare(a, b)).not.toBe(0);
  });

  it('lets a row with no stamp lose rather than throwing', () => {
    const stamped = row('c1', '2099-03-01T00:00:00.000Z');
    const bare = { id: 'c1', name: 'Naledi M.' };
    expect(lwwCompare(stamped, bare)).toBeGreaterThan(0);
  });
});

describe('mergeRow', () => {
  it('takes whichever side exists when only one does', () => {
    const only = row('c1', '2099-03-01T00:00:00.000Z');
    expect(mergeRow(only, undefined)).toEqual({ winner: only, conflict: null });
    expect(mergeRow(undefined, only)).toEqual({ winner: only, conflict: null });
  });

  it('records the loser whole, so a losing edit is never destroyed', () => {
    const local = row('c1', '2099-03-02T00:00:00.000Z', { note: 'mine' });
    const remote = row('c1', '2099-03-01T00:00:00.000Z', { note: 'theirs' });
    const outcome = mergeRow(local, remote);
    expect(outcome.winner).toBe(local);
    expect(outcome.conflict).toEqual({ winner: 'local', loser: remote });
  });

  it('reports no conflict when the two sides already agree', () => {
    const same = row('c1', '2099-03-01T00:00:00.000Z');
    expect(mergeRow(same, { ...same }).conflict).toBeNull();
  });
});

describe('backoff', () => {
  it('doubles and then caps at five minutes', () => {
    expect(backoffMs(1)).toBe(1000);
    expect(backoffMs(2)).toBe(2000);
    expect(backoffMs(3)).toBe(4000);
    expect(backoffMs(30)).toBe(BACKOFF_CAP_MS);
  });

  it('spreads by the jitter it is given, and clamps a silly one', () => {
    expect(backoffMs(2, 0.5)).toBe(3000);
    expect(backoffMs(2, -0.5)).toBe(1000);
    expect(backoffMs(2, 99)).toBe(3000);
  });
});

describe('the outbox', () => {
  const now = new Date('2099-03-10T08:00:00.000Z');

  it('coalesces repeat edits of one row into a single pending write', () => {
    const outbox = new Outbox();
    outbox.enqueue(TABLE, row('c1', '2099-03-10T08:00:00.000Z'), now);
    outbox.enqueue(TABLE, row('c1', '2099-03-10T08:00:01.000Z'), now);
    outbox.enqueue(TABLE, row('c2', '2099-03-10T08:00:02.000Z'), now);

    expect(outbox.size).toBe(2);
    // Looked up by key rather than by position: two rows enqueued in the same
    // millisecond share a uuidv7 timestamp prefix, so their relative order comes
    // down to random bits. Queue order does not affect convergence, so the code
    // leaves it alone and the test does not pretend otherwise.
    const pending = outbox.all().find((entry) => entry.key === 'c1');
    expect(pending?.row.updated_at).toBe('2099-03-10T08:00:01.000Z');
  });

  it('keeps a coalesced row in its original queue position', () => {
    // Otherwise a row she keeps touching starves behind everything else.
    const outbox = new Outbox();
    const first = outbox.enqueue(TABLE, row('c1', '2099-03-10T08:00:00.000Z'), now);
    outbox.enqueue(TABLE, row('c2', '2099-03-10T08:00:01.000Z'), new Date(now.getTime() + 1000));
    const again = outbox.enqueue(TABLE, row('c1', '2099-03-10T08:00:02.000Z'), new Date(now.getTime() + 2000));

    expect(again.id).toBe(first.id);
    expect(outbox.all()[0]!.key).toBe('c1');
  });

  it('holds a failed entry back until its backoff expires', () => {
    const outbox = new Outbox();
    const entry = outbox.enqueue(TABLE, row('c1', '2099-03-10T08:00:00.000Z'), now);
    outbox.fail(entry, 'offline', now);

    expect(outbox.ready(now)).toHaveLength(0);
    expect(outbox.ready(new Date(now.getTime() + 2000))).toHaveLength(1);
    expect(outbox.all()[0]!.last_error).toBe('offline');
    expect(outbox.all()[0]!.attempts).toBe(1);
  });

  it('keeps an edit made while the previous version was in flight', () => {
    const outbox = new Outbox();
    const sent = outbox.enqueue(TABLE, row('c1', '2099-03-10T08:00:00.000Z'), now);
    // She edits again before the push returns.
    outbox.enqueue(TABLE, row('c1', '2099-03-10T08:00:05.000Z'), now);
    outbox.settle(sent);

    expect(outbox.size).toBe(1);
    expect(outbox.all()[0]!.row.updated_at).toBe('2099-03-10T08:00:05.000Z');
  });
});

// ── The engine ────────────────────────────────────────────────────────────

/** A device: a local row store plus an engine, wired the way an app would. */
class Device {
  readonly rows = new Map<string, Record<string, unknown>>();
  readonly engine: SyncEngine;
  cursor: string | null = null;

  constructor(now: () => Date) {
    this.engine = new SyncEngine(new Outbox(), { now });
  }

  write(key: string, row: Record<string, unknown>): void {
    this.rows.set(key, row);
    this.engine.queue(TABLE, [row]);
  }

  async sync(remote: RemoteAdapter, incremental = false): Promise<void> {
    const result = await this.engine.sync(
      remote,
      (_table, key) => this.rows.get(key),
      incremental ? this.cursor : null,
    );
    for (const applied of result.apply) this.rows.set(applied.key, applied.row);
    this.cursor = result.cursor;
  }

  snapshot(): string {
    return canonicalJson([...this.rows.entries()].sort((a, b) => a[0].localeCompare(b[0])));
  }
}

describe('SyncEngine', () => {
  const clock = () => new Date('2099-03-10T08:00:00.000Z');

  it('pushes queued rows and clears the outbox', async () => {
    const remote = new MemoryRemote();
    const device = new Device(clock);
    device.write('c1', row('c1', '2099-03-10T08:00:00.000Z'));

    const result = await device.engine.sync(remote, (_t, key) => device.rows.get(key));
    expect(result.pushed).toBe(1);
    expect(result.pending).toBe(0);
    expect(result.error).toBeNull();
    expect(remote.snapshot()).toHaveLength(1);
  });

  it('pulls a row the device has never seen', async () => {
    const remote = new MemoryRemote();
    await remote.push([{ table: TABLE, key: 'c9', row: row('c9', '2099-03-09T00:00:00.000Z') }]);

    const device = new Device(clock);
    await device.sync(remote);

    expect(device.rows.get('c9')?.updated_at).toBe('2099-03-09T00:00:00.000Z');
  });

  it('logs a conflict and keeps the losing version', async () => {
    const remote = new MemoryRemote();
    await remote.push([
      { table: TABLE, key: 'c1', row: row('c1', '2099-03-09T00:00:00.000Z', { note: 'server' }) },
    ]);

    const device = new Device(clock);
    device.rows.set('c1', row('c1', '2099-03-10T00:00:00.000Z', { note: 'mine' }));

    const result = await device.engine.sync(remote, (_t, key) => device.rows.get(key));
    expect(result.conflicts).toHaveLength(1);
    expect(result.conflicts[0]!.winner).toBe('local');
    expect(result.conflicts[0]!.loser.note).toBe('server');
  });

  it('re-queues a local row that beat the server, or the two never agree', async () => {
    const remote = new MemoryRemote();
    await remote.push([
      { table: TABLE, key: 'c1', row: row('c1', '2099-03-09T00:00:00.000Z', { note: 'server' }) },
    ]);

    const device = new Device(clock);
    // Held locally but never queued — the case where a pull discovers the clash.
    device.rows.set('c1', row('c1', '2099-03-10T00:00:00.000Z', { note: 'mine' }));

    const first = await device.engine.sync(remote, (_t, key) => device.rows.get(key));
    expect(first.pending).toBe(1);

    await device.engine.sync(remote, (_t, key) => device.rows.get(key));
    expect(remote.snapshot()[0]!.row.note).toBe('mine');
  });

  it('does not write back a row it already agrees with', async () => {
    const remote = new MemoryRemote();
    const shared = row('c1', '2099-03-09T00:00:00.000Z');
    await remote.push([{ table: TABLE, key: 'c1', row: shared }]);

    const device = new Device(clock);
    device.rows.set('c1', { ...shared });

    const result = await device.engine.sync(remote, (_t, key) => device.rows.get(key));
    expect(result.apply).toHaveLength(0);
    expect(result.conflicts).toHaveLength(0);
  });

  it('holds the queue and reports the error when the push fails', async () => {
    const offline: RemoteAdapter = {
      fetchSince: () => Promise.reject(new Error('offline')),
      push: () => Promise.reject(new Error('offline')),
    };
    const device = new Device(clock);
    device.write('c1', row('c1', '2099-03-10T08:00:00.000Z'));

    const result = await device.engine.sync(offline, (_t, key) => device.rows.get(key));
    expect(result.error).toBe('offline');
    expect(result.pending).toBe(1);
    // Backed off, so an immediate retry does not hammer a server that is down.
    expect(device.engine.outbox.ready(clock())).toHaveLength(0);
  });

  it('survives a pull failing after a successful push', async () => {
    const half: RemoteAdapter = {
      push: (rows) => Promise.resolve([...rows]),
      fetchSince: () => Promise.reject(new Error('gateway timeout')),
    };
    const device = new Device(clock);
    device.write('c1', row('c1', '2099-03-10T08:00:00.000Z'));

    const result = await device.engine.sync(half, (_t, key) => device.rows.get(key));
    expect(result.pushed).toBe(1);
    expect(result.error).toBe('gateway timeout');
  });

  it('advances the cursor to the newest row the server returned', async () => {
    const remote = new MemoryRemote();
    await remote.push([
      { table: TABLE, key: 'c1', row: row('c1', '2099-03-08T00:00:00.000Z') },
      { table: TABLE, key: 'c2', row: row('c2', '2099-03-09T00:00:00.000Z') },
    ]);

    const device = new Device(clock);
    await device.sync(remote, true);
    expect(device.cursor).toBe('2099-03-09T00:00:00.000Z');
  });
});

// ── Convergence (the P6 acceptance criterion) ─────────────────────────────

/**
 * Deterministic PRNG.
 *
 * `Math.random` would make a failure unreproducible, and a convergence bug that
 * shows up once in a thousand runs is exactly the kind you need to replay.
 */
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

describe('convergence — 1,000 random interleavings across two devices', () => {
  it('always reaches identical state on both devices and the server', async () => {
    const failures: string[] = [];

    for (let seed = 1; seed <= 1000; seed += 1) {
      const random = mulberry32(seed);
      const remote = new MemoryRemote();

      let tick = 0;
      // A shared clock the devices both read, so same-millisecond collisions —
      // the case the tie-break exists for — actually occur.
      const clock = (): Date => new Date(Date.UTC(2099, 2, 10, 8, 0, 0, tick));

      const a = new Device(clock);
      const b = new Device(clock);
      const devices = [a, b];

      const keys = ['c1', 'c2', 'c3'];

      for (let step = 0; step < 12; step += 1) {
        const device = devices[Math.floor(random() * devices.length)]!;
        const action = random();

        if (action < 0.6) {
          // An edit. The clock advances only sometimes, so roughly a third of
          // writes land on a timestamp another device has already used.
          if (random() < 0.7) tick += 1;
          const key = keys[Math.floor(random() * keys.length)]!;
          device.write(
            key,
            row(key, clock().toISOString(), { note: `s${seed}-${step}`, score: Math.floor(random() * 10) }),
          );
        } else {
          await device.sync(remote, random() < 0.5);
        }
      }

      // Quiesce: sync both devices until nothing changes. Convergence is the
      // claim that this terminates and agrees, not that one round suffices.
      let settled = false;
      for (let round = 0; round < 8 && !settled; round += 1) {
        const before = `${a.snapshot()}|${b.snapshot()}`;
        await a.sync(remote);
        await b.sync(remote);
        await a.sync(remote);
        settled = `${a.snapshot()}|${b.snapshot()}` === before;
      }

      const serverState = canonicalJson(
        remote.snapshot().map((entry) => [entry.key, entry.row] as const),
      );

      if (a.snapshot() !== b.snapshot()) {
        failures.push(`seed ${seed}: devices disagree\n  A ${a.snapshot()}\n  B ${b.snapshot()}`);
      } else if (a.snapshot() !== serverState) {
        failures.push(`seed ${seed}: device and server disagree\n  D ${a.snapshot()}\n  S ${serverState}`);
      }
    }

    expect(failures.slice(0, 3).join('\n'), `${failures.length} of 1000 seeds diverged`).toBe('');
  });

  it('converges regardless of which device syncs first', async () => {
    // Order-independence is the property LWW buys; asserting it directly means a
    // regression shows up as this test rather than as a rare seed.
    for (const first of [0, 1]) {
      const remote = new MemoryRemote();
      const clock = (): Date => new Date('2099-03-10T08:00:00.000Z');
      const a = new Device(clock);
      const b = new Device(clock);

      a.write('c1', row('c1', '2099-03-10T08:00:00.000Z', { note: 'a' }));
      b.write('c1', row('c1', '2099-03-10T08:00:00.000Z', { note: 'b' }));

      const order = first === 0 ? [a, b] : [b, a];
      for (const device of order) await device.sync(remote);
      for (const device of order) await device.sync(remote);
      for (const device of order) await device.sync(remote);

      expect(a.snapshot()).toBe(b.snapshot());
    }
  });
});
