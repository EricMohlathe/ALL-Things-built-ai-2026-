/**
 * Application state.
 *
 * One in-memory `CmwDataset` is the whole truth; every screen is a pure
 * function of it. Mutations follow the same shape without exception — update
 * memory first so the UI is instant, then persist. On a local-first product
 * there is no round trip to wait for, so making the user watch a spinner for a
 * checkbox would be a self-inflicted wound.
 *
 * Derived values are never stored. Adherence, checklists, coherence and risk all
 * come from `@cmw/core` at render time, so there is exactly one implementation of
 * each rule and no cache to go stale.
 */

import {
  DATASET_TABLES,
  emptyDataset,
  toIsoDate,
  toIsoDateTime,
  uuidv7,
  type ActionItem,
  type ChecklistItem,
  type ChecklistState,
  type Coachee,
  type CmwDataset,
  type ContentItem,
  type ContentStatus,
  type DatasetTable,
  type ElementKey,
  type Goal,
  type IsoDate,
  type Pillar,
  type Rating,
  type Session,
  type SessionElementScore,
  type SmarterFlags,
  type Uuid,
  type WheelSnapshot,
} from '@cmw/core';
import {
  SETTING_KEYS,
  backupFilename,
  exportJSON,
  keyOfRow,
  parseImport,
  seedDataset,
  type DescribableStore,
  type StoreKind,
} from '@cmw/data';
import { themeNames, type ThemeName } from '@cmw/tokens';
import { create } from 'zustand';

export interface Toast {
  id: string;
  tone: 'info' | 'success' | 'warn' | 'error';
  message: string;
}

export type Status = 'loading' | 'ready' | 'error';

interface CmwState {
  status: Status;
  error: string | null;
  storeKind: StoreKind | null;
  data: CmwDataset;
  theme: ThemeName;
  toasts: Toast[];

  init: (store: DescribableStore) => Promise<void>;
  toast: (tone: Toast['tone'], message: string) => void;
  dismissToast: (id: string) => void;
  setTheme: (theme: ThemeName) => void;

  // Coachees
  addCoachee: (input: { name: string; package?: string; contact?: string }) => Promise<Uuid>;
  updateCoachee: (id: Uuid, patch: Partial<Coachee>) => Promise<void>;
  removeCoachee: (id: Uuid) => Promise<void>;

  // Goals
  addGoal: (coacheeId: Uuid, statement: string) => Promise<Uuid>;
  updateGoal: (id: Uuid, patch: Partial<Goal>) => Promise<void>;
  toggleSmarter: (goalId: Uuid, flag: keyof SmarterFlags) => Promise<void>;
  removeGoal: (id: Uuid) => Promise<void>;

  // Sessions
  addSession: (input: Partial<Session> & { participants: Uuid[] }) => Promise<Uuid>;
  updateSession: (id: Uuid, patch: Partial<Session>) => Promise<void>;
  removeSession: (id: Uuid) => Promise<void>;
  rateElement: (
    sessionId: Uuid,
    coacheeId: Uuid,
    element: ElementKey,
    rating: Rating,
    notes?: string,
  ) => Promise<void>;
  clearElementRating: (sessionId: Uuid, coacheeId: Uuid, element: ElementKey) => Promise<void>;
  recordChecklist: (
    sessionId: Uuid,
    item: ChecklistItem,
    state: ChecklistState,
    notes?: string,
  ) => Promise<void>;
  toggleFlaggedDomain: (sessionId: Uuid, domain: string) => Promise<void>;

  // Actions
  addAction: (input: {
    coachee_id: Uuid;
    session_id?: Uuid;
    title: string;
    due_date?: IsoDate;
    review_date?: IsoDate;
  }) => Promise<Uuid>;
  updateAction: (id: Uuid, patch: Partial<ActionItem>) => Promise<void>;
  setActionStatus: (id: Uuid, status: ActionItem['status']) => Promise<void>;
  removeAction: (id: Uuid) => Promise<void>;

  // Wheel
  saveWheelSnapshot: (snapshot: WheelSnapshot) => Promise<void>;
  setWheelDomains: (domains: string[]) => Promise<void>;

  // Content
  addPillar: (input: { name: string; color: string; core_message: string }) => Promise<Uuid>;
  updatePillar: (id: Uuid, patch: Partial<Pillar>) => Promise<void>;
  removePillar: (id: Uuid) => Promise<void>;
  addContent: (input: Partial<ContentItem> & { title: string }) => Promise<Uuid>;
  updateContent: (id: Uuid, patch: Partial<ContentItem>) => Promise<void>;
  setContentStatus: (id: Uuid, status: ContentStatus) => Promise<void>;
  removeContent: (id: Uuid) => Promise<void>;

  // Vault
  exportBackup: () => string;
  importBackup: (json: string) => Promise<void>;
  loadSample: () => Promise<void>;
  clearAll: () => Promise<void>;
  markBackedUp: () => Promise<void>;
  setting: <T>(key: string, fallback: T) => T;
}

/** The live adapter. Held outside the store so it never lands in React state. */
let adapter: DescribableStore | null = null;

function now(): string {
  return toIsoDateTime(new Date());
}

/** Merges rows into a table by primary key, preserving order for existing rows. */
function mergeRows(table: DatasetTable, existing: readonly object[], incoming: readonly object[]) {
  const byKey = new Map<string, object>(existing.map((row) => [keyOfRow(table, row), row]));
  for (const row of incoming) byKey.set(keyOfRow(table, row), row);
  return [...byKey.values()];
}

export const useStore = create<CmwState>((set, get) => {
  /** Update memory, then persist. Both halves always happen together. */
  async function commit(table: DatasetTable, rows: readonly object[]): Promise<void> {
    if (rows.length === 0) return;
    set((state) => ({
      data: {
        ...state.data,
        [table]: mergeRows(table, state.data[table], rows),
      } as CmwDataset,
    }));
    try {
      await adapter?.put(table, rows as never);
    } catch (cause) {
      get().toast('error', `Could not save: ${describe(cause)}`);
    }
  }

  /** Soft delete — nothing is ever truly dropped (§3.1). */
  async function softDelete(table: DatasetTable, id: string): Promise<void> {
    const rows = get().data[table] as readonly object[];
    const row = rows.find((r) => keyOfRow(table, r) === id);
    if (!row) return;
    await commit(table, [{ ...row, deleted_at: now(), updated_at: now() }]);
  }

  async function patchRow(table: DatasetTable, id: string, patch: object): Promise<void> {
    const rows = get().data[table] as readonly object[];
    const row = rows.find((r) => keyOfRow(table, r) === id);
    if (!row) return;
    await commit(table, [{ ...row, ...patch, updated_at: now() }]);
  }

  async function putSetting(key: string, value: unknown): Promise<void> {
    await commit('settings', [{ key, value, updated_at: now() }]);
  }

  async function replaceEverything(dataset: CmwDataset): Promise<void> {
    set({ data: dataset });
    try {
      await adapter?.replaceAll(dataset);
    } catch (cause) {
      get().toast('error', `Could not write to storage: ${describe(cause)}`);
    }
  }

  return {
    status: 'loading',
    error: null,
    storeKind: null,
    data: emptyDataset(),
    theme: 'dawn',
    toasts: [],

    async init(store) {
      adapter = store;
      try {
        const data = await store.load();
        const stored = data.settings.find((s) => s.key === SETTING_KEYS.theme)?.value;
        const theme = themeNames.includes(stored as ThemeName) ? (stored as ThemeName) : 'dawn';
        set({ data, status: 'ready', storeKind: store.kind, theme });

        if (store.kind === 'memory') {
          // She needs to know this session will not survive a refresh.
          get().toast(
            'warn',
            'This browser is not letting the app store data, so nothing will be saved. Export a backup before you close the tab.',
          );
        }
      } catch (cause) {
        set({ status: 'error', error: describe(cause) });
      }
    },

    toast(tone, message) {
      const id = uuidv7();
      set((state) => ({ toasts: [...state.toasts, { id, tone, message }] }));
      // Errors stay until dismissed; everything else clears itself.
      if (tone !== 'error') {
        setTimeout(() => get().dismissToast(id), 5000);
      }
    },

    dismissToast(id) {
      set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }));
    },

    setTheme(theme) {
      set({ theme });
      void putSetting(SETTING_KEYS.theme, theme);
    },

    // ── Coachees ─────────────────────────────────────────────────────────
    async addCoachee(input) {
      const id = uuidv7();
      const coachee: Coachee = {
        id,
        name: input.name.trim(),
        status: 'active',
        start_date: toIsoDate(new Date()),
        tags: [],
        package: input.package?.trim() || null,
        contact: input.contact?.trim() || null,
        updated_at: now(),
      };
      await commit('coachees', [coachee]);
      return id;
    },

    updateCoachee: (id, patch) => patchRow('coachees', id, patch),
    removeCoachee: (id) => softDelete('coachees', id),

    // ── Goals ────────────────────────────────────────────────────────────
    async addGoal(coacheeId, statement) {
      const id = uuidv7();
      const goal: Goal = {
        id,
        coachee_id: coacheeId,
        statement: statement.trim(),
        // Nothing is assumed met. The flags exist to be earned deliberately —
        // pre-ticking them would defeat the gap the checklist is built to show.
        smarter: { S: false, M: false, A: false, R: false, T: false, E: false, Rw: false },
        status: 'open',
        updated_at: now(),
      };
      await commit('goals', [goal]);
      return id;
    },

    updateGoal: (id, patch) => patchRow('goals', id, patch),

    async toggleSmarter(goalId, flag) {
      const goal = get().data.goals.find((g) => g.id === goalId);
      if (!goal) return;
      await patchRow('goals', goalId, {
        smarter: { ...goal.smarter, [flag]: !goal.smarter[flag] },
      });
    },

    removeGoal: (id) => softDelete('goals', id),

    // ── Sessions ─────────────────────────────────────────────────────────
    async addSession(input) {
      const id = uuidv7();
      const session: Session = {
        id,
        date: input.date ?? toIsoDate(new Date()),
        duration_min: input.duration_min ?? 60,
        framework: input.framework ?? 'GROW',
        participants: input.participants,
        summary: input.summary ?? null,
        confidence: input.confidence ?? null,
        commitment: input.commitment ?? null,
        review_dates: input.review_dates ?? [],
        flagged_domains: input.flagged_domains ?? [],
        updated_at: now(),
      };
      await commit('sessions', [session]);
      return id;
    },

    updateSession: (id, patch) => patchRow('sessions', id, patch),
    removeSession: (id) => softDelete('sessions', id),

    async rateElement(sessionId, coacheeId, element, rating, notes) {
      const existing = get().data.session_element_scores.find(
        (s) =>
          s.session_id === sessionId &&
          s.coachee_id === coacheeId &&
          s.element === element &&
          !s.deleted_at,
      );

      const row: SessionElementScore = {
        id: existing?.id ?? uuidv7(),
        session_id: sessionId,
        coachee_id: coacheeId,
        element,
        rating,
        notes: notes ?? existing?.notes ?? null,
        evidence: existing?.evidence ?? null,
        updated_at: now(),
      };
      await commit('session_element_scores', [row]);
    },

    async clearElementRating(sessionId, coacheeId, element) {
      const existing = get().data.session_element_scores.find(
        (s) =>
          s.session_id === sessionId &&
          s.coachee_id === coacheeId &&
          s.element === element &&
          !s.deleted_at,
      );
      if (existing) await softDelete('session_element_scores', existing.id);
    },

    async recordChecklist(sessionId, item, state, notes) {
      const existing = get().data.session_checklists.find(
        (c) => c.session_id === sessionId && c.item === item && !c.deleted_at,
      );
      await commit('session_checklists', [
        {
          id: existing?.id ?? uuidv7(),
          session_id: sessionId,
          item,
          state,
          notes: notes ?? existing?.notes ?? null,
          updated_at: now(),
        },
      ]);
    },

    async toggleFlaggedDomain(sessionId, domain) {
      const session = get().data.sessions.find((s) => s.id === sessionId);
      if (!session) return;
      const flagged = new Set(session.flagged_domains ?? []);
      if (flagged.has(domain)) flagged.delete(domain);
      else flagged.add(domain);
      await patchRow('sessions', sessionId, { flagged_domains: [...flagged] });
    },

    // ── Actions ──────────────────────────────────────────────────────────
    async addAction(input) {
      const id = uuidv7();
      const action: ActionItem = {
        id,
        coachee_id: input.coachee_id,
        session_id: input.session_id ?? null,
        title: input.title.trim(),
        due_date: input.due_date ?? null,
        review_date: input.review_date ?? null,
        status: 'open',
        updated_at: now(),
      };
      await commit('action_items', [action]);
      return id;
    },

    updateAction: (id, patch) => patchRow('action_items', id, patch),

    setActionStatus: (id, status) =>
      patchRow('action_items', id, {
        status,
        // Completion time is recorded when it happens and cleared when undone,
        // so a reopened action does not keep claiming it was finished.
        completed_at: status === 'done' ? now() : null,
      }),

    removeAction: (id) => softDelete('action_items', id),

    // ── Wheel ────────────────────────────────────────────────────────────
    async saveWheelSnapshot(snapshot) {
      const existing = get().data.wheel_snapshots.filter(
        (r) => r.coachee_id === snapshot.coachee_id && r.date === snapshot.date && !r.deleted_at,
      );
      const byDomain = new Map(existing.map((r) => [r.domain, r]));

      // Re-scoring a date updates the ten rows in place rather than stacking a
      // second snapshot on the same day.
      const rows = snapshot.domains.map((d) => ({
        id: byDomain.get(d.domain)?.id ?? uuidv7(),
        coachee_id: snapshot.coachee_id,
        date: snapshot.date,
        domain: d.domain,
        score: d.score,
        target: d.target,
        updated_at: now(),
      }));

      await commit('wheel_snapshots', rows);

      // A domain removed from the wheel is retired from this snapshot too.
      const kept = new Set(snapshot.domains.map((d) => d.domain));
      for (const row of existing) {
        if (!kept.has(row.domain)) await softDelete('wheel_snapshots', row.id);
      }
    },

    setWheelDomains: (domains) => putSetting(SETTING_KEYS.wheelDomains, domains),

    // ── Content ──────────────────────────────────────────────────────────
    async addPillar(input) {
      const id = uuidv7();
      await commit('pillars', [
        {
          id,
          name: input.name.trim(),
          color: input.color,
          core_message: input.core_message.trim(),
          keywords: [],
          updated_at: now(),
        },
      ]);
      return id;
    },

    updatePillar: (id, patch) => patchRow('pillars', id, patch),
    removePillar: (id) => softDelete('pillars', id),

    async addContent(input) {
      const id = uuidv7();
      const item: ContentItem = {
        id,
        title: input.title.trim(),
        type: input.type ?? 'Reel',
        platform: input.platform ?? 'IG',
        pillar_id: input.pillar_id ?? null,
        status: input.status ?? 'idea',
        hook: input.hook ?? null,
        cta: input.cta ?? null,
        script: input.script ?? null,
        publish_date: input.publish_date ?? null,
        link: input.link ?? null,
        metrics: input.metrics ?? null,
        updated_at: now(),
      };
      await commit('content_items', [item]);
      return id;
    },

    updateContent: (id, patch) => patchRow('content_items', id, patch),

    async setContentStatus(id, status) {
      const item = get().data.content_items.find((c) => c.id === id);
      if (!item) return;
      // Reaching "posted" without a date would make it invisible to the
      // coherence map, which counts published work by date.
      const publishDate =
        (status === 'posted' || status === 'analyzed') && !item.publish_date
          ? toIsoDate(new Date())
          : item.publish_date;
      await patchRow('content_items', id, { status, publish_date: publishDate });
    },

    removeContent: (id) => softDelete('content_items', id),

    // ── Vault ────────────────────────────────────────────────────────────
    exportBackup() {
      return exportJSON(get().data, { now: now() });
    },

    async importBackup(json) {
      const result = parseImport(json);
      await replaceEverything(result.dataset);
      for (const warning of result.warnings.slice(0, 3)) get().toast('warn', warning);
      const total = DATASET_TABLES.reduce((n, t) => n + result.dataset[t].length, 0);
      get().toast('success', `Restored ${total} records from ${backupFilename(new Date())}.`);
    },

    async loadSample() {
      await replaceEverything(seedDataset(new Date()));
      get().toast('success', 'Sample practice loaded — two coachees, four sessions, six posts.');
    },

    async clearAll() {
      set({ data: emptyDataset() });
      try {
        await adapter?.clear();
        get().toast('success', 'Everything cleared.');
      } catch (cause) {
        get().toast('error', `Could not clear storage: ${describe(cause)}`);
      }
    },

    markBackedUp: () => putSetting(SETTING_KEYS.lastBackupAt, now()),

    setting<T>(key: string, fallback: T): T {
      const found = get().data.settings.find((s) => s.key === key);
      return found === undefined || found.value === null ? fallback : (found.value as T);
    },
  };
});

function describe(cause: unknown): string {
  return cause instanceof Error ? cause.message : String(cause);
}

// ── Selectors ─────────────────────────────────────────────────────────────
// Kept as plain functions over the dataset so they compose and stay testable.

export function liveCoachees(data: CmwDataset): Coachee[] {
  return data.coachees
    .filter((c) => !c.deleted_at)
    .sort((a, b) => statusRank(a) - statusRank(b) || a.name.localeCompare(b.name));
}

function statusRank(coachee: Coachee): number {
  return coachee.status === 'active' ? 0 : coachee.status === 'paused' ? 1 : 2;
}

export function coacheeById(data: CmwDataset, id: Uuid): Coachee | undefined {
  return data.coachees.find((c) => c.id === id && !c.deleted_at);
}

export function goalsFor(data: CmwDataset, coacheeId: Uuid): Goal[] {
  return data.goals.filter((g) => g.coachee_id === coacheeId && !g.deleted_at);
}

export function sessionsFor(data: CmwDataset, coacheeId: Uuid): Session[] {
  return data.sessions
    .filter((s) => s.participants.includes(coacheeId) && !s.deleted_at)
    .sort((a, b) => b.date.localeCompare(a.date));
}

export function allSessions(data: CmwDataset): Session[] {
  return data.sessions.filter((s) => !s.deleted_at).sort((a, b) => b.date.localeCompare(a.date));
}

export function actionsFor(data: CmwDataset, coacheeId: Uuid): ActionItem[] {
  return data.action_items.filter((a) => a.coachee_id === coacheeId && !a.deleted_at);
}

export function liveActions(data: CmwDataset): ActionItem[] {
  return data.action_items.filter((a) => !a.deleted_at);
}

export function livePillars(data: CmwDataset): Pillar[] {
  return data.pillars.filter((p) => !p.deleted_at);
}

export function liveContent(data: CmwDataset): ContentItem[] {
  return data.content_items.filter((c) => !c.deleted_at);
}

export function wheelRowsFor(data: CmwDataset, coacheeId: Uuid) {
  return data.wheel_snapshots.filter((r) => r.coachee_id === coacheeId && !r.deleted_at);
}

export function scoresFor(data: CmwDataset, sessionId: Uuid): SessionElementScore[] {
  return data.session_element_scores.filter((s) => s.session_id === sessionId && !s.deleted_at);
}
