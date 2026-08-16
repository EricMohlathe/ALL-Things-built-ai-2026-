import { emptyDataset, type CmwDataset } from '@cmw/core';
import { describe, expect, it } from 'vitest';

import { SETTING_KEYS } from '../schema.js';
import { seedDataset } from '../seed.js';
import {
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
} from '../transfer.js';

const NOW = new Date('2026-07-30T10:00:00.000Z');

describe('exportJSON', () => {
  it('wraps the data in an identifiable envelope', () => {
    const envelope = JSON.parse(exportJSON(seedDataset(NOW), { now: NOW.toISOString() }));

    expect(envelope.format).toBe(EXPORT_FORMAT);
    expect(envelope.version).toBe(EXPORT_VERSION);
    expect(envelope.exported_at).toBe(NOW.toISOString());
    expect(envelope.counts.coachees).toBe(2);
    expect(envelope.dataset.coachees).toHaveLength(2);
  });

  it('is byte-for-byte deterministic for the same state', () => {
    // Gate G2 in its strictest reading. Determinism also means she can diff two
    // backups and see what actually changed.
    const dataset = seedDataset(NOW);
    const first = exportJSON(dataset, { now: NOW.toISOString() });
    const second = exportJSON(structuredClone(dataset), { now: NOW.toISOString() });
    expect(first).toBe(second);
  });

  it('does not depend on the order rows happen to sit in memory', () => {
    const dataset = seedDataset(NOW);
    const shuffled: CmwDataset = {
      ...structuredClone(dataset),
      coachees: [...dataset.coachees].reverse(),
      content_items: [...dataset.content_items].reverse(),
    };

    expect(exportJSON(shuffled, { now: NOW.toISOString() })).toBe(
      exportJSON(dataset, { now: NOW.toISOString() }),
    );
  });

  it('preserves the order of arrays inside a row', () => {
    // `review_dates` and `participants` mean something in sequence, so sorting
    // them would quietly corrupt the record even though the file still parsed.
    const dataset = emptyDataset();
    dataset.sessions = [
      {
        id: 's1',
        date: '2026-07-15',
        duration_min: 60,
        framework: 'GROW',
        participants: ['zz-second', 'aa-first'],
        review_dates: ['2026-08-05', '2026-07-29'],
        updated_at: NOW.toISOString(),
      },
    ];

    const restored = importJSON(exportJSON(dataset, { now: NOW.toISOString() }));
    expect(restored.sessions[0]!.participants).toEqual(['zz-second', 'aa-first']);
    expect(restored.sessions[0]!.review_dates).toEqual(['2026-08-05', '2026-07-29']);
  });

  it('leaves her API key out of the file by default', () => {
    const dataset = emptyDataset();
    dataset.settings = [
      { key: SETTING_KEYS.anthropicApiKey, value: 'sk-ant-secret', updated_at: NOW.toISOString() },
      { key: SETTING_KEYS.theme, value: 'dawn', updated_at: NOW.toISOString() },
    ];

    const json = exportJSON(dataset, { now: NOW.toISOString() });
    expect(json).not.toContain('sk-ant-secret');
    expect(importJSON(json).settings.map((s) => s.key)).toEqual([SETTING_KEYS.theme]);
  });

  it('can be asked to include secrets for a private encrypted backup', () => {
    const dataset = emptyDataset();
    dataset.settings = [
      { key: SETTING_KEYS.anthropicApiKey, value: 'sk-ant-secret', updated_at: NOW.toISOString() },
    ];
    expect(exportJSON(dataset, { includeSecrets: true })).toContain('sk-ant-secret');
  });

  it('ends with a newline so the file behaves in a text editor', () => {
    expect(exportJSON(emptyDataset())).toMatch(/\n$/);
  });

  it('refuses to serialise something that is not data', () => {
    const dataset = emptyDataset();
    dataset.settings = [
      { key: 'broken', value: () => 'nope', updated_at: NOW.toISOString() } as never,
    ];
    expect(() => exportJSON(dataset)).toThrow(TypeError);
  });

  it('defaults its timestamp and version', () => {
    const envelope = JSON.parse(exportJSON(emptyDataset()));
    expect(envelope.exported_at).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    expect(envelope.app_version).toBe('1.0.0');
  });
});

/**
 * Export normalises row order by primary key — that is what makes the file
 * deterministic. So a restored dataset holds the same rows, not the same array
 * order, and comparing round trips means comparing canonically.
 */
function canonical(dataset: CmwDataset): CmwDataset {
  const out = structuredClone(dataset);
  for (const table of Object.keys(out) as Array<keyof CmwDataset>) {
    const key = table === 'settings' ? 'key' : 'id';
    const rows: object[] = out[table];
    rows.sort((a, b) =>
      String((a as Record<string, unknown>)[key]).localeCompare(
        String((b as Record<string, unknown>)[key]),
      ),
    );
  }
  return out;
}

describe('round trip — gate G2', () => {
  it('restores every row of the seeded dataset', () => {
    const original = seedDataset(NOW);
    const restored = importJSON(exportJSON(original, { now: NOW.toISOString() }));

    expect(canonical(restored)).toEqual(canonical(original));
  });

  it('loses nothing — every table comes back at full count', () => {
    const original = seedDataset(NOW);
    const restored = importJSON(exportJSON(original, { now: NOW.toISOString() }));

    for (const table of Object.keys(original) as Array<keyof CmwDataset>) {
      expect(restored[table].length, table).toBe(original[table].length);
    }
  });

  it('re-exports to the identical file after a round trip', () => {
    const original = seedDataset(NOW);
    const once = exportJSON(original, { now: NOW.toISOString() });
    const twice = exportJSON(importJSON(once), { now: NOW.toISOString() });
    expect(twice).toBe(once);
  });

  it('round-trips an empty dataset', () => {
    expect(importJSON(exportJSON(emptyDataset()))).toEqual(emptyDataset());
  });

  it('keeps nested values intact', () => {
    const original = seedDataset(NOW);
    const restored = importJSON(exportJSON(original, { now: NOW.toISOString() }));

    const goal = restored.goals.find((g) => !g.smarter.E)!;
    expect(goal.smarter).toEqual({ S: true, M: true, A: true, R: true, T: true, E: false, Rw: false });
    expect(restored.content_items[0]!.metrics).toEqual({
      views: 8400,
      likes: 612,
      saves: 214,
      comments: 38,
    });
  });
});

describe('parseImport', () => {
  function envelope(overrides: Record<string, unknown> = {}): string {
    return JSON.stringify({
      format: EXPORT_FORMAT,
      version: EXPORT_VERSION,
      exported_at: NOW.toISOString(),
      app_version: '1.0.0',
      dataset: { coachees: [] },
      ...overrides,
    });
  }

  it('reports what it found', () => {
    const result = parseImport(envelope());
    expect(result.meta).toEqual({
      exported_at: NOW.toISOString(),
      app_version: '1.0.0',
      version: EXPORT_VERSION,
    });
  });

  it('fills a missing table and says so rather than failing', () => {
    // An older backup predating an entity should still restore.
    const result = parseImport(envelope({ dataset: { coachees: [] } }));
    expect(result.dataset.pillars).toEqual([]);
    expect(result.warnings.some((w) => w.includes('pillars'))).toBe(true);
  });

  it('ignores a table it does not recognise', () => {
    const result = parseImport(envelope({ dataset: { coachees: [], invented_table: [] } }));
    expect(result.warnings.some((w) => w.includes('invented_table'))).toBe(true);
  });

  it('drops a duplicate row and keeps the first', () => {
    const result = parseImport(
      envelope({
        dataset: {
          coachees: [
            { id: 'a', name: 'First', updated_at: NOW.toISOString() },
            { id: 'a', name: 'Second', updated_at: NOW.toISOString() },
          ],
        },
      }),
    );
    expect(result.dataset.coachees).toHaveLength(1);
    expect(result.dataset.coachees[0]!.name).toBe('First');
    expect(result.warnings.some((w) => w.includes('Duplicate'))).toBe(true);
  });

  it('rejects a file that is not JSON', () => {
    expect(() => parseImport('this is not json')).toThrow(ImportError);
    expect(() => parseImport('this is not json')).toThrow(/not valid JSON/);
  });

  it('rejects a file that is not a backup', () => {
    expect(() => parseImport('[]')).toThrow(/does not look like/);
    expect(() => parseImport('null')).toThrow(/does not look like/);
    expect(() => parseImport(JSON.stringify({ hello: 'world' }))).toThrow(/does not look like/);
  });

  it('refuses a backup from a newer version of the app', () => {
    // Silently ignoring fields it does not understand would lose her data on the
    // next export, so this stops instead and tells her to update.
    expect(() => parseImport(envelope({ version: EXPORT_VERSION + 1 }))).toThrow(
      /newer version of the app/,
    );
  });

  it('accepts a backup from an older version', () => {
    expect(parseImport(envelope({ version: 0 })).meta.version).toBe(0);
  });

  it('rejects a backup with no data', () => {
    expect(() => parseImport(envelope({ dataset: undefined }))).toThrow(/missing its data/);
    expect(() => parseImport(envelope({ dataset: 'nope' }))).toThrow(/missing its data/);
    expect(() => parseImport(envelope({ dataset: [] }))).toThrow(/missing its data/);
  });

  it('rejects a table that is not a list', () => {
    expect(() => parseImport(envelope({ dataset: { coachees: {} } }))).toThrow(
      /should be a list of rows/,
    );
  });

  it('rejects a malformed row rather than dropping it', () => {
    // The one failure she would never notice: a session missing from a restore.
    expect(() => parseImport(envelope({ dataset: { coachees: ['nope'] } }))).toThrow(
      /row 1 is not a record/,
    );
    expect(() => parseImport(envelope({ dataset: { coachees: [null] } }))).toThrow(
      /row 1 is not a record/,
    );
    expect(() => parseImport(envelope({ dataset: { coachees: [{ name: 'No id' }] } }))).toThrow(
      /row 1 is missing its "id"/,
    );
    expect(() => parseImport(envelope({ dataset: { coachees: [{ id: '' }] } }))).toThrow(
      /missing its "id"/,
    );
    expect(() => parseImport(envelope({ dataset: { coachees: [{ id: 7 }] } }))).toThrow(
      /missing its "id"/,
    );
  });

  it('keys settings by key rather than id', () => {
    const result = parseImport(
      envelope({ dataset: { settings: [{ key: 'theme', value: 'morning' }] } }),
    );
    expect(result.dataset.settings[0]!.key).toBe('theme');
  });

  it('reports missing envelope metadata as absent rather than guessing', () => {
    const result = parseImport(
      JSON.stringify({ format: EXPORT_FORMAT, version: 1, dataset: { coachees: [] } }),
    );
    expect(result.meta.exported_at).toBeNull();
    expect(result.meta.app_version).toBeNull();
  });

  it('treats a missing version as the oldest format', () => {
    const result = parseImport(
      JSON.stringify({ format: EXPORT_FORMAT, dataset: { coachees: [] } }),
    );
    expect(result.meta.version).toBe(0);
  });
});

describe('CSV export', () => {
  it('writes a header and one row per record', () => {
    const csv = toCsv([
      { id: 'a', name: 'Naledi M.', score: 7 },
      { id: 'b', name: 'Thabo K.', score: 5 },
    ]);
    expect(csv).toBe('id,name,score\r\na,Naledi M.,7\r\nb,Thabo K.,5\r\n');
  });

  it('quotes and escapes per RFC 4180', () => {
    const csv = toCsv([{ note: 'She said "start now", then left', list: 'a,b', wrapped: 'one\ntwo' }]);
    expect(csv).toContain('"She said ""start now"", then left"');
    expect(csv).toContain('"a,b"');
    expect(csv).toContain('"one\ntwo"');
  });

  it('renders nested values as JSON and blanks for absent ones', () => {
    const csv = toCsv([{ smarter: { S: true }, missing: null, absent: undefined }]);
    expect(csv).toContain('"{""S"":true}"');
    expect(csv.split('\r\n')[1]).toBe('"{""S"":true}",,');
  });

  it('keeps a stable header when later rows carry extra columns', () => {
    const csv = toCsv([{ id: 'a' }, { id: 'b', zeta: 1, alpha: 2 }]);
    expect(csv.split('\r\n')[0]).toBe('id,alpha,zeta');
  });

  it('has nothing to write for no rows', () => {
    expect(toCsv([])).toBe('');
  });

  it('produces one file per table', () => {
    const csvs = datasetToCsv(seedDataset(NOW));
    expect(csvs.coachees.split('\r\n')[0]).toContain('id');
    expect(csvs.coachees).toContain('Naledi M.');
    expect(csvs.ai_runs).toBe('');
  });
});

describe('backupStatus', () => {
  it('nudges when it has been two weeks', () => {
    const status = backupStatus('2026-07-16T10:00:00.000Z', NOW);
    expect(status.days_since).toBe(BACKUP_INTERVAL_DAYS);
    expect(status.due).toBe(true);
    expect(status.never).toBe(false);
  });

  it('stays quiet inside the window', () => {
    const status = backupStatus('2026-07-25T10:00:00.000Z', NOW);
    expect(status.days_since).toBe(5);
    expect(status.due).toBe(false);
  });

  it('treats never-backed-up as its own louder case', () => {
    expect(backupStatus(null, NOW)).toEqual({
      last_backup_at: null,
      days_since: null,
      due: true,
      never: true,
    });
  });

  it('treats an unreadable timestamp as never', () => {
    const status = backupStatus('not a date', NOW);
    expect(status.due).toBe(true);
    expect(status.never).toBe(true);
  });

  it('defaults to now', () => {
    expect(backupStatus(new Date().toISOString()).due).toBe(false);
  });

  it('names the file so backups sort by date in a folder', () => {
    expect(backupFilename(NOW)).toBe('CoachMillaWellness-backup-2026-07-30.json');
    expect(backupFilename()).toMatch(/^CoachMillaWellness-backup-\d{4}-\d{2}-\d{2}\.json$/);
  });
});
