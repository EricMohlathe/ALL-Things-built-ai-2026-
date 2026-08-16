/**
 * M6 · Coherence Checker — "does this piece actually say what I stand for?"
 *
 * It runs on the draft in the editor rather than on the saved row, because the
 * moment the answer is worth anything is *before* she posts. Checking a
 * published piece would only tell her what she can no longer change.
 *
 * The verdict deliberately has three values rather than a score out of ten.
 * `drifting` is the one that earns its place: most off-message content is not
 * wrong, it is true-to-her-but-filed-wrong, and a number would flatten that into
 * "6/10" where a word says what to do about it.
 */

import type { CoherenceVerdict, CoherenceVerdictLevel } from '@cmw/ai';
import type { ContentItem, Pillar } from '@cmw/core';
import { useMemo } from 'react';

import { useCopilot, useCopilotRun } from '../app/copilot.js';
import { Button, Card, Chip, Reveal, type Tone } from '../primitives/index.js';
import { AiCaveat, CopilotOffNote, CopilotRunBar } from './Copilot.js';

const VERDICT_TONES: Record<CoherenceVerdictLevel, Tone> = {
  on: 'success',
  drifting: 'warn',
  off: 'danger',
};

const VERDICT_WORDS: Record<CoherenceVerdictLevel, string> = {
  on: 'On message',
  drifting: 'Drifting',
  off: 'Off pillar',
};

export function CoherenceChecker({
  draft,
  pillar,
  recent,
  onUseHook,
}: {
  /** The piece as it stands in the editor, saved or not. */
  draft: ContentItem;
  pillar: Pillar | null;
  recent: readonly ContentItem[];
  onUseHook: (hook: string) => void;
}) {
  const copilot = useCopilot();

  const input = useMemo(() => ({ item: draft, pillar, recent }), [draft, pillar, recent]);
  const check = useCopilotRun<CoherenceVerdict>((options) =>
    copilot.checkCoherence(input, options),
  );

  if (!copilot.available) {
    return <CopilotOffNote what="Checking a piece against its pillar" />;
  }

  const enough = draft.title.trim().length > 2 && (draft.script ?? draft.hook ?? '').trim().length > 10;
  const estimate = enough
    ? copilot.estimate('coherence_checker', `${draft.title} ${draft.script ?? ''}`)
    : null;

  const verdict = check.data;

  return (
    <Card className="border-dashed">
      <p className="mb-1 text-sm font-medium text-hi">Coherence check</p>
      <p className="mb-3 text-sm text-lo">
        {pillar
          ? `Does this carry "${pillar.core_message}"?`
          : 'No pillar chosen yet — it will tell you which one this belongs to.'}
      </p>

      <CopilotRunBar
        label="Check against pillar"
        estimate={estimate}
        running={check.running}
        error={check.error}
        overBudget={check.overBudget}
        disabled={!enough}
        onRun={(allowOverBudget) => void check.run(allowOverBudget)}
      />

      {!enough ? (
        <p className="mt-2 text-xs text-lo">
          Add a title and a hook or script first — there is nothing to judge yet.
        </p>
      ) : null}

      {verdict ? (
        <Reveal>
          <div className="mt-4 border-t border-edge pt-4">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <Chip tone={VERDICT_TONES[verdict.verdict]}>{VERDICT_WORDS[verdict.verdict]}</Chip>
            </div>

            <p className="text-sm text-hi">{verdict.why}</p>

            <p className="mt-3 text-sm font-medium text-hi">The smallest fix</p>
            <p className="text-sm text-lo">{verdict.one_line_fix}</p>

            <p className="mt-3 text-sm font-medium text-hi">A hook it suggests</p>
            <p className="text-sm text-lo">{verdict.suggested_hook}</p>
            <Button
              variant="quiet"
              className="mt-2"
              onClick={() => onUseHook(verdict.suggested_hook)}
            >
              Use this hook
            </Button>

            <AiCaveat className="mt-4" />
          </div>
        </Reveal>
      ) : null}
    </Card>
  );
}
