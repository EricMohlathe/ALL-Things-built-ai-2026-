/**
 * M7 — VAULT & SETTINGS.
 *
 * "Local-first, hers forever" is a promise this screen has to keep. So the export
 * is one tap, the restore accepts a dropped file, and the 14-day nudge is loud
 * rather than polite — a backup she never takes is the same as no backup.
 *
 * The POPIA note is here on purpose (§13). She is processing other people's
 * personal information, and the honest version of that obligation belongs in the
 * product rather than only in a document she signed once.
 */

import {
  DATASET_TABLES,
  type AiRunKind,
  type CmwDataset,
  type DatasetTable,
} from '@cmw/core';
import {
  BACKUP_INTERVAL_DAYS,
  SETTING_KEYS,
  backupFilename,
  backupStatus,
  datasetToCsv,
  type StoreKind,
} from '@cmw/data';
import { themeNames, type ThemeName } from '@cmw/tokens';
import { AlertTriangle, Database, Download, ShieldCheck, Sparkles, Upload } from 'lucide-react';
import { useRef, useState } from 'react';

import { StatTile } from '../charts/index.js';
import { AI_MODELS_SETTING, modelOptions, useAiSettings, useCopilot } from '../app/copilot.js';
import { useStore } from '../app/store.js';
import {
  Button,
  Card,
  Chip,
  Modal,
  Numeric,
  PageHeader,
  Reveal,
  SectionHeader,
  Select,
  TextInput,
  cn,
} from '../primitives/index.js';
import { downloadText } from '../wheel/export.js';
import { BudgetMeter } from './Copilot.js';

const TABLE_LABELS: Partial<Record<DatasetTable, string>> = {
  coachees: 'Coachees',
  goals: 'Goals',
  sessions: 'Sessions',
  session_element_scores: 'Element scores',
  wheel_snapshots: 'Wheel rows',
  action_items: 'Actions',
  pillars: 'Pillars',
  content_items: 'Content',
};

export function Vault({
  data,
  storeKind,
  theme,
}: {
  data: CmwDataset;
  storeKind: StoreKind | null;
  theme: ThemeName;
}) {
  const fileInput = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [confirmClear, setConfirmClear] = useState(false);

  const lastBackup = useStore.getState().setting<string | null>(SETTING_KEYS.lastBackupAt, null);
  const backup = backupStatus(lastBackup);

  const totalRows = DATASET_TABLES.reduce((n, table) => n + data[table].length, 0);

  const exportJson = (): void => {
    const json = useStore.getState().exportBackup();
    downloadText(json, backupFilename(new Date()));
    void useStore.getState().markBackedUp();
    useStore.getState().toast('success', 'Backup downloaded. Keep it somewhere that is not this device.');
  };

  const exportCsv = (): void => {
    const csvs = datasetToCsv(data);
    // One file per table rather than a zip: no archive dependency, and she can
    // open exactly the sheet she wants.
    let written = 0;
    for (const table of DATASET_TABLES) {
      const csv = csvs[table];
      if (!csv) continue;
      downloadText(csv, `coachmillawellness-${table}.csv`, 'text/csv');
      written += 1;
    }
    useStore.getState().toast('success', `${written} CSV file${written === 1 ? '' : 's'} downloaded.`);
  };

  const restore = async (file: File): Promise<void> => {
    try {
      await useStore.getState().importBackup(await file.text());
    } catch (cause) {
      useStore
        .getState()
        .toast('error', cause instanceof Error ? cause.message : 'That file could not be read.');
    }
  };

  return (
    <div>
      <PageHeader
        eyebrow="Vault"
        title="Your data"
        subtitle="Everything lives on this device. Export it whenever you like, restore it anywhere, and take it with you if you ever stop using this app."
      />

      {/* The 14-day nudge (§6 safety net, gate G8). */}
      {backup.due ? (
        <Reveal>
          <Card className="mb-6 border-warn/50">
            <div className="flex items-start gap-3">
              <AlertTriangle size={18} className="mt-0.5 shrink-0 text-warn-ink" />
              <div className="flex-1">
                <p className="font-medium text-hi">
                  {backup.never
                    ? 'You have not backed up yet'
                    : `It has been ${backup.days_since} days since your last backup`}
                </p>
                <p className="mt-1 text-sm text-lo">
                  {backup.never
                    ? 'A backup is one file. Download it now and keep it in your email or cloud drive — if this device is lost, that file is your practice.'
                    : `The reminder fires every ${BACKUP_INTERVAL_DAYS} days. One tap and you are covered again.`}
                </p>
                <Button variant="primary" className="mt-3" icon={<Download size={16} />} onClick={exportJson}>
                  Download backup
                </Button>
              </div>
            </div>
          </Card>
        </Reveal>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* ── Backup ───────────────────────────────────────────────────── */}
        <section>
          <SectionHeader title="Backup and restore" hint="JSON round-trips exactly" />
          <Card>
            <div className="flex flex-wrap gap-2">
              <Button variant="primary" icon={<Download size={16} />} onClick={exportJson}>
                Download backup (JSON)
              </Button>
              <Button variant="quiet" icon={<Download size={16} />} onClick={exportCsv}>
                Export CSV
              </Button>
            </div>

            <p className="mt-3 text-sm text-lo">
              JSON is the format that restores exactly — every score, flag and nested value. CSV is
              for reading in Excel; it cannot carry the nested fields, so it is a view rather than a
              backup.
            </p>

            {/* Drop target for restore. */}
            <div
              onDragOver={(event) => {
                event.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(event) => {
                event.preventDefault();
                setDragging(false);
                const file = event.dataTransfer.files[0];
                if (file) void restore(file);
              }}
              className={cn(
                'mt-4 rounded-md border border-dashed p-5 text-center transition-colors duration-150',
                dragging ? 'border-accent bg-accent-quiet' : 'border-edge',
              )}
            >
              <Upload size={20} className="mx-auto mb-2 text-lo" />
              <p className="text-sm text-hi">Drop a backup file here to restore</p>
              <p className="mt-1 text-xs text-lo">This replaces everything currently in the app.</p>
              <input
                ref={fileInput}
                type="file"
                accept="application/json,.json"
                aria-label="Choose a backup file to restore"
                className="cmw-sr-only"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) void restore(file);
                  event.target.value = '';
                }}
              />
              <Button variant="quiet" className="mt-3" onClick={() => fileInput.current?.click()}>
                Choose a file
              </Button>
            </div>

            {backup.last_backup_at ? (
              <p className="mt-3 text-xs text-lo">
                Last backup {new Date(backup.last_backup_at).toLocaleString()}.
              </p>
            ) : null}
          </Card>
        </section>

        {/* ── Storage ──────────────────────────────────────────────────── */}
        <section>
          <SectionHeader title="What is stored" hint={`${totalRows} rows on this device`} />
          <Card>
            <div className="mb-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
              {(Object.keys(TABLE_LABELS) as DatasetTable[]).map((table) => (
                <StatTile key={table} label={TABLE_LABELS[table]!} value={data[table].length} />
              ))}
            </div>

            <div className="flex items-center gap-2 border-t border-edge pt-3">
              <Database size={15} className="shrink-0 text-lo" />
              <p className="text-sm text-lo">
                Storage:{' '}
                <span className="text-hi">
                  {storeKind === 'indexeddb'
                    ? 'IndexedDB on this device'
                    : storeKind === 'memory'
                      ? 'memory only — nothing is being saved'
                      : (storeKind ?? 'unknown')}
                </span>
              </p>
            </div>

            {storeKind === 'memory' ? (
              <p className="mt-2 text-sm text-warn-ink">
                This browser is not letting the app store data — usually private browsing. Export a
                backup before you close the tab.
              </p>
            ) : null}

            <TakeItWithYou />
          </Card>
        </section>

        {/* ── Appearance ───────────────────────────────────────────────── */}
        <section>
          <SectionHeader title="Appearance" hint="Both themes are contrast-tested" />
          <Card>
            <div className="flex flex-wrap gap-1.5">
              {themeNames.map((name) => (
                <Chip
                  key={name}
                  tone={theme === name ? 'accent' : 'neutral'}
                  pressed={theme === name}
                  onClick={() => useStore.getState().setTheme(name)}
                >
                  {name === 'dawn' ? 'Dawn (dark)' : 'Morning (light)'}
                </Chip>
              ))}
            </div>
            <p className="mt-3 text-sm text-lo">
              Morning is designed alongside Dawn rather than inverted from it, so neither is a
              second-class version of the other.
            </p>
          </Card>
        </section>

        {/* ── Privacy ──────────────────────────────────────────────────── */}
        <section>
          <SectionHeader title="Privacy" hint="POPIA, in plain terms" />
          <Card>
            <div className="flex items-start gap-3">
              <ShieldCheck size={18} className="mt-0.5 shrink-0 text-success-ink" />
              <div className="text-sm text-lo">
                <p className="text-hi">You are processing other people's personal information.</p>
                <ul className="mt-2 flex flex-col gap-1.5">
                  <li>
                    Everything stays on this device. There is no account and no server holding your
                    coachees' notes.
                  </li>
                  <li>
                    Wellness coaching notes are not medical records — keeping them that way keeps
                    this out of health-regulation territory.
                  </li>
                  <li>
                    A coachee can ask for their data or ask you to delete it. Export gives you
                    theirs; removing them here removes it.
                  </li>
                  <li>
                    Add a consent line to your client agreement covering the notes you keep, before
                    any client-facing link exists.
                  </li>
                  <li>
                    If you switch the Copilot on, session notes are sent to Anthropic to be
                    analysed. First names only, contact details stripped — but the notes themselves
                    still describe a named person, so that belongs in the consent line too.
                  </li>
                </ul>
              </div>
            </div>
          </Card>
        </section>

        {/*
          Full width, and last. A `col-span-2` card placed mid-grid pushes the
          section after it onto a row of its own and leaves a hole beside the one
          before — so the wide card goes at the end where it has nothing to split.
        */}
        <section className="lg:col-span-2">
          <SectionHeader title="AI Copilot" hint="Optional — the app is complete without it" />
          <CopilotSettings data={data} />
        </section>
      </div>

      {/* ── Danger zone ──────────────────────────────────────────────────── */}
      <section className="mt-7">
        <SectionHeader title="Start over" />
        <Card className="border-danger/30">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-hi">Load the sample practice, or clear everything</p>
              <p className="mt-1 text-sm text-lo">
                Both replace what is currently here. Download a backup first if you need it.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button variant="quiet" onClick={() => void useStore.getState().loadSample()}>
                Load sample
              </Button>
              <Button variant="danger" onClick={() => setConfirmClear(true)}>
                Clear all data
              </Button>
            </div>
          </div>
        </Card>
      </section>

      <Modal
        open={confirmClear}
        onClose={() => setConfirmClear(false)}
        title="Clear everything?"
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirmClear(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={() => {
                void useStore.getState().clearAll();
                setConfirmClear(false);
              }}
            >
              Yes, clear it
            </Button>
          </>
        }
      >
        <p className="text-hi">
          This removes all <Numeric>{totalRows}</Numeric> rows from this device — every coachee,
          session, wheel snapshot and post.
        </p>
        <p className="mt-2 text-sm text-lo">
          It cannot be undone from inside the app. If you have a backup file, you can restore from
          it afterwards.
        </p>
        <Button
          variant="quiet"
          className="mt-4"
          icon={<Download size={16} />}
          onClick={exportJson}
          full
        >
          Download a backup first
        </Button>
      </Modal>
    </div>
  );
}

/**
 * "Take the app with you" — shown only when this is a hosted copy.
 *
 * §6's artefact and the deployed site are the same build, emitted twice under
 * two names, so the site can hand her the offline copy of itself. That closes
 * the loop the compendium describes: she finds it at a URL, and leaves with a
 * file that keeps working when the URL does not.
 *
 * Hidden over `file://` because there she is already holding it, and a button
 * offering to download the thing she opened from her own disk reads as a bug.
 */
function TakeItWithYou() {
  // `file:` has no host. Checking the protocol rather than the hostname keeps
  // this correct on localhost, on a preview URL and on her own domain alike.
  const hosted = typeof window !== 'undefined' && window.location.protocol.startsWith('http');
  if (!hosted) return null;

  return (
    <div className="mt-3 border-t border-edge pt-3">
      <p className="text-sm text-hi">Take this app with you</p>
      <p className="mt-1 text-sm text-lo">
        The same app as one file. Keep it on your phone and it opens with no internet, no login and
        no website — even if this address stops working.
      </p>
      <Button
        variant="quiet"
        className="mt-3"
        icon={<Download size={16} />}
        onClick={() => {
          // An anchor with `download` rather than a navigation, so this works on
          // a host that does not send `Content-Disposition`. Setting
          // `location.href` would depend on that header and otherwise replace the
          // app with a second copy of itself in the same tab.
          const link = document.createElement('a');
          link.href = 'CoachMillaWellness.html';
          link.download = 'CoachMillaWellness.html';
          document.body.append(link);
          link.click();
          link.remove();
        }}
      >
        Download the offline copy
      </Button>
      <p className="mt-2 text-xs text-lo">
        Your coachees live in this browser, not in the file — download a backup as well, and restore
        it once on the copy you keep.
      </p>
    </div>
  );
}

/**
 * The Copilot's settings (§9).
 *
 * The key field is the sensitive part of this whole build, so three things are
 * true of it at once and all three are said out loud on the screen: it is stored
 * only in this browser, it is excluded from every backup file she exports, and
 * removing it turns the Copilot off without touching anything else.
 *
 * It is a password field with no reveal toggle. She pastes it once; a reveal
 * button would exist only for the case where someone is reading it off her
 * screen.
 */
function CopilotSettings({ data }: { data: CmwDataset }) {
  const { apiKey, budgetUsd, models } = useAiSettings();
  const copilot = useCopilot();

  const [draftKey, setDraftKey] = useState(apiKey);
  const [budget, setBudget] = useState(String(budgetUsd));

  const save = useStore.getState().saveSetting;

  return (
    <Card>
      <div className="grid gap-5 lg:grid-cols-2">
        <div>
          <TextInput
            label="Anthropic API key"
            type="password"
            value={draftKey}
            onChange={setDraftKey}
            placeholder="sk-ant-…"
            hint="Stored in this browser only. Never included in a backup file, never sent anywhere but Anthropic."
          />
          <div className="mt-3 flex flex-wrap gap-2">
            <Button
              variant="primary"
              disabled={draftKey.trim() === apiKey}
              onClick={() => {
                void save(SETTING_KEYS.anthropicApiKey, draftKey.trim());
                useStore
                  .getState()
                  .toast(
                    'success',
                    draftKey.trim() ? 'Copilot switched on.' : 'Copilot switched off.',
                  );
              }}
            >
              Save key
            </Button>
            {apiKey ? (
              <Button
                variant="quiet"
                onClick={() => {
                  setDraftKey('');
                  void save(SETTING_KEYS.anthropicApiKey, '');
                  useStore.getState().toast('info', 'Key removed from this device.');
                }}
              >
                Remove key
              </Button>
            ) : null}
          </div>

          <p className="mt-3 flex items-center gap-2 text-sm text-lo">
            <Sparkles size={14} className="shrink-0 text-accent-ink" aria-hidden />
            {copilot.available
              ? `Running on ${copilot.transportLabel}.`
              : 'Off. Sessions, wheels and content all work exactly as they do now.'}
          </p>
        </div>

        <div>
          <TextInput
            label="Monthly budget"
            type="number"
            value={budget}
            onChange={setBudget}
            hint="A soft cap. At 80% you get a warning; past it, each run asks first rather than refusing."
          />
          <Button
            variant="quiet"
            className="mt-3"
            disabled={Number(budget) === budgetUsd || !Number.isFinite(Number(budget))}
            onClick={() => void save(SETTING_KEYS.aiBudgetUsd, Math.max(0, Number(budget)))}
          >
            Save budget
          </Button>

          <div className="mt-5 border-t border-edge pt-4">
            <BudgetMeter runs={data.ai_runs} capUsd={budgetUsd} />
          </div>
        </div>
      </div>

      {copilot.available ? (
        <div className="mt-6 border-t border-edge pt-5">
          <p className="mb-1 text-sm font-medium text-hi">Which model does what</p>
          <p className="mb-4 text-sm text-lo">
            Sonnet is the default everywhere except the Monday digest, which summarises rather than
            judges. Opus reads a session more carefully and costs roughly five times as much.
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            {(Object.keys(AI_FEATURE_LABELS) as AiRunKind[]).map((kind) => (
              <Select
                key={kind}
                label={AI_FEATURE_LABELS[kind]}
                value={models[kind] ?? copilot.modelFor(kind)}
                options={modelOptions(kind)}
                onChange={(model) => void save(AI_MODELS_SETTING, { ...models, [kind]: model })}
              />
            ))}
          </div>
        </div>
      ) : null}
    </Card>
  );
}

const AI_FEATURE_LABELS: Record<AiRunKind, string> = {
  session_analyzer: 'Session Analyzer',
  coherence_checker: 'Coherence Checker',
  weekly_digest: 'Weekly Digest',
  prep_whisperer: 'Prep Whisperer',
};
