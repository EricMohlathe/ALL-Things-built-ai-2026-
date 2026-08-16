/**
 * Storage schema (§3.2). One schema, four stores.
 *
 * The table names and primary keys declared here are shared by the Dexie
 * adapter, the in-memory adapter, the export format and — in P5 — the Supabase
 * migration. Adding an entity means touching this file and nothing else.
 */

import { DATASET_TABLES, type CmwDataset, type DatasetTable } from '@cmw/core';

export { DATASET_TABLES, type CmwDataset, type DatasetTable };

/**
 * Primary key per table. Everything is keyed by `id` except `settings`, which is
 * a key/value table and is keyed by `key`.
 */
export const PRIMARY_KEYS = {
  coachees: 'id',
  goals: 'id',
  sessions: 'id',
  session_element_scores: 'id',
  session_checklists: 'id',
  wheel_snapshots: 'id',
  action_items: 'id',
  pillars: 'id',
  content_items: 'id',
  inquiries: 'id',
  ai_runs: 'id',
  share_links: 'id',
  pulse_responses: 'id',
  nudges: 'id',
  settings: 'key',
} as const satisfies Record<DatasetTable, string>;

export function primaryKeyOf(table: DatasetTable): string {
  return PRIMARY_KEYS[table];
}

/**
 * Reads a row's primary key. Takes `object` rather than an indexable type so
 * adapters can pass entity rows straight in — the entity interfaces have no index
 * signature, and widening them at every call site would mean a cast per caller.
 */
export function keyOfRow(table: DatasetTable, row: object): string {
  return String((row as Record<string, unknown>)[primaryKeyOf(table)]);
}

/**
 * Dexie index declarations.
 *
 * Deliberately sparse. The app loads the whole dataset on boot — a solo
 * practice is thousands of rows, not millions — so indexes exist for the few
 * lookups that happen outside that snapshot, not as a reflex. Nullable columns
 * are left unindexed on purpose: IndexedDB omits rows with a null key from an
 * index, which turns "find the deleted ones" into a silently short answer.
 */
export const DEXIE_SCHEMA: Record<DatasetTable, string> = {
  coachees: 'id, status, updated_at',
  goals: 'id, coachee_id, status, updated_at',
  sessions: 'id, date, framework, updated_at, *participants',
  session_element_scores: 'id, session_id, coachee_id, element, updated_at',
  session_checklists: 'id, session_id, item, updated_at',
  wheel_snapshots: 'id, coachee_id, date, domain, [coachee_id+date], updated_at',
  action_items: 'id, coachee_id, status, updated_at',
  pillars: 'id, name, updated_at',
  content_items: 'id, status, platform, updated_at',
  inquiries: 'id, date, updated_at',
  ai_runs: 'id, kind, created_at',
  share_links: 'id, coachee_id, token, kind, updated_at',
  pulse_responses: 'id, coachee_id, date, updated_at',
  nudges: 'id, kind, scheduled_at, updated_at',
  settings: 'key, updated_at',
};

export const DATABASE_NAME = 'coachmillawellness';

/** Bump only alongside a Dexie `.version()` migration. */
export const DATABASE_VERSION = 1;

// ── Settings keys ─────────────────────────────────────────────────────────

/**
 * Settings are a key/value table, so the keys live here as constants rather
 * than as strings scattered through the UI.
 */
export const SETTING_KEYS = {
  theme: 'theme',
  wheelDomains: 'wheel_domains',
  questionBanks: 'question_banks',
  lastBackupAt: 'last_backup_at',
  onboardingComplete: 'onboarding_complete',
  /** Local-only. Never synced, never exported, never committed. */
  anthropicApiKey: 'anthropic_api_key',
  aiBudgetUsd: 'ai_budget_usd',
} as const;

/**
 * Keys excluded from export. The API key is the coach's own credential held on
 * her device (§6); putting it in a backup file she forwards over WhatsApp would
 * turn a safety net into a leak.
 */
export const UNEXPORTED_SETTING_KEYS: readonly string[] = [SETTING_KEYS.anthropicApiKey];
