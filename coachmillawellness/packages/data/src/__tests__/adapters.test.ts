/**
 * Adapter conformance.
 *
 * Both stores are driven through the same suite, against real IndexedDB
 * semantics via fake-indexeddb. An adapter that only passes in memory would let
 * a transaction or key-path bug reach her device, so the contract is tested where
 * it actually runs.
 */

import 'fake-indexeddb/auto';

import { emptyDataset } from '@cmw/core';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { DexieStore, openBestStore } from '../dexie-adapter.js';
import { MemoryStore } from '../memory-adapter.js';
import { seedDataset } from '../seed.js';
import type { DescribableStore } from '../store.js';
import { exportJSON, importJSON } from '../transfer.js';

const NOW = new Date('2026-07-30T10:00:00.000Z');

let databaseCounter = 0;

const adapters: Array<{ name: string; make: () => DescribableStore }> = [
  { name: 'MemoryStore', make: () => new MemoryStore() },
  {
    name: 'DexieStore',
    // A fresh database per test, so state never leaks between cases.
    make: () => new DexieStore(`cmw-test-${(databaseCounter += 1)}`),
  },
];

describe.each(adapters)('$name', ({ make }) => {
  let store: DescribableStore;

  beforeEach(async () => {
    store = make();
    await store.open();
  });

  afterEach(async () => {
    await store.clear();
    await store.close();
  });

  it('starts empty', async () => {
    expect(await store.load()).toEqual(emptyDataset());
  });

  it('stores and returns rows', async () => {
    await store.put('coachees', [
      {
        id: 'c1',
        name: 'Naledi M.',
        status: 'active',
        start_date: '2026-01-15',
        tags: [],
        updated_at: NOW.toISOString(),
      },
    ]);

    const loaded = await store.load();
    expect(loaded.coachees).toHaveLength(1);
    expect(loaded.coachees[0]!.name).toBe('Naledi M.');
  });

  it('replaces a row with the same primary key rather than duplicating it', async () => {
    const base = {
      id: 'c1',
      name: 'Naledi M.',
      status: 'active' as const,
      start_date: '2026-01-15',
      tags: [],
      updated_at: NOW.toISOString(),
    };
    await store.put('coachees', [base]);
    await store.put('coachees', [{ ...base, name: 'Naledi Mokoena', status: 'paused' }]);

    const loaded = await store.load();
    expect(loaded.coachees).toHaveLength(1);
    expect(loaded.coachees[0]!.name).toBe('Naledi Mokoena');
    expect(loaded.coachees[0]!.status).toBe('paused');
  });

  it('keys settings by key, not id', async () => {
    await store.put('settings', [{ key: 'theme', value: 'dawn', updated_at: NOW.toISOString() }]);
    await store.put('settings', [{ key: 'theme', value: 'morning', updated_at: NOW.toISOString() }]);

    const loaded = await store.load();
    expect(loaded.settings).toHaveLength(1);
    expect(loaded.settings[0]!.value).toBe('morning');
  });

  it('does nothing for an empty write', async () => {
    await store.put('coachees', []);
    expect((await store.load()).coachees).toEqual([]);
  });

  it('hard-deletes by primary key', async () => {
    await store.replaceAll(seedDataset(NOW));
    const before = await store.load();
    const victim = before.coachees[0]!.id;

    await store.hardDelete('coachees', [victim]);
    const after = await store.load();

    expect(after.coachees.map((c) => c.id)).not.toContain(victim);
    expect(after.coachees).toHaveLength(before.coachees.length - 1);
  });

  it('ignores an empty delete', async () => {
    await store.replaceAll(seedDataset(NOW));
    await store.hardDelete('coachees', []);
    expect((await store.load()).coachees).toHaveLength(2);
  });

  it('replaces the whole dataset atomically', async () => {
    await store.put('coachees', [
      {
        id: 'stale',
        name: 'Should not survive',
        status: 'active',
        start_date: '2020-01-01',
        tags: [],
        updated_at: NOW.toISOString(),
      },
    ]);

    await store.replaceAll(seedDataset(NOW));
    const loaded = await store.load();

    expect(loaded.coachees.map((c) => c.id)).not.toContain('stale');
    expect(loaded.coachees).toHaveLength(2);
    expect(loaded.wheel_snapshots).toHaveLength(40);
  });

  it('clears everything', async () => {
    await store.replaceAll(seedDataset(NOW));
    await store.clear();
    expect(await store.load()).toEqual(emptyDataset());
  });

  it('survives the full export → wipe → import cycle', async () => {
    // Gate G2, end to end and through real storage rather than only in memory.
    await store.replaceAll(seedDataset(NOW));
    const before = await store.load();
    const backup = exportJSON(before, { now: NOW.toISOString() });

    await store.clear();
    expect((await store.load()).coachees).toEqual([]);

    await store.replaceAll(importJSON(backup));
    const after = await store.load();

    expect(exportJSON(after, { now: NOW.toISOString() })).toBe(backup);
  });

  it('round-trips every nested value through storage', async () => {
    await store.replaceAll(seedDataset(NOW));
    const loaded = await store.load();

    const goal = loaded.goals.find((g) => !g.smarter.E)!;
    expect(goal.smarter.Rw).toBe(false);
    expect(loaded.sessions.find((s) => s.participants.length === 2)).toBeDefined();
    expect(loaded.settings.find((s) => s.key === 'wheel_domains')?.value).toHaveLength(10);
  });

  it('does not hand out a live reference to its own state', async () => {
    // Mutating what `load()` returned must not silently rewrite the database.
    await store.put('coachees', [
      {
        id: 'c1',
        name: 'Naledi M.',
        status: 'active',
        start_date: '2026-01-15',
        tags: [],
        updated_at: NOW.toISOString(),
      },
    ]);

    const first = await store.load();
    first.coachees[0]!.name = 'Mutated';
    expect((await store.load()).coachees[0]!.name).toBe('Naledi M.');
  });
});

describe('MemoryStore extras', () => {
  it('reports its kind and row counts for the Vault screen', async () => {
    const store = new MemoryStore();
    await store.open();
    await store.replaceAll(seedDataset(NOW));

    expect(store.kind).toBe('memory');
    expect(store.counts().coachees).toBe(2);
    expect(store.counts().content_items).toBe(6);
    await store.close();
  });
});

describe('DexieStore extras', () => {
  it('reports its kind and counts', async () => {
    const store = new DexieStore(`cmw-test-counts-${(databaseCounter += 1)}`);
    await store.open();
    await store.replaceAll(seedDataset(NOW));

    expect(store.kind).toBe('indexeddb');
    expect(await store.counts()).toMatchObject({ coachees: 2, content_items: 6, pillars: 4 });

    await store.destroy();
  });
});

describe('openBestStore', () => {
  it('prefers IndexedDB when the browser provides it', async () => {
    const store = await openBestStore(`cmw-test-best-${(databaseCounter += 1)}`);
    expect(store.kind).toBe('indexeddb');
    await store.close();
  });

  it('degrades to memory rather than failing to boot', async () => {
    // Private browsing and locked-down WebViews genuinely do this. The app should
    // still open and simply not persist.
    const original = globalThis.indexedDB;
    try {
      Reflect.deleteProperty(globalThis, 'indexedDB');
      const store = await openBestStore();
      expect(store.kind).toBe('memory');
      await store.close();
    } finally {
      Object.defineProperty(globalThis, 'indexedDB', {
        value: original,
        configurable: true,
        writable: true,
      });
    }
  });
});
