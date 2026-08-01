/**
 * M6 · Prep Whisperer — the two minutes before a session starts.
 *
 * The brief is deliberately small: three lines she must remember, one question
 * to open with, and the things to hold lightly. A longer brief would be read
 * less, and this one is read standing up.
 *
 * The opening question is drawn from her own bank wherever one fits, which is
 * the difference between a prompt that sounds like her and a prompt that sounds
 * like a coaching blog. Like every other Copilot surface, the result is a draft:
 * it is shown, never saved, because a prep note that outlives the session it
 * prepared is clutter.
 */

import { latestRun, prepContract, type PrepBrief } from '@cmw/ai';
import {
  latestSnapshot,
  scoreSession,
  toIsoDate,
  type ActionItem,
  type CmwDataset,
  type Coachee,
  type Framework,
  type Session,
} from '@cmw/core';
import { Ear } from 'lucide-react';
import { useMemo } from 'react';

import { useCopilot, useCopilotRun } from '../app/copilot.js';
import { goalsFor, scoresFor, wheelRowsFor } from '../app/store.js';
import { Chip, Reveal } from '../primitives/index.js';
import { AiCaveat, CopilotRunBar } from './Copilot.js';

export function PrepWhisperer({
  data,
  coachee,
  framework,
  previous,
  openActions,
}: {
  data: CmwDataset;
  coachee: Coachee;
  framework: Framework;
  previous: Session | null;
  openActions: readonly ActionItem[];
}) {
  const copilot = useCopilot();
  const today = toIsoDate(new Date());

  const input = useMemo(
    () => ({
      coachee,
      framework,
      lastSession: previous,
      lastScorecard: previous
        ? scoreSession({
            session: previous,
            scores: scoresFor(data, previous.id),
            coachee_id: coachee.id,
          })
        : null,
      openActions,
      wheel: latestSnapshot(wheelRowsFor(data, coachee.id), coachee.id),
      goals: goalsFor(data, coachee.id).filter((goal) => goal.status === 'open'),
      today,
    }),
    [data, coachee, framework, previous, openActions, today],
  );

  const stored = useMemo(
    () =>
      latestRun<PrepBrief>(
        data.ai_runs,
        'prep_whisperer',
        prepContract(),
        `prep:${coachee.id}@${today}`,
      ),
    [data.ai_runs, coachee.id, today],
  );

  const prep = useCopilotRun<PrepBrief>((options) => copilot.prepBrief(input, options));

  if (!copilot.available) return null;

  const brief = prep.data ?? stored?.data ?? null;

  return (
    <div className="mt-4 border-t border-edge pt-4">
      {brief ? (
        <Reveal>
          <div className="mb-4">
            <p className="mb-1.5 flex items-center gap-2 text-sm font-medium text-hi">
              <Ear size={15} className="shrink-0 text-accent-ink" aria-hidden />
              Before you start
            </p>
            <ul className="flex flex-col gap-1">
              {brief.recap_3_lines.map((line) => (
                <li key={line} className="text-sm text-hi">
                  {line}
                </li>
              ))}
            </ul>

            <p className="mt-3 text-sm font-medium text-hi">Open with</p>
            <p className="text-sm text-lo">“{brief.suggested_opening_question}”</p>

            {brief.watchouts.length > 0 ? (
              <div className="mt-3">
                <p className="mb-1.5 text-sm font-medium text-hi">Hold lightly</p>
                <div className="flex flex-wrap gap-1.5">
                  {brief.watchouts.map((watchout) => (
                    <Chip key={watchout} tone="warn">
                      {watchout}
                    </Chip>
                  ))}
                </div>
              </div>
            ) : null}

            <AiCaveat className="mt-3" />
          </div>
        </Reveal>
      ) : null}

      <CopilotRunBar
        label={brief ? 'Refresh the brief' : 'Brief me'}
        estimate={copilot.estimate('prep_whisperer', coachee.id)}
        running={prep.running}
        error={prep.error}
        overBudget={prep.overBudget}
        onRun={(allowOverBudget) => void prep.run(allowOverBudget)}
      />
    </div>
  );
}
