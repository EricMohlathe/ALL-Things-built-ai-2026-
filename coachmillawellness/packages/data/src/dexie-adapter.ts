/**
 * IndexedDB store via Dexie — the Build 1 and browser adapter (§3.2).
 *
 * Note for anyone reading this next to the compendium: browser storage is
 * correct here. `CoachMillaWellness.html` runs in a real local browser from her
 * Files app, so IndexedDB is her actual database. The "no browser storage" rule
 * applies only to claude.ai artifact previews.
 */

import Dexie from 'dexie';
import { emptyDataset, type CmwDataset, type DatasetTable } from '@cmw/core';

import {
  DATABASE_NAME,
  DATABASE_VERSION,
  DATASET_TABLES,
  DEXIE_SCHEMA,
  keyOfRow,
} from './schema.js';
import type { DescribableStore, StoreKind } from './store.js';

/**
 * Built by function rather than by subclassing Dexie.
 *
 * `class CmwDexie extends Dexie` reads naturally but Dexie's class type is
 * self-referential, so every assignment of the subclass back to `Dexie` sends
 * the checker into an unbounded instantiation. The subclass was only ever
 * carrying a constructor call, so a factory says the same thing for less.
 */
function createDatabase(name: string): Dexie {
  const db = new Dexie(name);
  db.version(DATABASE_VERSION).stores(DEXIE_SCHEMA);
  return db;
}

/**
 * The five table operations this adapter uses, declared plainly.
 *
 * Dexie's own `Table<T, TKey, TInsertType>` is generic over a table name that
 * cannot be known statically, and instantiating it across a fifteen-table
 * dataset sends the checker into "excessively deep" territory. Naming the narrow
 * surface instead is both cheaper to check and a useful statement of exactly how
 * much of Dexie this adapter depends on — which is what a future SQLite or
 * Supabase adapter has to match.
 *
 * Row types are enforced at the `DataStore` boundary, so nothing is lost here.
 */
interface TableOps {
  toArray(): Promise<unknown[]>;
  bulkPut(items: readonly object[]): Promise<unknown>;
  bulkDelete(keys: readonly string[]): Promise<unknown>;
  clear(): Promise<unknown>;
  count(): Promise<number>;
}

function tableOf(db: Dexie, name: DatasetTable): TableOps {
  return db.table(name) as unknown as TableOps;
}

/**
 * Writes a table back onto the dataset. Indexing `CmwDataset` by the fifteen-way
 * table union makes the checker unfold every entity array at once, so the write
 * goes through a flat record type instead.
 */
function assignTable(dataset: CmwDataset, table: DatasetTable, rows: unknown[]): void {
  (dataset as unknown as Record<string, unknown[]>)[table] = rows;
}

/**
 * Dexie's `transaction` carries six overloads and a generic scope callback.
 * Resolving them against a fifteen-table dataset sends the checker into an
 * "excessively deep" instantiation, so the call is narrowed to the one signature
 * this adapter actually uses — every transaction here spans all tables and
 * resolves to void.
 */
type TransactionRunner = (
  mode: 'r' | 'rw',
  tables: readonly unknown[],
  scope: () => Promise<void>,
) => Promise<void>;

export class DexieStore implements DescribableStore {
  readonly kind: StoreKind = 'indexeddb';

  private db: Dexie;

  constructor(name: string = DATABASE_NAME) {
    this.db = createDatabase(name);
  }

  async open(): Promise<void> {
    await this.db.open();
  }

  /** Runs `work` in one transaction spanning every table. */
  private transact(mode: 'r' | 'rw', work: () => Promise<void>): Promise<void> {
    const run = this.db.transaction.bind(this.db) as unknown as TransactionRunner;
    return run(mode, this.db.tables, work);
  }

  async load(): Promise<CmwDataset> {
    const dataset = emptyDataset();
    // One transaction across every table, so a snapshot can never be half of
    // one write and half of another.
    await this.transact('r', async () => {
      for (const table of DATASET_TABLES) {
        assignTable(dataset, table, await tableOf(this.db, table).toArray());
      }
    });
    return dataset;
  }

  /**
   * Implemented non-generically on purpose. The `DataStore` contract keeps the
   * `<T extends DatasetTable>` form so call sites still get their rows checked
   * against the table they name; resolving that generic *inside* the adapter
   * buys nothing and is what pushes the checker over its instantiation limit.
   */
  async put(table: DatasetTable, rows: readonly object[]): Promise<void> {
    if (rows.length === 0) return;
    await tableOf(this.db, table).bulkPut(rows);
  }

  async hardDelete(table: DatasetTable, keys: string[]): Promise<void> {
    if (keys.length === 0) return;
    await tableOf(this.db, table).bulkDelete(keys);
  }

  async replaceAll(dataset: CmwDataset): Promise<void> {
    // One transaction for the whole import: a restore that fails partway would
    // otherwise leave her with neither the old data nor the new.
    await this.transact('rw', async () => {
      for (const table of DATASET_TABLES) {
        const target = tableOf(this.db, table);
        await target.clear();
        const rows: object[] = dataset[table];
        if (rows.length > 0) await target.bulkPut(rows);
      }
    });
  }

  async clear(): Promise<void> {
    await this.transact('rw', async () => {
      for (const table of DATASET_TABLES) {
        await tableOf(this.db, table).clear();
      }
    });
  }

  async close(): Promise<void> {
    this.db.close();
  }

  async counts(): Promise<Record<DatasetTable, number>> {
    const out = {} as Record<DatasetTable, number>;
    await Promise.all(
      DATASET_TABLES.map(async (table) => {
        out[table] = await tableOf(this.db, table).count();
      }),
    );
    return out;
  }

  /** Deletes the whole database file. The Vault's "start over" path. */
  async destroy(): Promise<void> {
    await this.db.delete();
  }
}

/**
 * Picks the best available store. IndexedDB when the browser will give it to us,
 * memory when it will not — the app should still open in private browsing, just
 * without persistence.
 */
export async function openBestStore(name?: string): Promise<DescribableStore> {
  const { MemoryStore } = await import('./memory-adapter.js');
  if (typeof indexedDB === 'undefined') return new MemoryStore();

  const store = new DexieStore(name);
  try {
    await store.open();
    return store;
  } catch {
    await store.close().catch(() => undefined);
    return new MemoryStore();
  }
}

export function keyFor(table: DatasetTable, row: Record<string, unknown>): string {
  return keyOfRow(table, row);
}
