/**
 * M2 — SESSION DETAIL: prep, live capture, and the scorecard.
 *
 * This is where her existing manual Claude workflow becomes the product. Three
 * things it insists on, all drawn from Appendix A:
 *
 *  - The steps she tends to skip are marked, not buried. Options/Explore and the
 *    obstacle question carry a visible "often skipped" flag with the coaching note
 *    attached.
 *  - When confidence and commitment both reach 8, the closing script appears in
 *    full. A reminder that a script exists is not the same as the words.
 *  - The reminders checklist is graded from the data, live, with an honest "not
 *    applicable" — so a clear checklist means something.
 *
 * Every rating is editable: the AI proposes and the coach disposes (§2 M2). The
 * Analyzer sits above the stepper and writes into these same fields, so a graded
 * session and a hand-scored one are indistinguishable afterwards — which is what
 * lets the Coach Growth Curve treat them as one series.
 */

import {
  CEMENT_SCRIPT,
  CEMENT_THRESHOLD,
  LOW_SCORE_THRESHOLD,
  RATINGS,
  RATING_RUBRIC,
  checklistFromSession,
  domainsBelow,
  frameworkFor,
  latestSnapshot,
  scoreSession,
  suggestReviewDates,
  type ChecklistState,
  type CmwDataset,
  type ElementKey,
  type Framework,
  type Rating,
  type Uuid,
} from '@cmw/core';
import { AlertCircle, Check, CheckCircle2, Circle, MinusCircle, Plus, Sparkles } from 'lucide-react';
import { useState } from 'react';

import { ProgressRing as Ring } from '../primitives/index.js';
import { hrefFor, navigate } from '../app/router.js';
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
  Button,
  Card,
  Chip,
  EmptyState,
  Numeric,
  Reveal,
  ScoreSlider,
  SectionHeader,
  TextArea,
  TextInput,
  cn,
  type Tone,
} from '../primitives/index.js';
import { PrepWhisperer } from './PrepWhisperer.js';
import { SessionAnalyzer } from './SessionAnalyzer.js';

const RATING_TONES: Record<Rating, Tone> = {
  Strong: 'success',
  Adequate: 'info',
  Weak: 'warn',
  Met: 'accent',
  'N/A': 'neutral',
};

export function SessionDetail({ data, id }: { data: CmwDataset; id: Uuid }) {
  const session = data.sessions.find((s) => s.id === id && !s.deleted_at);
  const [activeParticipant, setActiveParticipant] = useState(0);

  if (!session) {
    return (
      <EmptyState
        title="Session not found"
        body="This session may have been removed."
        action={
          <Button variant="quiet" onClick={() => navigate({ name: 'sessions' })}>
            Back to sessions
          </Button>
        }
      />
    );
  }

  const framework = frameworkFor(session.framework);
  const participantId = session.participants[Math.min(activeParticipant, session.participants.length - 1)];
  const coachee = participantId ? coacheeById(data, participantId) : undefined;

  const card = scoreSession({
    session,
    scores: scoresFor(data, session.id),
    ...(participantId ? { coachee_id: participantId } : {}),
  });

  const sessionActions = data.action_items.filter(
    (a) => a.session_id === session.id && !a.deleted_at,
  );

  const wheel = participantId ? latestSnapshot(wheelRowsFor(data, participantId), participantId) : null;

  const checklist = checklistFromSession({
    session,
    goals: participantId ? goalsFor(data, participantId) : [],
    actions: sessionActions,
    wheel,
  });

  const cementOwed = card.closing.cement_expected;

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm tracking-[0.14em] text-lo uppercase">{session.framework}</p>
          <h1 className="mt-1 font-display text-3xl text-hi">
            {session.participants
              .map((p) => coacheeById(data, p)?.name ?? 'Unknown')
              .join(' and ')}
          </h1>
          <p className="mt-1 text-sm text-lo">
            {session.date} · {session.duration_min} minutes · {framework.expansion}
          </p>
        </div>
        <Ring value={card.adherence_pct} size={72} label="Adherence" />
      </div>

      {/* A joint session grades each participant separately — never one pooled cycle. */}
      {session.participants.length > 1 ? (
        <Card className="mb-5">
          <p className="mb-2 text-sm font-medium text-hi">
            Joint session — grading {coachee?.name ?? 'participant'}'s cycle
          </p>
          <div className="flex flex-wrap gap-1.5">
            {session.participants.map((participant, index) => (
              <Chip
                key={participant}
                tone={index === activeParticipant ? 'accent' : 'neutral'}
                pressed={index === activeParticipant}
                onClick={() => setActiveParticipant(index)}
              >
                {coacheeById(data, participant)?.name ?? 'Unknown'}
              </Chip>
            ))}
          </div>
        </Card>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_21rem]">
        <div className="flex flex-col gap-6">
          <PrepCard
            data={data}
            sessionId={session.id}
            participantId={participantId}
            framework={session.framework}
          />

          {/* M6 — grades this cycle from her notes and proposes the scorecard. */}
          {coachee ? (
            <SessionAnalyzer
              session={session}
              coachee={coachee}
              participants={session.participants.flatMap((p) => {
                const found = coacheeById(data, p);
                return found ? [found] : [];
              })}
              goals={participantId ? goalsFor(data, participantId) : []}
              wheel={wheel}
              openActions={sessionActions.filter((a) => a.status !== 'done')}
            />
          ) : null}

          {/* ── The framework stepper ─────────────────────────────────── */}
          <section>
            <SectionHeader
              title="Framework"
              hint="Rate each element — the questions are your own bank"
            />
            <div className="flex flex-col gap-3">
              {card.lines.map((line) => {
                const definition = framework.elements.find((e) => e.key === line.element)!;
                return (
                  <ElementCard
                    key={line.element}
                    letter={line.letter}
                    label={line.label}
                    purpose={definition.purpose}
                    questions={definition.questions}
                    note={definition.note}
                    oftenSkipped={line.historically_skipped}
                    rating={line.rating}
                    notes={line.notes ?? ''}
                    onRate={(rating) => {
                      if (!participantId) return;
                      void useStore
                        .getState()
                        .rateElement(session.id, participantId, line.element, rating);
                    }}
                    onClear={() => {
                      if (!participantId) return;
                      void useStore
                        .getState()
                        .clearElementRating(session.id, participantId, line.element);
                    }}
                    onNotes={(notes) => {
                      if (!participantId || !line.rating) return;
                      void useStore
                        .getState()
                        .rateElement(session.id, participantId, line.element, line.rating, notes);
                    }}
                  />
                );
              })}
            </div>
          </section>

          {/* ── Close ─────────────────────────────────────────────────── */}
          <section>
            <SectionHeader title="Closing" hint="Confidence and commitment, then the review date" />
            <Card>
              <div className="grid gap-5 sm:grid-cols-2">
                <ScoreSlider
                  label="Confidence"
                  value={session.confidence ?? null}
                  onChange={(confidence) =>
                    void useStore.getState().updateSession(session.id, { confidence })
                  }
                />
                <ScoreSlider
                  label="Commitment"
                  value={session.commitment ?? null}
                  onChange={(commitment) =>
                    void useStore.getState().updateSession(session.id, { commitment })
                  }
                />
              </div>

              {/*
                The closing script, in full, exactly when it is owed. The
                compendium records this as historically skipped — a nudge that
                says "use the script" does not help at the moment she needs
                the words.
              */}
              {cementOwed ? (
                <Reveal>
                  <div className="mt-5 rounded-md border border-success/40 bg-[color-mix(in_srgb,var(--cmw-success)_8%,var(--cmw-surface))] p-4">
                    <p className="flex items-center gap-2 text-sm font-medium text-success-ink">
                      <Sparkles size={15} />
                      Both at {CEMENT_THRESHOLD} or above — cement the agreement out loud
                    </p>
                    <ul className="mt-3 flex flex-col gap-1.5">
                      {CEMENT_SCRIPT.map((line) => (
                        <li key={line} className="text-sm text-hi">
                          {line}
                        </li>
                      ))}
                    </ul>
                  </div>
                </Reveal>
              ) : session.confidence !== null && session.commitment !== null ? (
                <p className="mt-4 text-sm text-lo">
                  Below {CEMENT_THRESHOLD} on one or both — worth asking what would move that
                  number before you close.
                </p>
              ) : null}

              <ReviewDates sessionId={session.id} dates={session.review_dates} date={session.date} />

              <div className="mt-5 border-t border-edge pt-4">
                <TextArea
                  label="Session summary"
                  value={session.summary ?? ''}
                  onChange={(summary) =>
                    void useStore.getState().updateSession(session.id, { summary })
                  }
                  rows={4}
                  placeholder="What happened, what shifted, what you noticed."
                />
              </div>
            </Card>
          </section>

          <ActionsBlock
            data={data}
            sessionId={session.id}
            participantId={participantId}
            sessionDate={session.date}
          />
        </div>

        {/* ── Sidebar: checklist and low scores ─────────────────────────── */}
        <div className="flex flex-col gap-4">
          <Card>
            <SectionHeader title="Reminders" hint="Graded from this session" />
            <ul className="flex flex-col gap-3">
              {checklist.lines.map((line) => (
                <li key={line.item} className="flex gap-2.5">
                  <ChecklistIcon state={line.state} />
                  <div className="min-w-0">
                    <p
                      className={cn(
                        'text-sm',
                        line.state === 'fail' ? 'text-hi' : 'text-lo',
                      )}
                    >
                      {line.label}
                    </p>
                    <p className="mt-0.5 text-xs text-lo">{line.detail}</p>
                  </div>
                </li>
              ))}
            </ul>
            <p
              className={cn(
                'mt-4 border-t border-edge pt-3 text-sm',
                checklist.all_clear ? 'text-success-ink' : 'text-warn-ink',
              )}
            >
              {checklist.all_clear
                ? 'All clear — nothing outstanding on this session.'
                : `${checklist.failed} item${checklist.failed === 1 ? '' : 's'} to close out.`}
            </p>
          </Card>

          {/* Low wheel scores, ready to flag as the honesty they are. */}
          {wheel ? (
            <Card>
              <SectionHeader
                title="Low scores"
                hint={`At or below ${LOW_SCORE_THRESHOLD}/10`}
              />
              {domainsBelow(wheel, LOW_SCORE_THRESHOLD).length === 0 ? (
                <p className="text-sm text-lo">
                  Nothing low on the latest wheel — this item is not applicable.
                </p>
              ) : (
                <>
                  <p className="mb-3 text-sm text-lo">
                    Tick each one you named in the room. Naming a low score as honesty is the
                    reframe.
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {domainsBelow(wheel, LOW_SCORE_THRESHOLD).map((domain) => {
                      const flagged = (session.flagged_domains ?? []).includes(domain);
                      return (
                        <Chip
                          key={domain}
                          tone={flagged ? 'success' : 'warn'}
                          pressed={flagged}
                          icon={flagged ? <Check size={12} /> : undefined}
                          onClick={() =>
                            void useStore.getState().toggleFlaggedDomain(session.id, domain)
                          }
                        >
                          {domain}
                        </Chip>
                      );
                    })}
                  </div>
                </>
              )}
            </Card>
          ) : null}

          {card.weakest.length > 0 || card.strongest.length > 0 ? (
            <Card>
              <SectionHeader title="This session" />
              {card.strongest.length > 0 ? (
                <p className="text-sm text-hi">
                  Strongest:{' '}
                  <span className="text-success-ink">
                    {card.strongest
                      .map((key) => card.lines.find((l) => l.element === key)?.label)
                      .join(', ')}
                  </span>
                </p>
              ) : null}
              {card.weakest.length > 0 ? (
                <p className="mt-1 text-sm text-hi">
                  Weakest:{' '}
                  <span className="text-warn-ink">
                    {card.weakest
                      .map((key) => card.lines.find((l) => l.element === key)?.label)
                      .join(', ')}
                  </span>
                </p>
              ) : null}
              <p className="mt-2 text-xs text-lo">
                {card.counted_elements} of {card.lines.length} elements graded.
              </p>
            </Card>
          ) : null}
        </div>
      </div>
    </div>
  );
}

// ── Prep card ─────────────────────────────────────────────────────────────

function PrepCard({
  data,
  sessionId,
  participantId,
  framework,
}: {
  data: CmwDataset;
  sessionId: Uuid;
  participantId: Uuid | undefined;
  framework: Framework;
}) {
  if (!participantId) return null;

  const coachee = coacheeById(data, participantId);
  const history = sessionsFor(data, participantId).filter((s) => s.id !== sessionId);
  const previous = history[0];
  const open = actionsFor(data, participantId).filter((a) => a.status !== 'done');

  // The Whisperer can brief a first session from goals and the wheel alone, so
  // the card now earns its place even with no history to summarise.
  if (!previous && open.length === 0 && !coachee) return null;

  return (
    <Card>
      <SectionHeader title="Prep" hint="Where you left off" />
      {previous ? (
        <p className="text-sm text-hi">
          Last session {previous.date}:{' '}
          <span className="text-lo">{previous.summary ?? 'no summary recorded'}</span>
        </p>
      ) : null}
      {open.length > 0 ? (
        <div className="mt-3">
          <p className="text-sm font-medium text-hi">Still open</p>
          <ul className="mt-1 flex flex-col gap-1">
            {open.slice(0, 4).map((action) => (
              <li key={action.id} className="text-sm text-lo">
                · {action.title}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {coachee ? (
        <PrepWhisperer
          data={data}
          coachee={coachee}
          framework={framework}
          previous={previous ?? null}
          openActions={open}
        />
      ) : null}
    </Card>
  );
}

// ── Element card ──────────────────────────────────────────────────────────

function ElementCard({
  letter,
  label,
  purpose,
  questions,
  note,
  oftenSkipped,
  rating,
  notes,
  onRate,
  onClear,
  onNotes,
}: {
  letter: string;
  label: string;
  purpose: string;
  questions: string[];
  note?: string;
  oftenSkipped: boolean;
  rating: Rating | null;
  notes: string;
  onRate: (rating: Rating) => void;
  onClear: () => void;
  onNotes: (notes: string) => void;
}) {
  const [draft, setDraft] = useState(notes);
  const [showNotes, setShowNotes] = useState(false);

  return (
    <Card>
      <div className="flex items-start gap-3">
        <span
          aria-hidden="true"
          className="cmw-numeric flex size-9 shrink-0 items-center justify-center rounded-md bg-accent-quiet text-lg font-semibold text-accent-ink"
        >
          {letter}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-display text-lg text-hi">{label}</h3>
            {/* Marked as data, not as prose — see frameworks.ts. */}
            {oftenSkipped ? (
              <Chip tone="warn" title="A step this framework records you as tending to skip">
                often skipped
              </Chip>
            ) : null}
          </div>
          <p className="mt-0.5 text-sm text-lo">{purpose}</p>
        </div>
      </div>

      <ul className="mt-3 flex flex-col gap-1.5 border-l-2 border-edge pl-3">
        {questions.map((question) => (
          <li key={question} className="text-sm text-hi">
            {question}
          </li>
        ))}
      </ul>

      {note ? (
        <p className="mt-3 rounded-md bg-raised p-2.5 text-sm text-lo">{note}</p>
      ) : null}

      <div className="mt-4 flex flex-wrap items-center gap-1.5">
        {RATINGS.map((option) => (
          <Chip
            key={option}
            tone={rating === option ? RATING_TONES[option] : 'neutral'}
            pressed={rating === option}
            title={RATING_RUBRIC[option]}
            onClick={() => (rating === option ? onClear() : onRate(option))}
          >
            {option}
          </Chip>
        ))}
        <Button
          variant="ghost"
          className="ml-auto min-h-9 px-2 text-xs"
          onClick={() => setShowNotes((current) => !current)}
        >
          {showNotes ? 'Hide note' : notes ? 'Edit note' : 'Add note'}
        </Button>
      </div>

      {showNotes ? (
        <Reveal>
          <div className="mt-3">
            <TextArea
              label="Evidence and notes"
              value={draft}
              onChange={setDraft}
              rows={3}
              placeholder="What you actually said or heard here."
            />
            <div className="mt-2 flex justify-end">
              <Button
                variant="quiet"
                onClick={() => {
                  onNotes(draft);
                  setShowNotes(false);
                }}
                disabled={!rating}
                title={rating ? undefined : 'Rate this element first'}
              >
                Save note
              </Button>
            </div>
          </div>
        </Reveal>
      ) : null}
    </Card>
  );
}

// ── Review dates ──────────────────────────────────────────────────────────

function ReviewDates({
  sessionId,
  dates,
  date,
}: {
  sessionId: Uuid;
  dates: string[];
  date: string;
}) {
  const [wednesday, saturday] = suggestReviewDates(date);

  const set = (next: string[]): void => {
    void useStore.getState().updateSession(sessionId, { review_dates: next });
  };

  return (
    <div className="mt-5 border-t border-edge pt-4">
      <p className="text-sm font-medium text-hi">Review dates</p>
      <p className="mt-0.5 text-sm text-lo">
        Set before closing. Your rhythm is the coming Wednesday and the Saturday after.
      </p>
      <div className="mt-2.5 flex flex-wrap gap-1.5">
        {dates.map((existing) => (
          <Chip
            key={existing}
            tone="accent"
            onClick={() => set(dates.filter((d) => d !== existing))}
            title="Remove this review date"
          >
            {existing} ×
          </Chip>
        ))}
        {!dates.includes(wednesday) ? (
          <Chip tone="neutral" onClick={() => set([...dates, wednesday])}>
            + Wed {wednesday.slice(5)}
          </Chip>
        ) : null}
        {!dates.includes(saturday) ? (
          <Chip tone="neutral" onClick={() => set([...dates, saturday])}>
            + Sat {saturday.slice(5)}
          </Chip>
        ) : null}
      </div>
    </div>
  );
}

// ── Actions from this session ─────────────────────────────────────────────

function ActionsBlock({
  data,
  sessionId,
  participantId,
  sessionDate,
}: {
  data: CmwDataset;
  sessionId: Uuid;
  participantId: Uuid | undefined;
  sessionDate: string;
}) {
  const [title, setTitle] = useState('');
  const [review, setReview] = useState(suggestReviewDates(sessionDate)[0]);
  const actions = data.action_items.filter((a) => a.session_id === sessionId && !a.deleted_at);

  const add = async (): Promise<void> => {
    if (!participantId || title.trim().length < 3) return;
    await useStore.getState().addAction({
      coachee_id: participantId,
      session_id: sessionId,
      title,
      review_date: review,
    });
    setTitle('');
  };

  return (
    <section>
      <SectionHeader
        title="Actions"
        hint="The Will step — dated, with a review date"
      />
      <Card>
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-48 flex-1">
            <TextInput
              label="What will they do?"
              value={title}
              onChange={setTitle}
              placeholder="Walk 20 minutes before work, Monday to Thursday"
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

        {actions.length > 0 ? (
          <ul className="mt-4 flex flex-col gap-2 border-t border-edge pt-4">
            {actions.map((action) => (
              <li key={action.id} className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className={cn('text-sm text-hi', action.status === 'done' && 'line-through opacity-70')}>
                    {action.title}
                  </p>
                  <p className="mt-0.5 text-xs text-lo">
                    {action.review_date ? `Review ${action.review_date}` : 'No review date'}
                  </p>
                </div>
                <div className="flex shrink-0 gap-1">
                  <Button
                    variant="ghost"
                    className="min-h-9 px-2 text-xs"
                    onClick={() =>
                      void useStore
                        .getState()
                        .setActionStatus(action.id, action.status === 'done' ? 'open' : 'done')
                    }
                  >
                    {action.status === 'done' ? 'Reopen' : 'Done'}
                  </Button>
                  <a
                    href={hrefFor({ name: 'client', id: action.coachee_id, tab: 'actions' })}
                    className="inline-flex min-h-9 items-center px-2 text-xs text-lo hover:text-hi"
                  >
                    Open
                  </a>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-sm text-warn-ink">
            No action yet — a session without a Will step is the most common way progress stalls.
          </p>
        )}
      </Card>
    </section>
  );
}

function ChecklistIcon({ state }: { state: ChecklistState }) {
  // Icon and shape carry the state as well as colour (§4.7).
  if (state === 'pass') {
    return <CheckCircle2 size={17} className="mt-0.5 shrink-0 text-success-ink" aria-label="Pass" />;
  }
  if (state === 'fail') {
    return <AlertCircle size={17} className="mt-0.5 shrink-0 text-warn-ink" aria-label="Not done" />;
  }
  return (
    <MinusCircle size={17} className="mt-0.5 shrink-0 text-lo" aria-label="Not applicable" />
  );
}
