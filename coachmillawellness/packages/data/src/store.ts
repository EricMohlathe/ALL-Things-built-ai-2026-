/**
 * The persistence contract.
 *
 * Every target implements this and nothing above it knows which one is in play:
 * Dexie/IndexedDB for Build 1 and the browser, SQLite for desktop and mobile,
 * Supabase for the hosted web app. §3.2's storage mapping becomes a matter of
 * choosing an adapter at boot.
 *
 * The shape is deliberately snapshot-oriented — `load()` returns the whole
 * dataset — because this is a single-user product with a few thousand rows. That
 * makes the UI a pure function of one in-memory value, and it makes offline the
 * default rather than a feature.
 */

import type { CmwDataset, DatasetTable } from '@cmw/core';

export interface DataStore {
  /** Resolves once the underlying store is open and migrated. */
  open(): Promise<void>;

  /** Everything, including soft-deleted rows — filtering is the caller's job. */
  load(): Promise<CmwDataset>;

  /** Insert or replace rows by primary key. */
  put<T extends DatasetTable>(table: T, rows: CmwDataset[T]): Promise<void>;

  /** Hard delete by primary key. Ordinary deletion is a soft delete via `put`. */
  hardDelete(table: DatasetTable, keys: string[]): Promise<void>;

  /** Atomically replace the entire contents — the import path. */
  replaceAll(dataset: CmwDataset): Promise<void>;

  /** Remove everything. Used by import and by the tests. */
  clear(): Promise<void>;

  close(): Promise<void>;
}

/** Identifies which adapter is running, for diagnostics and the Vault screen. */
export type StoreKind = 'indexeddb' | 'memory' | 'sqlite' | 'supabase';

export interface DescribableStore extends DataStore {
  readonly kind: StoreKind;
}
