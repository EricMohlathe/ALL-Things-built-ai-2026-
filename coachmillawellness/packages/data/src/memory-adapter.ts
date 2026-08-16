/**
 * In-memory store.
 *
 * Not only a test double: it is the store the app uses when IndexedDB is
 * unavailable (private browsing, a locked-down WebView) so the UI degrades to
 * "works but does not persist" instead of failing to boot. The Vault screen
 * reads `kind` and warns her when this is what she is running on.
 */

import { emptyDataset, type CmwDataset, type DatasetTable } from '@cmw/core';

import { DATASET_TABLES, keyOfRow } from './schema.js';
import type { DescribableStore, StoreKind } from './store.js';

export class MemoryStore implements DescribableStore {
  readonly kind: StoreKind = 'memory';

  private data: CmwDataset = emptyDataset();

  async open(): Promise<void> {
    // Nothing to open.
  }

  async load(): Promise<CmwDataset> {
    return structuredClone(this.data);
  }

  async put<T extends DatasetTable>(table: T, rows: CmwDataset[T]): Promise<void> {
    if (rows.length === 0) return;
    const existing: object[] = this.data[table];
    const byKey = new Map<string, object>(existing.map((row) => [keyOfRow(table, row), row]));
    for (const row of rows as object[]) {
      byKey.set(keyOfRow(table, row), structuredClone(row));
    }
    (this.data[table] as unknown[]) = [...byKey.values()];
  }

  async hardDelete(table: DatasetTable, keys: string[]): Promise<void> {
    const doomed = new Set(keys);
    const rows: object[] = this.data[table];
    (this.data[table] as unknown[]) = rows.filter((row) => !doomed.has(keyOfRow(table, row)));
  }

  async replaceAll(dataset: CmwDataset): Promise<void> {
    this.data = structuredClone(dataset);
  }

  async clear(): Promise<void> {
    this.data = emptyDataset();
  }

  async close(): Promise<void> {
    // Nothing to close.
  }

  /** Row counts per table, for the Vault screen. */
  counts(): Record<DatasetTable, number> {
    const out = {} as Record<DatasetTable, number>;
    for (const table of DATASET_TABLES) out[table] = this.data[table].length;
    return out;
  }
}
