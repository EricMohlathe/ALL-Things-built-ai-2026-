/**
 * M1 — COACHEE DETAIL.
 *
 * Five tabs: Overview, Wheel, Sessions, Actions, Notes. The SMARTER chips on each
 * goal are the sharpest thing on this page — toggling "Exciting" and "Rewarded"
 * turns the compendium's noted gap from an invisible habit into a visible switch.
 */

import {
  SMARTER_FLAGS,
  WHEEL_DOMAINS_DEFAULT,
  coacheeRisk,
  frameworkFor,
  gapToTarget,
  groupWheelRows,
  latestSnapshot,
  relativeDay,
  scoreSession,
  suggestReviewDates,
  toIsoDate,
  wheelAverage,
  wheelDelta,
  type ActionItem,
  type CmwDataset,
  type SmarterFlags,
  type Uuid,
} from '@cmw/core';
import { CalendarClock, Check, Download, Plus, Trash2 } from 'lucide-react';
import { useState } from 'react';

import { BarMeter, StatTile, TrendLine } from '../charts/index.js';
import { hrefFor, navigate, type ClientTab } from '../app/router.js';
import {
  actionsFor,
  coacheeById,
  goalsFor,
  scoresFor,
  sessionsFor,
  useStore,
  wheelRowsFor,
} from '../app/store.js';
import {
  Avatar,
  Button,
  Card,
  Chip,
  EmptyState,
  Numeric,
  ProgressRing,
  Reveal,
  SectionHeader,
  Select,
  TextArea,
  TextInput,
  cn,
} from '../primitives/index.js';
import { LivingWheel } from '../wheel/LivingWheel.js';
import { downloadBlob, wheelPngBlob } from '../wheel/export.js';

const TABS: Array<{ value: ClientTab; label: string }> = [
  { value: 'overview', label: 'Overview' },
  { value: 'wheel', label: 'Wheel' },
  { value: 'sessions', label: 'Sessions' },
  { value: 'actions', label: 'Actions' },
  { value: 'notes', label: 'Notes' },
];

export function ClientDetail({
  data,
  id,
  tab,
}: {
  data: CmwDataset;
  id: Uuid;
  tab: ClientTab;
}) {
  const coachee = coacheeById(data, id);
  const today = toIsoDate(new Date());

  if (!coachee) {
    return (
      <EmptyState
        title="Coachee not found"
        body="This person may have been removed. Head back to the constellation."
        action={
          <Button variant="quiet" onClick={() => navigate({ name: 'clients' })}>
            Back to clients
          </Button>
        }
      />
    );
  }

  const snapshot = latestSnapshot(wheelRowsFor(data, id), id);
  const average = wheelAverage(snapshot);
  const risk = coacheeRisk(id, actionsFor(data, id), today);

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <Avatar name={coachee.name} size={52} />
          <div>
            <h1 className="font-display text-3xl text-hi">{coachee.name}</h1>
            <p className="mt-0.5 text-sm text-lo">
              {coachee.package ?? 'No package set'} · since {coachee.start_date}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Select
            label="Status"
            value={coachee.status}
            options={[
              { value: 'active', label: 'Active' },
              { value: 'paused', label: 'Paused' },
              { value: 'alumni', label: 'Alumni' },
            ]}
            onChange={(status) => void useStore.getState().updateCoachee(id, { status })}
          />
        </div>
      </div>

      {risk.level !== 'none' ? (
        <Reveal>
          <Card className="mb-5 border-warn/40">
            <p className="text-sm text-hi">
              <span className="font-medium">{risk.reason}.</span> A slipped review is the earliest
              sign someone is drifting — a short message today is worth more than a long one next
              week.
            </p>
          </Card>
        </Reveal>
      ) : null}

      <nav role="tablist" className="mb-6 flex gap-1 overflow-x-auto border-b border-edge">
        {TABS.map((option) => (
          <a
            key={option.value}
            role="tab"
            aria-selected={tab === option.value}
            href={hrefFor({ name: 'client', id, tab: option.value })}
            className={cn(
              'relative min-h-11 shrink-0 px-3 text-sm font-medium leading-[2.75rem] transition-colors duration-150',
              tab === option.value
                ? 'text-hi after:absolute after:inset-x-2 after:-bottom-px after:h-0.5 after:rounded-pill after:bg-accent'
                : 'text-lo hover:text-hi',
            )}
          >
            {option.label}
          </a>
        ))}
      </nav>

      {tab === 'overview' ? (
        <Overview data={data} id={id} average={average} />
      ) : tab === 'wheel' ? (
        <WheelTab data={data} id={id} name={coachee.name} />
      ) : tab === 'sessions' ? (
        <SessionsTab data={data} id={id} />
      ) : tab === 'actions' ? (
        <ActionsTab data={data} id={id} today={today} />
      ) : (
        <NotesTab data={data} id={id} />
      )}
    </div>
  );
}

// ── Overview ──────────────────────────────────────────────────────────────

function Overview({
  data,
  id,
  average,
}: {
  data: CmwDataset;
  id: Uuid;
  average: number | null;
}) {
  const [statement, setStatement] = useState('');
  const goals = goalsFor(data, id).filter((g) => g.status === 'open');
  const actions = actionsFor(data, id).filter((a) => a.status !== 'done');
  const snapshot = latestSnapshot(wheelRowsFor(data, id), id);
  const gaps = gapToTarget(snapshot).slice(0, 3);

  const addGoal = async (): Promise<void> => {
    if (statement.trim().length < 3) return;
    await useStore.getState().addGoal(id, statement);
    setStatement('');
  };

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <section>
        <SectionHeader title="Goals" hint="SMARTER flags are earned, not assumed" />

        <Card className="mb-3">
          <div className="flex flex-wrap items-end gap-2">
            <div className="min-w-48 flex-1">
              <TextInput
                label="New goal"
                value={statement}
                onChange={setStatement}
                placeholder="Run a 5km without walking"
                onEnter={addGoal}
              />
            </div>
            <Button variant="primary" icon={<Plus size={16} />} onClick={addGoal}>
              Add
            </Button>
          </div>
        </Card>

        {goals.length === 0 ? (
          <Card>
            <p className="text-sm text-lo">No open goals yet.</p>
          </Card>
        ) : (
          <ul className="flex flex-col gap-2">
            {goals.map((goal) => (
              <li key={goal.id}>
                <Card>
                  <div className="flex items-start justify-between gap-3">
                    <p className="flex-1 text-hi">{goal.statement}</p>
                    <Button
                      variant="ghost"
                      title="Mark achieved"
                      label="Mark achieved"
                      icon={<Check size={16} />}
                      onClick={() =>
                        void useStore.getState().updateGoal(goal.id, { status: 'achieved' })
                      }
                    />
                  </div>
                  {/* The visible gap: each letter is a switch she can see is off. */}
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {SMARTER_FLAGS.map((flag) => {
                      const on = goal.smarter[flag.key as keyof SmarterFlags];
                      return (
                        <Chip
                          key={flag.key}
                          tone={on ? 'success' : 'neutral'}
                          pressed={on}
                          title={`${flag.label}${on ? ' — named' : ' — not named yet'}`}
                          onClick={() =>
                            void useStore
                              .getState()
                              .toggleSmarter(goal.id, flag.key as keyof SmarterFlags)
                          }
                        >
                          {on ? <Check size={12} /> : null}
                          {flag.label}
                        </Chip>
                      );
                    })}
                  </div>
                  {goal.target_date ? (
                    <p className="mt-2 text-xs text-lo">Target {goal.target_date}</p>
                  ) : null}
                </Card>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <SectionHeader title="Where they are" />
        <Card className="mb-3">
          <div className="flex items-center gap-5">
            <ProgressRing
              value={average === null ? null : average * 10}
              label="Wheel average"
              tone="success"
            />
            <div className="flex-1">
              {gaps.length === 0 ? (
                <p className="text-sm text-lo">No wheel scored yet.</p>
              ) : (
                <>
                  <p className="mb-2 text-sm text-lo">Widest gaps to target</p>
                  <BarMeter
                    rows={gaps.map((gap) => ({
                      label: gap.domain,
                      value: gap.score,
                      note: `target ${gap.target}`,
                      tone: gap.gap >= 4 ? 'warn' : 'success',
                    }))}
                    max={10}
                    suffix="/10"
                  />
                </>
              )}
            </div>
          </div>
        </Card>

        <SectionHeader title="Open actions" hint={`${actions.length} outstanding`} />
        {actions.length === 0 ? (
          <Card>
            <p className="text-sm text-lo">Nothing outstanding.</p>
          </Card>
        ) : (
          <ul className="flex flex-col gap-2">
            {actions.slice(0, 5).map((action) => (
              <li key={action.id}>
                <Card>
                  <p className="text-hi">{action.title}</p>
                  <p className="mt-0.5 text-xs text-lo">
                    {action.review_date ? `Review ${action.review_date}` : 'No review date set'}
                  </p>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

// ── Wheel tab ─────────────────────────────────────────────────────────────

function WheelTab({ data, id, name }: { data: CmwDataset; id: Uuid; name: string }) {
  const snapshots = groupWheelRows(wheelRowsFor(data, id), id);
  const [index, setIndex] = useState(Math.max(0, snapshots.length - 1));
  const [exporting, setExporting] = useState(false);

  const domains = useStore.getState().setting<string[]>('wheel_domains', [
    ...WHEEL_DOMAINS_DEFAULT,
  ]);

  const current = snapshots[Math.min(index, snapshots.length - 1)] ?? null;
  const previous = index > 0 ? snapshots[index - 1] ?? null : null;
  const delta = wheelDelta(previous, current);

  const values =
    current?.domains ??
    domains.map((domain) => ({ domain, score: 5, target: 8 }));

  const save = (domain: string, score: number): void => {
    const next = values.map((v) => (v.domain === domain ? { ...v, score } : v));
    void useStore.getState().saveWheelSnapshot({
      coachee_id: id,
      date: current?.date ?? toIsoDate(new Date()),
      domains: next,
    });
  };

  const exportPng = async (): Promise<void> => {
    setExporting(true);
    try {
      const blob = await wheelPngBlob({
        domains: values,
        title: name.split(/\s+/)[0],
        subtitle: current ? `Wheel of Life · ${current.date}` : 'Wheel of Life',
      });
      downloadBlob(blob, `wheel-${name.split(/\s+/)[0]?.toLowerCase()}-${current?.date ?? 'today'}.png`);
      useStore.getState().toast('success', 'Wheel exported as a PNG, ready to send.');
    } catch (cause) {
      useStore
        .getState()
        .toast('error', cause instanceof Error ? cause.message : 'Export failed.');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
      <div>
        <Card>
          <div className="flex flex-col items-center">
            <LivingWheel
              domains={values}
              editable
              onScoreChange={save}
              improved={delta.improved}
              snapshotKey={current?.date}
              size={460}
            />
          </div>

          {/* Timeline scrubber — morphs the wheel between snapshot dates. */}
          {snapshots.length > 1 ? (
            <div className="mt-6 border-t border-edge pt-4">
              <label htmlFor="wheel-scrub" className="text-sm font-medium text-hi">
                Timeline
              </label>
              <input
                id="wheel-scrub"
                type="range"
                min={0}
                max={snapshots.length - 1}
                step={1}
                value={Math.min(index, snapshots.length - 1)}
                onChange={(event) => setIndex(Number(event.target.value))}
                className="mt-1 h-11 w-full accent-[var(--cmw-accent)]"
              />
              <div className="flex justify-between text-xs text-lo">
                <span>{snapshots[0]!.date}</span>
                <span className="text-hi">{current?.date}</span>
                <span>{snapshots[snapshots.length - 1]!.date}</span>
              </div>
            </div>
          ) : null}
        </Card>
      </div>

      <div className="flex flex-col gap-3">
        <Card>
          <SectionHeader title="Since last time" />
          {previous === null ? (
            <p className="text-sm text-lo">
              This is the first snapshot — score another one to see movement.
            </p>
          ) : (
            <>
              <div className="mb-3 grid grid-cols-2 gap-2">
                <StatTile
                  label="Average"
                  value={delta.average_to ?? '—'}
                  hint={
                    delta.average_delta === null
                      ? undefined
                      : `${delta.average_delta > 0 ? '+' : ''}${delta.average_delta} since ${previous.date}`
                  }
                  tone={
                    delta.average_delta !== null && delta.average_delta > 0
                      ? 'success-ink'
                      : delta.average_delta !== null && delta.average_delta < 0
                        ? 'warn-ink'
                        : 'hi'
                  }
                />
                <StatTile
                  label="Improved"
                  value={delta.improved.length}
                  hint={`${delta.declined.length} declined`}
                  tone="success-ink"
                />
              </div>
              {delta.biggest_gain ? (
                <p className="text-sm text-hi">
                  Biggest gain: {delta.biggest_gain.domain}{' '}
                  <Numeric className="text-success-ink">+{delta.biggest_gain.delta}</Numeric>
                </p>
              ) : null}
              {delta.biggest_drop ? (
                <p className="mt-1 text-sm text-hi">
                  Biggest drop: {delta.biggest_drop.domain}{' '}
                  <Numeric className="text-warn-ink">{delta.biggest_drop.delta}</Numeric>
                </p>
              ) : null}
            </>
          )}
        </Card>

        <Card>
          <SectionHeader title="Average over time" />
          <TrendLine
            points={snapshots.map((s) => ({
              label: s.date.slice(5),
              value: wheelAverage(s) ?? 0,
            }))}
            tone="success"
            suffix="/10"
          />
        </Card>

        <Button
          variant="quiet"
          icon={<Download size={16} />}
          onClick={exportPng}
          disabled={exporting}
          full
        >
          {exporting ? 'Rendering…' : 'Export as PNG'}
        </Button>

        <Button
          variant="quiet"
          onClick={() =>
            void useStore.getState().saveWheelSnapshot({
              coachee_id: id,
              date: toIsoDate(new Date()),
              domains: values.map((v) => ({ ...v })),
            })
          }
          full
        >
          Save today's snapshot
        </Button>
      </div>
    </div>
  );
}

// ── Sessions tab ──────────────────────────────────────────────────────────

function SessionsTab({ data, id }: { data: CmwDataset; id: Uuid }) {
  const sessions = sessionsFor(data, id);

  if (sessions.length === 0) {
    return (
      <EmptyState
        title="No sessions logged"
        body="Log a session to get an adherence scorecard and a reminders checklist against your own framework."
        action={
          <Button variant="primary" onClick={() => navigate({ name: 'session-new' })}>
            Log a session
          </Button>
        }
      />
    );
  }

  return (
    <ul className="flex flex-col gap-2">
      {sessions.map((session) => {
        const card = scoreSession({
          session,
          scores: scoresFor(data, session.id),
          coachee_id: id,
        });
        return (
          <li key={session.id}>
            <a href={hrefFor({ name: 'session', id: session.id })}>
              <Card interactive>
                <div className="flex items-center justify-between gap-4">
                  <div className="min-w-0">
                    <p className="font-medium text-hi">
                      {session.date} · {session.framework}
                    </p>
                    <p className="mt-0.5 line-clamp-2 text-sm text-lo">
                      {session.summary ?? frameworkFor(session.framework).expansion}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {session.participants.length > 1 ? <Chip tone="info">Joint</Chip> : null}
                      {card.weakest.length > 0 ? (
                        <Chip tone="warn">Weakest: {card.weakest.join(', ')}</Chip>
                      ) : null}
                    </div>
                  </div>
                  <ProgressRing value={card.adherence_pct} size={54} />
                </div>
              </Card>
            </a>
          </li>
        );
      })}
    </ul>
  );
}

// ── Actions tab ───────────────────────────────────────────────────────────

const COLUMNS: Array<{ status: ActionItem['status']; label: string }> = [
  { status: 'open', label: 'Open' },
  { status: 'in_review', label: 'In review' },
  { status: 'done', label: 'Done' },
];

function ActionsTab({ data, id, today }: { data: CmwDataset; id: Uuid; today: string }) {
  const [title, setTitle] = useState('');
  const [review, setReview] = useState(suggestReviewDates(today)[0]);
  const actions = actionsFor(data, id);

  const add = async (): Promise<void> => {
    if (title.trim().length < 3) return;
    await useStore.getState().addAction({ coachee_id: id, title, review_date: review });
    setTitle('');
  };

  return (
    <div>
      <Card className="mb-5">
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-48 flex-1">
            <TextInput
              label="New action"
              value={title}
              onChange={setTitle}
              placeholder="Walk 20 minutes before work"
              onEnter={add}
            />
          </div>
          <div className="w-40">
            <TextInput label="Review date" type="date" value={review} onChange={setReview} />
          </div>
          <Button variant="primary" icon={<Plus size={16} />} onClick={add}>
            Add
          </Button>
        </div>
        <p className="mt-2 text-xs text-lo">
          Defaults to the coming Wednesday — the review rhythm from your framework.
        </p>
      </Card>

      <div className="grid gap-4 md:grid-cols-3">
        {COLUMNS.map((column) => {
          const items = actions.filter((a) => a.status === column.status);
          return (
            <section key={column.status}>
              <SectionHeader title={column.label} hint={`${items.length}`} />
              <ul className="flex flex-col gap-2">
                {items.map((action) => {
                  const slipped =
                    action.status !== 'done' && action.review_date && action.review_date < today;
                  return (
                    <li key={action.id}>
                      <Card className={cn(slipped && 'border-warn/40')}>
                        <p className={cn('text-hi', action.status === 'done' && 'line-through opacity-70')}>
                          {action.title}
                        </p>
                        <div className="mt-2 flex flex-wrap items-center gap-1.5">
                          {action.review_date ? (
                            <Chip tone={slipped ? 'warn' : 'neutral'} icon={<CalendarClock size={12} />}>
                              {slipped
                                ? `slipped ${relativeDay(today, action.review_date)}`
                                : action.review_date}
                            </Chip>
                          ) : (
                            <Chip tone="warn">No review date</Chip>
                          )}
                        </div>
                        <div className="mt-3 flex flex-wrap gap-1.5">
                          {COLUMNS.filter((c) => c.status !== action.status).map((target) => (
                            <Button
                              key={target.status}
                              variant="ghost"
                              className="min-h-9 px-2 text-xs"
                              onClick={() =>
                                void useStore.getState().setActionStatus(action.id, target.status)
                              }
                            >
                              → {target.label}
                            </Button>
                          ))}
                          <Button
                            variant="ghost"
                            title="Remove"
                            className="ml-auto min-h-9 px-2"
                            icon={<Trash2 size={14} />}
                            onClick={() => void useStore.getState().removeAction(action.id)}
                          />
                        </div>
                      </Card>
                    </li>
                  );
                })}
                {items.length === 0 ? (
                  <li className="rounded-md border border-dashed border-edge px-3 py-6 text-center text-sm text-lo">
                    Nothing here
                  </li>
                ) : null}
              </ul>
            </section>
          );
        })}
      </div>
    </div>
  );
}

// ── Notes tab ─────────────────────────────────────────────────────────────

function NotesTab({ data, id }: { data: CmwDataset; id: Uuid }) {
  const coachee = coacheeById(data, id);
  const [notes, setNotes] = useState(coachee?.notes ?? '');

  return (
    <Card>
      <TextArea
        label="Private notes"
        value={notes}
        onChange={setNotes}
        rows={12}
        hint="Never shown on a client-facing page. Saved on this device."
      />
      <div className="mt-3 flex justify-end">
        <Button
          variant="primary"
          onClick={() => {
            void useStore.getState().updateCoachee(id, { notes });
            useStore.getState().toast('success', 'Notes saved.');
          }}
        >
          Save notes
        </Button>
      </div>
    </Card>
  );
}
