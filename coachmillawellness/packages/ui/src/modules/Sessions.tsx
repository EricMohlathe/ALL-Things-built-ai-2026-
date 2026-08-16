/**
 * M2 — SESSION ENGINE (index + new session).
 *
 * A joint session links two or more coachees and each participant keeps their own
 * full cycle (Appendix A's joint-session rule), so the picker here is
 * multi-select rather than a single dropdown — the data model allows it and
 * collapsing it in the UI would quietly break the rule.
 */

import {
  FRAMEWORK_NAMES,
  frameworkFor,
  scoreSession,
  toIsoDate,
  type CmwDataset,
  type Framework,
  type Uuid,
} from '@cmw/core';
import { Plus } from 'lucide-react';
import { useState } from 'react';

import { hrefFor, navigate } from '../app/router.js';
import { allSessions, liveCoachees, scoresFor, useStore } from '../app/store.js';
import {
  Avatar,
  Button,
  Card,
  Chip,
  EmptyState,
  Modal,
  PageHeader,
  ProgressRing,
  Reveal,
  Select,
  TextInput,
  cn,
} from '../primitives/index.js';

export function Sessions({ data, openNew }: { data: CmwDataset; openNew: boolean }) {
  const [creating, setCreating] = useState(openNew);
  const sessions = allSessions(data);
  const coachees = liveCoachees(data);

  const nameOf = (id: Uuid): string => coachees.find((c) => c.id === id)?.name ?? 'Unknown';

  return (
    <div>
      <PageHeader
        eyebrow="Session engine"
        title="Sessions"
        subtitle="Every session graded against your own framework — adherence per element, the reminders checklist, and the actions that came out of it."
        action={
          <Button variant="primary" icon={<Plus size={16} />} onClick={() => setCreating(true)}>
            Log a session
          </Button>
        }
      />

      {coachees.length === 0 ? (
        <EmptyState
          title="Add a coachee first"
          body="A session needs someone to be with. Add your first coachee and come back."
          action={
            <Button variant="primary" onClick={() => navigate({ name: 'clients' })}>
              Go to clients
            </Button>
          }
        />
      ) : sessions.length === 0 ? (
        <EmptyState
          title="No sessions yet"
          body="Log your first session to get an adherence scorecard, the SMARTER checklist, and dated actions with review dates."
          action={
            <Button variant="primary" icon={<Plus size={16} />} onClick={() => setCreating(true)}>
              Log a session
            </Button>
          }
        />
      ) : (
        <ul className="flex flex-col gap-2">
          {sessions.map((session, index) => {
            const card = scoreSession({ session, scores: scoresFor(data, session.id) });
            return (
              <li key={session.id}>
                <Reveal delay={Math.min(index, 8) * 0.04}>
                  <a href={hrefFor({ name: 'session', id: session.id })}>
                    <Card interactive>
                      <div className="flex items-center gap-4">
                        <div className="flex -space-x-2">
                          {session.participants.slice(0, 3).map((participant) => (
                            <Avatar key={participant} name={nameOf(participant)} size={34} />
                          ))}
                        </div>

                        <div className="min-w-0 flex-1">
                          <p className="truncate font-medium text-hi">
                            {session.participants.map((id) => nameOf(id)).join(' and ')}
                          </p>
                          <p className="mt-0.5 text-sm text-lo">
                            {session.date} · {session.framework} · {session.duration_min} min
                          </p>
                          <div className="mt-2 flex flex-wrap gap-1.5">
                            {!card.complete ? (
                              <Chip tone="warn">
                                {card.unscored.length} element
                                {card.unscored.length === 1 ? '' : 's'} ungraded
                              </Chip>
                            ) : null}
                            {card.closing.cement_expected ? (
                              <Chip tone="success">Cement the agreement</Chip>
                            ) : null}
                            {session.review_dates.length === 0 ? (
                              <Chip tone="warn">No review date</Chip>
                            ) : null}
                          </div>
                        </div>

                        <ProgressRing value={card.adherence_pct} size={56} />
                      </div>
                    </Card>
                  </a>
                </Reveal>
              </li>
            );
          })}
        </ul>
      )}

      <NewSessionModal
        open={creating}
        onClose={() => {
          setCreating(false);
          if (openNew) navigate({ name: 'sessions' });
        }}
        data={data}
      />
    </div>
  );
}

function NewSessionModal({
  open,
  onClose,
  data,
}: {
  open: boolean;
  onClose: () => void;
  data: CmwDataset;
}) {
  const coachees = liveCoachees(data);
  const [participants, setParticipants] = useState<Uuid[]>([]);
  const [framework, setFramework] = useState<Framework>('GROW');
  const [date, setDate] = useState(toIsoDate(new Date()));
  const [durationMin, setDurationMin] = useState('60');
  const [error, setError] = useState<string | undefined>();

  const toggle = (id: Uuid): void => {
    setParticipants((current) =>
      current.includes(id) ? current.filter((p) => p !== id) : [...current, id],
    );
    setError(undefined);
  };

  const submit = async (): Promise<void> => {
    if (participants.length === 0) {
      setError('Pick at least one coachee.');
      return;
    }
    const id = await useStore.getState().addSession({
      participants,
      framework,
      date,
      duration_min: Number(durationMin) || 60,
    });
    setParticipants([]);
    onClose();
    navigate({ name: 'session', id });
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Log a session"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" onClick={submit}>
            Start session
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <div>
          <p className="mb-2 text-sm font-medium text-hi">Who was in the room?</p>
          <div className="flex flex-wrap gap-1.5">
            {coachees.map((coachee) => (
              <Chip
                key={coachee.id}
                tone={participants.includes(coachee.id) ? 'accent' : 'neutral'}
                pressed={participants.includes(coachee.id)}
                onClick={() => toggle(coachee.id)}
              >
                {coachee.name}
              </Chip>
            ))}
          </div>
          {participants.length > 1 ? (
            <p className="mt-2 text-sm text-info-ink">
              Joint session — each participant gets their own full {framework} cycle to grade.
            </p>
          ) : null}
          {error ? (
            <p className="mt-2 text-sm text-danger-ink" role="alert">
              {error}
            </p>
          ) : null}
        </div>

        <Select
          label="Framework"
          value={framework}
          options={FRAMEWORK_NAMES.map((name) => ({
            value: name,
            label: `${name} — ${frameworkFor(name).expansion}`,
          }))}
          onChange={setFramework}
        />

        <div className="grid grid-cols-2 gap-3">
          <TextInput label="Date" type="date" value={date} onChange={setDate} />
          <TextInput
            label="Duration (minutes)"
            type="number"
            value={durationMin}
            onChange={setDurationMin}
          />
        </div>
      </div>
    </Modal>
  );
}
