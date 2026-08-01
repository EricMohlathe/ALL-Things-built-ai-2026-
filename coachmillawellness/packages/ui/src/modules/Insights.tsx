/**
 * M5 — INSIGHTS OBSERVATORY.
 *
 * The screen that grades the coach. `coachGrowthCurve` has been written and
 * tested since P1; this is where it becomes visible.
 *
 * The honesty rule this screen keeps: it never smooths a thin month into a
 * trend. Every figure carries the number of graded cycles behind it, and a month
 * with one session says "1 cycle" rather than drawing a confident line between
 * two points. A chart that flatters her is worse than no chart, because the
 * whole point is to show her the element she keeps skipping.
 */

import { formatUsd, spendByKind } from '@cmw/ai';
import {
  FRAMEWORK_NAMES,
  actionCompletionRate,
  coachGrowthCurve,
  groupWheelRows,
  wheelDelta,
  type AiRunKind,
  type CmwDataset,
  type ElementKey,
  type Framework,
} from '@cmw/core';
import { Sparkles, TrendingUp } from 'lucide-react';
import { useMemo, useState } from 'react';

import { useAiSettings } from '../app/copilot.js';
import { liveActions, liveCoachees } from '../app/store.js';
import { BarMeter, StatTile, TrendLine } from '../charts/index.js';
import {
  Card,
  Chip,
  EmptyState,
  Numeric,
  PageHeader,
  SectionHeader,
  Tabs,
} from '../primitives/index.js';
import { BudgetMeter } from './Copilot.js';

const KIND_LABELS: Record<AiRunKind, string> = {
  session_analyzer: 'Session Analyzer',
  coherence_checker: 'Coherence Checker',
  weekly_digest: 'Weekly Digest',
  prep_whisperer: 'Prep Whisperer',
};

export function Insights({ data }: { data: CmwDataset }) {
  const [framework, setFramework] = useState<Framework>('GROW');
  const { budgetUsd } = useAiSettings();

  const curve = useMemo(
    () => coachGrowthCurve(data.sessions, data.session_element_scores, framework),
    [data.sessions, data.session_element_scores, framework],
  );

  const months = useMemo(() => [...new Set(curve.points.map((p) => p.month))].sort(), [curve]);

  /**
   * Cycles, not element-gradings.
   *
   * `averages[].sessions` counts how many times *that element* was graded, so
   * summing across elements multiplies by the framework's length — four graded
   * GROW cycles would report as sixteen. The busiest element is the honest
   * count, because a cycle contributes at most one grading to each.
   */
  const gradedCycles = curve.averages.reduce((most, a) => Math.max(most, a.sessions), 0);

  const completion = actionCompletionRate(liveActions(data));
  const spend = spendByKind(data.ai_runs);

  return (
    <div>
      <PageHeader
        eyebrow="Insights"
        title="How your practice is going"
        subtitle="Your own adherence per element, your clients' movement, and what the Copilot has cost. Every figure names how much data is behind it."
      />

      <div className="mb-7 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="Graded cycles" value={gradedCycles} />
        <StatTile label="Coachees" value={liveCoachees(data).filter((c) => c.status === 'active').length} />
        {/* `rate` is 0–1, not a percentage — printing it raw reads as "0.25%". */}
        <StatTile
          label="Actions done"
          value={completion.rate === null ? '—' : `${Math.round(completion.rate * 100)}%`}
        />
        <StatTile label="AI this month" value={formatUsd(spend.reduce((n, s) => n + s.cost_usd, 0))} />
      </div>

      <section className="mb-7">
        <SectionHeader
          title="Coach Growth Curve"
          hint="Your adherence per element, month by month"
        />

        <Card>
          <Tabs
            active={framework}
            tabs={FRAMEWORK_NAMES.map((name) => ({ value: name, label: name }))}
            onChange={setFramework}
          />

          {gradedCycles === 0 ? (
            <EmptyState
              title="Nothing graded yet"
              body={`Score the elements on a ${framework} session — by hand or with the Analyzer — and this chart starts filling in. It needs a few sessions before a trend means anything.`}
              icon={<TrendingUp size={28} />}
            />
          ) : (
            <div className="mt-5 grid gap-6 lg:grid-cols-2">
              <div>
                <p className="mb-3 text-sm font-medium text-hi">Across every graded cycle</p>
                <BarMeter
                  rows={curve.averages.map((average) => ({
                    label: average.label,
                    value: average.adherence_pct,
                    note:
                      average.sessions === 0
                        ? 'not graded'
                        : `${average.sessions} cycle${average.sessions === 1 ? '' : 's'}`,
                    tone: toneFor(average.element, curve.weakest_element),
                  }))}
                />
                {curve.weakest_element ? (
                  <p className="mt-4 text-sm text-lo">
                    <span className="text-hi">
                      {labelOf(curve, curve.weakest_element)} is your thinnest element.
                    </span>{' '}
                    That is the one worth naming before your next session — not because the score is
                    low, but because it is lower than the rest of your own work.
                  </p>
                ) : null}
              </div>

              <div>
                <p className="mb-3 text-sm font-medium text-hi">Month by month</p>
                {months.length < 2 ? (
                  <p className="py-6 text-sm text-lo">
                    One month of data so far. A line between a single point and nothing is a
                    decoration, so this stays empty until there is a second month to compare.
                  </p>
                ) : (
                  <div className="flex flex-col gap-5">
                    {curve.averages
                      .filter((average) => average.sessions > 0)
                      .map((average) => (
                        <div key={average.element}>
                          <p className="mb-1 text-sm text-hi">{average.label}</p>
                          <TrendLine
                            max={100}
                            suffix="%"
                            height={60}
                            points={months.map((month) => ({
                              label: month,
                              value:
                                curve.points.find(
                                  (p) => p.month === month && p.element === average.element,
                                )?.adherence_pct ?? 0,
                            }))}
                          />
                        </div>
                      ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </Card>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <section>
          <SectionHeader title="Client movement" hint="Wheel change since the first snapshot" />
          <Card>
            <ClientMovement data={data} />
          </Card>
        </section>

        <section>
          <SectionHeader title="Copilot spend" hint="Every call, with its cost" />
          <Card>
            <BudgetMeter runs={data.ai_runs} capUsd={budgetUsd} />

            {spend.length > 0 ? (
              <ul className="mt-4 flex flex-col gap-2 border-t border-edge pt-4">
                {spend.map((row) => (
                  <li key={row.kind} className="flex items-baseline justify-between gap-3">
                    <span className="text-sm text-lo">{KIND_LABELS[row.kind]}</span>
                    <span className="flex items-baseline gap-2">
                      <span className="text-xs text-lo">
                        {row.runs} run{row.runs === 1 ? '' : 's'}
                      </span>
                      <Numeric className="text-sm text-hi">{formatUsd(row.cost_usd)}</Numeric>
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-4 flex items-center gap-2 border-t border-edge pt-4 text-sm text-lo">
                <Sparkles size={14} className="shrink-0 text-accent-ink" aria-hidden />
                Nothing spent yet. The Copilot is optional — everything here works without it.
              </p>
            )}
          </Card>
        </section>
      </div>
    </div>
  );
}

function labelOf(
  curve: ReturnType<typeof coachGrowthCurve>,
  element: ElementKey,
): string {
  return curve.averages.find((a) => a.element === element)?.label ?? element;
}

/**
 * The weakest element is the only one tinted differently.
 *
 * Colouring every bar by score would turn the chart into a traffic light and
 * invite her to read 60% as failure — but 60% across her own graded cycles is
 * just her baseline. One highlight says "this one, next" without grading the
 * rest.
 */
function toneFor(element: ElementKey, weakest: ElementKey | null): string {
  return element === weakest ? 'warn' : 'accent';
}

function ClientMovement({ data }: { data: CmwDataset }) {
  const rows = liveCoachees(data)
    .flatMap((coachee) => {
      const snapshots = groupWheelRows(
        data.wheel_snapshots.filter((r) => !r.deleted_at),
        coachee.id,
      );
      const first = snapshots[0];
      const last = snapshots[snapshots.length - 1];
      if (!first || !last || first.date === last.date) return [];
      const delta = wheelDelta(first, last);
      // `average_delta` is null when a snapshot has no scorable domains. That is
      // an absence of movement rather than movement of zero, so the row is
      // dropped instead of being charted as flat.
      if (delta.average_delta === null) return [];
      return [
        { name: coachee.name, delta, average: delta.average_delta, snapshots: snapshots.length },
      ];
    })
    .sort((a, b) => b.average - a.average);

  if (rows.length === 0) {
    return (
      <p className="py-4 text-sm text-lo">
        Movement needs two wheel snapshots for the same person. Score a wheel again in a month and
        this fills in.
      </p>
    );
  }

  return (
    <ul className="flex flex-col gap-3">
      {rows.map((row) => (
        <li key={row.name} className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="text-sm text-hi">{row.name}</p>
            <p className="text-xs text-lo">
              {row.snapshots} snapshots · {row.delta.improved.length} domains up,{' '}
              {row.delta.declined.length} down
            </p>
          </div>
          <Chip tone={row.average >= 0 ? 'success' : 'warn'}>
            {row.average >= 0 ? '+' : ''}
            {row.average.toFixed(1)} average
          </Chip>
        </li>
      ))}
    </ul>
  );
}
