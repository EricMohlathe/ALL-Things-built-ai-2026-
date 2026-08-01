/**
 * @cmw/data — persistence, transfer and sample data.
 *
 * The `DataStore` contract is the only thing the UI knows about. Which adapter
 * is behind it (IndexedDB now, SQLite and Supabase later) is a boot-time choice,
 * which is what keeps §3.2's storage mapping from leaking into screens.
 */

export {
  DATABASE_NAME,
  DATABASE_VERSION,
  DATASET_TABLES,
  DEXIE_SCHEMA,
  PRIMARY_KEYS,
  SETTING_KEYS,
  UNEXPORTED_SETTING_KEYS,
  keyOfRow,
  primaryKeyOf,
  type CmwDataset,
  type DatasetTable,
} from './schema.js';

export type { DataStore, DescribableStore, StoreKind } from './store.js';

export { MemoryStore } from './memory-adapter.js';
export { DexieStore, openBestStore, keyFor } from './dexie-adapter.js';

export {
  BACKUP_INTERVAL_DAYS,
  EXPORT_FORMAT,
  EXPORT_VERSION,
  ImportError,
  backupFilename,
  backupStatus,
  datasetToCsv,
  exportJSON,
  importJSON,
  parseImport,
  toCsv,
  type BackupStatus,
  type ExportEnvelope,
  type ExportOptions,
  type ImportResult,
} from './transfer.js';

export { seedDataset } from './seed.js';

export {
  BACKOFF_BASE_MS,
  BACKOFF_CAP_MS,
  MemoryRemote,
  Outbox,
  SyncEngine,
  backoffMs,
  canonicalJson,
  lwwCompare,
  mergeRow,
  type ConflictEntry,
  type ConflictWinner,
  type MergeOutcome,
  type OutboxEntry,
  type RemoteAdapter,
  type SyncOptions,
  type SyncResult,
  type SyncRow,
} from './sync.js';
