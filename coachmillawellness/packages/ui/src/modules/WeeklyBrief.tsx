/**
 * M6 · Weekly Digest — the Monday brief, on the Deck.
 *
 * §9 schedules this as a cron on the web and "on open" locally. Build 1 has no
 * scheduler and no server, so it is offered rather than fired: a single line on
 * the Deck saying this week has no brief yet, and a button. Generating it
 * automatically on open would spend her money on a morning she only wanted to
 * check a date.
 *
 * Once written, the brief is read back out of the `ai_run` ledger rather than
 * stored again. The row already holds the JSON and the week it was for, so the
 * ledger *is* the cache — one fewer table, and one fewer way for the Deck to
 * show a brief that no longer matches what it cost.
 */

import { digestContract, latestRun, type WeeklyDigest } from '@cmw/ai';
import {
  buildDeck,
  coherenceMatrix,
  toIsoDate,
  weekKey,
  type CmwDataset,
} from '@cmw/core';
import { CalendarDays } from 'lucide-react';
import { useMemo } from 'react';

import { useCopilot, useCopilotRun } from '../app/copilot.js';
import { liveCoachees, liveContent, livePillars } from '../app/store.js';
import { Card, Chip, Reveal } from '../primitives/index.js';
import { AiCaveat, CopilotRunBar } from './Copilot.js';

export function WeeklyBrief({ data }: { data: CmwDataset }) {
  const copilot = useCopilot();
  const today = toIsoDate(new Date());
  const weekOf = weekKey(today);

  const stored = useMemo(
    () => latestRun<WeeklyDigest>(data.ai_runs, 'weekly_digest', digestContract(), `week:${weekOf}`),
    [data.ai_runs, weekOf],
  );

  const input = useMemo(() => {
    const deck = buildDeck({
      coachees: data.coachees,
      sessions: data.sessions,
      actions: data.action_items,
      content: data.content_items,
      now: today,
      hour: new Date().getHours(),
    });

    // The same rule the coherence map uses — published work only, so a starved
    // pillar cannot look healthy on the strength of drafts.
    const matrix = coherenceMatrix(livePillars(data), liveContent(data), { now: today });

    const weekStart = weekOf;
    const published = liveContent(data).filter(
      (item) =>
        (item.status === 'posted' || item.status === 'analyzed') &&
        (item.publish_date ?? '') >= weekStart,
    ).length;

    return {
      deck,
      coachees: liveCoachees(data),
      starvedPillars: matrix.starved_pillars,
      publishedThisWeek: published,
      weekOf,
    };
  }, [data, today, weekOf]);

  const digest = useCopilotRun<WeeklyDigest>((options) => copilot.weeklyDigest(input, options));

  // Nothing is offered when there is no key. The Deck's own focus sentence is
  // deterministic and already good; an advert for a paid feature is not.
  if (!copilot.available) return null;

  const brief = digest.data ?? stored?.data ?? null;

  return (
    <Reveal>
      <Card className="mb-7">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <p className="flex items-center gap-2 text-sm font-medium text-hi">
            <CalendarDays size={15} className="shrink-0 text-accent-ink" aria-hidden />
            Week of {weekOf}
          </p>
          {stored && !digest.data ? <Chip tone="neutral">Written {stored.run.created_at.slice(0, 10)}</Chip> : null}
        </div>

        {brief ? (
          <div>
            <p className="text-lg text-hi">{brief.focus_sentence}</p>

            {brief.clients_needing_attention.length > 0 ? (
              <div className="mt-4">
                <p className="mb-1.5 text-sm font-medium text-hi">Who needs a nudge</p>
                <ul className="flex flex-col gap-1">
                  {brief.clients_needing_attention.map((client) => (
                    <li key={client.first_name} className="text-sm text-lo">
                      <span className="text-hi">{client.first_name}</span> — {client.why}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {brief.content_gaps.length > 0 ? (
              <div className="mt-4">
                <p className="mb-1.5 text-sm font-medium text-hi">Where the message is thin</p>
                <ul className="flex flex-col gap-1">
                  {brief.content_gaps.map((gap) => (
                    <li key={gap} className="text-sm text-lo">
                      {gap}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            <div className="mt-4 rounded-md border border-edge p-3">
              <p className="text-sm font-medium text-hi">One thing for you</p>
              <p className="mt-1 text-sm text-lo">{brief.coach_tip}</p>
            </div>

            <AiCaveat className="mt-4" />
          </div>
        ) : (
          <p className="text-sm text-lo">
            No brief for this week yet. It reads the week's rollup — slipped reviews, drifting
            clients, starved pillars and your own adherence — and comes back with one line for the
            top of this page.
          </p>
        )}

        <div className="mt-4">
          <CopilotRunBar
            label={brief ? 'Write it again' : 'Write this week’s brief'}
            estimate={copilot.estimate('weekly_digest', JSON.stringify(input.deck).slice(0, 4000))}
            running={digest.running}
            error={digest.error}
            overBudget={digest.overBudget}
            onRun={(allowOverBudget) => void digest.run(allowOverBudget)}
          />
        </div>
      </Card>
    </Reveal>
  );
}
