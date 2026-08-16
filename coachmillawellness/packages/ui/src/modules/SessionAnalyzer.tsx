/**
 * M6 · Session Analyzer — the button that replaces her manual Claude loop.
 *
 * Today she pastes session notes into a chat, reads a grading, and types the
 * result back in by hand. This does the same work against the same methodology
 * and lands it in the right fields — but the shape of the screen is the argument:
 * nothing the model returns is saved on arrival. Ratings sit in editable chips,
 * evidence in editable text, and each suggested action has to be ticked. She
 * presses one button at the end, and until she does, her scorecard is untouched.
 *
 * That is not caution about model quality. It is that this product's whole claim
 * is that it grades *her* practice — a grade she did not agree with, silently
 * saved, would make her own adherence chart a record of the machine's opinion.
 */

import type { AnalyzedElement, SessionAnalysis } from '@cmw/ai';
import {
  RATINGS,
  elementLabel,
  type ChecklistItem,
  type ChecklistState,
  type Coachee,
  type Goal,
  type ActionItem,
  type Rating,
  type Session,
  type WheelSnapshot,
} from '@cmw/core';
import { useMemo, useState } from 'react';

import { useCopilot, useCopilotRun } from '../app/copilot.js';
import { useStore } from '../app/store.js';
import {
  Card,
  Chip,
  SectionHeader,
  TextArea,
  TextInput,
  type Tone,
} from '../primitives/index.js';
import { CopilotOffNote, CopilotRunBar, ProposalCard } from './Copilot.js';

const RATING_TONES: Record<Rating, Tone> = {
  Strong: 'success',
  Adequate: 'info',
  Weak: 'warn',
  Met: 'accent',
  'N/A': 'neutral',
};

const CHECKLIST_LABELS: Record<ChecklistItem, string> = {
  smarter_met: 'SMARTER named in full',
  low_scores_flagged: 'Low wheel scores named',
  will_step: 'Ended with a dated action',
  review_date_set: 'Review date set before closing',
};

const CHECKLIST_STATES: ChecklistState[] = ['pass', 'fail', 'na'];

const STATE_LABELS: Record<ChecklistState, string> = {
  pass: 'Yes',
  fail: 'No',
  na: 'Did not arise',
};

export function SessionAnalyzer({
  session,
  coachee,
  participants,
  goals,
  wheel,
  openActions,
}: {
  session: Session;
  coachee: Coachee;
  participants: readonly Coachee[];
  goals: readonly Goal[];
  wheel: WheelSnapshot | null;
  openActions: readonly ActionItem[];
}) {
  const copilot = useCopilot();
  const [notes, setNotes] = useState('');
  /** Which suggested actions she wants. Everything starts unticked. */
  const [wanted, setWanted] = useState<Set<number>>(new Set());

  const input = useMemo(
    () => ({
      session,
      coachee,
      participants,
      goals,
      notes,
      wheel,
      openActions,
    }),
    [session, coachee, participants, goals, notes, wheel, openActions],
  );

  const analysis = useCopilotRun<SessionAnalysis>((options) =>
    copilot.analyzeSession(input, options),
  );

  if (!copilot.available) {
    return (
      <section>
        <SectionHeader title="Analyze this session" hint="Grades against your own frameworks" />
        <CopilotOffNote what="Grading a session from your notes" />
      </section>
    );
  }

  const estimate = notes.trim()
    ? copilot.estimate('session_analyzer', notes)
    : null;

  const proposal = analysis.data;

  const accept = async (): Promise<void> => {
    if (!proposal) return;
    const store = useStore.getState();

    for (const element of proposal.elements) {
      await store.rateElement(
        session.id,
        coachee.id,
        element.element,
        element.rating,
        element.note || undefined,
        element.evidence || undefined,
      );
    }

    for (const [item, state] of Object.entries(proposal.checklist) as Array<
      [ChecklistItem, ChecklistState]
    >) {
      await store.recordChecklist(session.id, item, state);
    }

    for (const [index, action] of proposal.suggested_actions.entries()) {
      if (!wanted.has(index)) continue;
      await store.addAction({
        coachee_id: coachee.id,
        session_id: session.id,
        title: action.title,
        ...(action.due ? { due_date: action.due } : {}),
        ...(action.review ? { review_date: action.review } : {}),
      });
    }

    store.toast(
      'success',
      `Scorecard saved for ${coachee.name}. Edit any rating from the cards above.`,
    );
    analysis.reset();
    setWanted(new Set());
  };

  return (
    <section>
      <SectionHeader
        title="Analyze this session"
        hint="Graded against your GROW and GREAT banks"
      />
      <Card>
        <TextArea
          label="Session notes or transcript"
          value={notes}
          onChange={setNotes}
          rows={6}
          placeholder="Paste what you wrote during or after the session. Rough notes are enough."
          hint="Client names are reduced to first names and contact details are stripped before this is sent."
        />

        <div className="mt-4">
          <CopilotRunBar
            label="Analyze session"
            estimate={estimate}
            running={analysis.running}
            error={analysis.error}
            overBudget={analysis.overBudget}
            disabled={notes.trim().length < 40}
            onRun={(allowOverBudget) => void analysis.run(allowOverBudget)}
          />
          {notes.trim().length < 40 ? (
            <p className="mt-2 text-xs text-lo">
              A few sentences at minimum — grading five elements from one line would be guesswork
              dressed as a score.
            </p>
          ) : null}
        </div>
      </Card>

      {proposal ? (
        <ProposalCard
          title={`Proposed scorecard for ${coachee.name}`}
          hint="Change anything here before you save it. Nothing is written until you do."
          onAccept={() => void accept()}
          onDiscard={() => {
            analysis.reset();
            setWanted(new Set());
          }}
          acceptLabel="Save scorecard"
        >
          <div className="flex flex-col gap-3">
            {proposal.elements.map((element, index) => (
              <ProposedElement
                key={element.element}
                element={element}
                onChange={(next) =>
                  analysis.edit({
                    ...proposal,
                    elements: proposal.elements.map((e, i) => (i === index ? next : e)),
                  })
                }
              />
            ))}
          </div>

          <div className="mt-5 border-t border-edge pt-4">
            <p className="mb-2 text-sm font-medium text-hi">Reminders checklist</p>
            <div className="flex flex-col gap-2.5">
              {(Object.keys(CHECKLIST_LABELS) as ChecklistItem[]).map((item) => (
                <div key={item} className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm text-lo">{CHECKLIST_LABELS[item]}</span>
                  <div className="flex gap-1.5">
                    {CHECKLIST_STATES.map((state) => (
                      <Chip
                        key={state}
                        tone={
                          proposal.checklist[item] !== state
                            ? 'neutral'
                            : state === 'pass'
                              ? 'success'
                              : state === 'fail'
                                ? 'warn'
                                : 'neutral'
                        }
                        pressed={proposal.checklist[item] === state}
                        onClick={() =>
                          analysis.edit({
                            ...proposal,
                            checklist: { ...proposal.checklist, [item]: state },
                          })
                        }
                      >
                        {STATE_LABELS[state]}
                      </Chip>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {proposal.suggested_actions.length > 0 ? (
            <div className="mt-5 border-t border-edge pt-4">
              <p className="mb-1 text-sm font-medium text-hi">Actions it heard</p>
              <p className="mb-3 text-xs text-lo">
                Tick the ones that are real. Unticked actions are not created.
              </p>
              <ul className="flex flex-col gap-2">
                {proposal.suggested_actions.map((action, index) => (
                  <li key={`${action.title}-${index}`}>
                    <label className="flex min-h-11 cursor-pointer items-center gap-3 rounded-md border border-edge px-3 py-2">
                      <input
                        type="checkbox"
                        checked={wanted.has(index)}
                        onChange={(event) => {
                          const next = new Set(wanted);
                          if (event.target.checked) next.add(index);
                          else next.delete(index);
                          setWanted(next);
                        }}
                        className="h-4 w-4 shrink-0 accent-[var(--cmw-accent)]"
                      />
                      <span className="min-w-0 flex-1">
                        <span className="block text-sm text-hi">{action.title}</span>
                        <span className="block text-xs text-lo">
                          {action.due ? `Due ${action.due}` : 'No due date'}
                          {action.review ? ` · review ${action.review}` : ' · no review date'}
                        </span>
                      </span>
                    </label>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          <div className="mt-5 border-t border-edge pt-4">
            <TextArea
              label="One thing to do differently"
              value={proposal.one_growth_tip}
              onChange={(one_growth_tip) => analysis.edit({ ...proposal, one_growth_tip })}
              rows={2}
              hint="This is for you, not the client. It is not saved with the scorecard — read it and let it go."
            />
          </div>
        </ProposalCard>
      ) : null}
    </section>
  );
}

function ProposedElement({
  element,
  onChange,
}: {
  element: AnalyzedElement;
  onChange: (next: AnalyzedElement) => void;
}) {
  return (
    <div className="rounded-md border border-edge p-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm font-medium text-hi">{elementLabel(element.element)}</span>
        <div className="flex flex-wrap gap-1.5">
          {RATINGS.map((rating) => (
            <Chip
              key={rating}
              tone={element.rating === rating ? RATING_TONES[rating] : 'neutral'}
              pressed={element.rating === rating}
              onClick={() => onChange({ ...element, rating })}
            >
              {rating}
            </Chip>
          ))}
        </div>
      </div>

      <TextInput
        label="Evidence"
        value={element.evidence}
        onChange={(evidence) => onChange({ ...element, evidence })}
        placeholder="The line this rating rests on"
      />
      <div className="mt-2">
        <TextInput
          label="Note"
          value={element.note}
          onChange={(note) => onChange({ ...element, note })}
        />
      </div>
    </div>
  );
}
