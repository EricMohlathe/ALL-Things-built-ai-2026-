/**
 * Export and import — §6's safety net and gate G2.
 *
 * "Local-first, hers forever" is only true if she can get everything out and put
 * it back. This module is therefore held to a stricter standard than deep
 * equality: the serialisation is deterministic, so exporting the same state twice
 * produces byte-identical files, and export → wipe → import round-trips exactly.
 *
 * Determinism comes from sorting table rows by primary key and object keys
 * alphabetically. Arrays *inside* a row are left alone — `review_dates`,
 * `participants` and `actions_done` carry meaning in their order.
 */

import { DATASET_TABLES, emptyDataset, type CmwDataset, type DatasetTable } from '@cmw/core';

import { UNEXPORTED_SETTING_KEYS, keyOfRow, primaryKeyOf } from './schema.js';

export const EXPORT_FORMAT = 'coachmillawellness.export';
export const EXPORT_VERSION = 1;

export interface ExportEnvelope {
  format: typeof EXPORT_FORMAT;
  version: number;
  exported_at: string;
  app_version: string;
  counts: Record<string, number>;
  dataset: CmwDataset;
}

export interface ExportOptions {
  /** Injected so a test can assert on an exact file. */
  now?: string;
  appVersion?: string;
  /** Include the locally-held API key. Off by default, and never on for a file she shares. */
  includeSecrets?: boolean;
}

// ── Deterministic serialisation ───────────────────────────────────────────

type Json = string | number | boolean | null | Json[] | { [key: string]: Json };

function sortKeysDeep(value: unknown): Json {
  if (value === null || value === undefined) return null;
  if (Array.isArray(value)) return value.map(sortKeysDeep);
  if (typeof value === 'object') {
    const source = value as Record<string, unknown>;
    const out: Record<string, Json> = {};
    for (const key of Object.keys(source).sort()) {
      if (source[key] === undefined) continue; // JSON drops these anyway.
      out[key] = sortKeysDeep(source[key]);
    }
    return out;
  }
  if (typeof value === 'number' || typeof value === 'boolean' || typeof value === 'string') {
    return value;
  }
  throw new TypeError(`Cannot serialise a ${typeof value} into an export file`);
}

function sortedRows(table: DatasetTable, rows: readonly unknown[]): Json[] {
  return [...(rows as Array<Record<string, unknown>>)]
    .sort((a, b) => keyOfRow(table, a).localeCompare(keyOfRow(table, b)))
    .map(sortKeysDeep);
}

/** Strips the local-only credential unless explicitly asked to keep it. */
function exportableDataset(dataset: CmwDataset, includeSecrets: boolean): CmwDataset {
  if (includeSecrets) return dataset;
  return {
    ...dataset,
    settings: dataset.settings.filter((s) => !UNEXPORTED_SETTING_KEYS.includes(s.key)),
  };
}

export function exportJSON(dataset: CmwDataset, options: ExportOptions = {}): string {
  const source = exportableDataset(dataset, options.includeSecrets ?? false);

  const tables: Record<string, Json[]> = {};
  const counts: Record<string, number> = {};
  for (const table of DATASET_TABLES) {
    tables[table] = sortedRows(table, source[table]);
    counts[table] = source[table].length;
  }

  const envelope = {
    format: EXPORT_FORMAT,
    version: EXPORT_VERSION,
    exported_at: options.now ?? new Date().toISOString(),
    app_version: options.appVersion ?? '1.0.0',
    counts,
    dataset: tables,
  };

  return `${JSON.stringify(envelope, null, 2)}\n`;
}

// ── Import ────────────────────────────────────────────────────────────────

export interface ImportResult {
  dataset: CmwDataset;
  /** Recoverable oddities, surfaced to her rather than swallowed. */
  warnings: string[];
  meta: { exported_at: string | null; app_version: string | null; version: number };
}

export class ImportError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ImportError';
  }
}

/**
 * Parses and validates a backup file.
 *
 * Strict on structure, forgiving on absence. A missing table is filled empty
 * with a warning — an older export predating an entity should still restore. A
 * malformed *row* is an error, because silently dropping a session from a
 * restore is the one failure she would never notice.
 */
export function parseImport(json: string): ImportResult {
  let parsed: unknown;
  try {
    parsed = JSON.parse(json);
  } catch (cause) {
    throw new ImportError(
      `That file is not valid JSON. ${cause instanceof Error ? cause.message : ''}`.trim(),
    );
  }

  if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new ImportError('That file does not look like a CoachMillaWellness backup.');
  }

  const envelope = parsed as Record<string, unknown>;

  if (envelope.format !== EXPORT_FORMAT) {
    throw new ImportError(
      `That file does not look like a CoachMillaWellness backup (found format "${String(
        envelope.format ?? 'none',
      )}").`,
    );
  }

  const version = typeof envelope.version === 'number' ? envelope.version : 0;
  if (version > EXPORT_VERSION) {
    throw new ImportError(
      `This backup was written by a newer version of the app (format ${version}, this build reads ${EXPORT_VERSION}). Update first, then import.`,
    );
  }

  const rawDataset = envelope.dataset;
  if (rawDataset === null || typeof rawDataset !== 'object' || Array.isArray(rawDataset)) {
    throw new ImportError('The backup is missing its data.');
  }

  const source = rawDataset as Record<string, unknown>;
  const dataset = emptyDataset();
  const warnings: string[] = [];

  for (const table of DATASET_TABLES) {
    const rows = source[table];
    if (rows === undefined) {
      warnings.push(`No "${table}" in this backup — restored as empty.`);
      continue;
    }
    if (!Array.isArray(rows)) {
      throw new ImportError(`"${table}" should be a list of rows, but it is not.`);
    }

    const key = primaryKeyOf(table);
    rows.forEach((row, index) => {
      if (row === null || typeof row !== 'object' || Array.isArray(row)) {
        throw new ImportError(`"${table}" row ${index + 1} is not a record.`);
      }
      const value = (row as Record<string, unknown>)[key];
      if (typeof value !== 'string' || value === '') {
        throw new ImportError(`"${table}" row ${index + 1} is missing its "${key}".`);
      }
    });

    const seen = new Set<string>();
    const deduped = (rows as Array<Record<string, unknown>>).filter((row) => {
      const value = String(row[key]);
      if (seen.has(value)) {
        warnings.push(`Duplicate "${table}" entry ${value} — kept the first.`);
        return false;
      }
      seen.add(value);
      return true;
    });

    (dataset[table] as unknown[]) = deduped;
  }

  const unknownTables = Object.keys(source).filter(
    (name) => !(DATASET_TABLES as readonly string[]).includes(name),
  );
  for (const name of unknownTables) {
    warnings.push(`Ignored unrecognised table "${name}".`);
  }

  return {
    dataset,
    warnings,
    meta: {
      exported_at: typeof envelope.exported_at === 'string' ? envelope.exported_at : null,
      app_version: typeof envelope.app_version === 'string' ? envelope.app_version : null,
      version,
    },
  };
}

/** Convenience wrapper for the happy path. */
export function importJSON(json: string): CmwDataset {
  return parseImport(json).dataset;
}

// ── CSV ───────────────────────────────────────────────────────────────────

/**
 * CSV export, RFC 4180.
 *
 * DECISION: CSV is a read-only view, and JSON is the round-trip format. CSV
 * cannot represent the nested fields — SMARTER flags, content metrics, a Pulse
 * mini-wheel — without inventing an encoding, and an import that quietly dropped
 * a goal's Exciting flag would be worse than having no CSV import at all. So this
 * exists for opening her data in Excel, and §2 M7's full round-trip obligation is
 * met by JSON.
 */
export function toCsv(rows: ReadonlyArray<Record<string, unknown>>): string {
  if (rows.length === 0) return '';

  // Columns in first-seen order, then anything extra alphabetically, so the
  // header is stable across exports.
  const firstSeen: string[] = [];
  const extras = new Set<string>();
  rows.forEach((row, index) => {
    for (const key of Object.keys(row)) {
      if (index === 0) firstSeen.push(key);
      else if (!firstSeen.includes(key)) extras.add(key);
    }
  });
  const columns = [...firstSeen, ...[...extras].sort()];

  const lines = [columns.map(csvCell).join(',')];
  for (const row of rows) {
    lines.push(columns.map((column) => csvCell(row[column])).join(','));
  }
  return `${lines.join('\r\n')}\r\n`;
}

function csvCell(value: unknown): string {
  if (value === null || value === undefined) return '';
  const text =
    typeof value === 'object' ? JSON.stringify(value) : String(value as string | number | boolean);
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

/** One CSV per table, ready to zip or write out individually. */
export function datasetToCsv(dataset: CmwDataset): Record<DatasetTable, string> {
  const out = {} as Record<DatasetTable, string>;
  for (const table of DATASET_TABLES) {
    out[table] = toCsv(
      sortedRows(table, dataset[table]) as unknown as Array<Record<string, unknown>>,
    );
  }
  return out;
}

// ── Backup discipline ─────────────────────────────────────────────────────

export const BACKUP_INTERVAL_DAYS = 14;

export interface BackupStatus {
  last_backup_at: string | null;
  days_since: number | null;
  /** The §6 auto-reminder: nudge her every 14 days. */
  due: boolean;
  /** Never backed up at all — a different, louder message than "it has been a while". */
  never: boolean;
}

/** Drives the 14-day backup nudge (§6 safety net, gate G8). */
export function backupStatus(lastBackupAt: string | null, now: Date = new Date()): BackupStatus {
  if (!lastBackupAt) {
    return { last_backup_at: null, days_since: null, due: true, never: true };
  }
  const then = Date.parse(lastBackupAt);
  if (Number.isNaN(then)) {
    return { last_backup_at: lastBackupAt, days_since: null, due: true, never: true };
  }
  const days = Math.floor((now.getTime() - then) / 86_400_000);
  return {
    last_backup_at: lastBackupAt,
    days_since: days,
    due: days >= BACKUP_INTERVAL_DAYS,
    never: false,
  };
}

/** `CoachMillaWellness-backup-2026-07-30.json` — sorts chronologically in a folder. */
export function backupFilename(now: Date = new Date()): string {
  return `CoachMillaWellness-backup-${now.toISOString().slice(0, 10)}.json`;
}
