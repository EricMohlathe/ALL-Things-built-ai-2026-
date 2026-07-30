/**
 * M1 — COACHEE CONSTELLATION (index).
 *
 * A card per human, each carrying the four things she needs before opening
 * anyone: who they are, where their wheel sits, when they are next in, and
 * whether a review has slipped. The risk flag is the reason this page exists in
 * this shape — it is the earliest visible sign that someone is drifting.
 */

import { coacheeRisk, latestSnapshot, toIsoDate, wheelAverage, type CmwDataset } from '@cmw/core';
import { Plus, Search } from 'lucide-react';
import { useMemo, useState } from 'react';

import { MiniWheel } from '../charts/index.js';
import { hrefFor } from '../app/router.js';
import { actionsFor, liveCoachees, sessionsFor, wheelRowsFor } from '../app/store.js';
import {
  Avatar,
  Button,
  Card,
  Chip,
  EmptyState,
  Modal,
  Numeric,
  PageHeader,
  Reveal,
  TextInput,
  cn,
} from '../primitives/index.js';

type StatusFilter = 'all' | 'active' | 'paused' | 'alumni';

const FILTERS: Array<{ value: StatusFilter; label: string }> = [
  { value: 'all', label: 'All' },
  { value: 'active', label: 'Active' },
  { value: 'paused', label: 'Paused' },
  { value: 'alumni', label: 'Alumni' },
];

export function Clients({
  data,
  onAdd,
}: {
  data: CmwDataset;
  onAdd: (input: { name: string; package?: string; contact?: string }) => Promise<string>;
}) {
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState<StatusFilter>('all');
  const [adding, setAdding] = useState(false);

  const coachees = liveCoachees(data);
  const today = toIsoDate(new Date());

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return coachees.filter((c) => {
      if (filter !== 'all' && c.status !== filter) return false;
      if (!needle) return true;
      return (
        c.name.toLowerCase().includes(needle) ||
        (c.package ?? '').toLowerCase().includes(needle) ||
        c.tags.some((t) => t.toLowerCase().includes(needle))
      );
    });
  }, [coachees, filter, query]);

  return (
    <div>
      <PageHeader
        eyebrow="Constellation"
        title="Clients"
        subtitle="Every coachee, their goals, wheel history, sessions and open actions — one screen per human."
        action={
          <Button variant="primary" icon={<Plus size={16} />} onClick={() => setAdding(true)}>
            Add coachee
          </Button>
        }
      />

      {coachees.length === 0 ? (
        <EmptyState
          title="No coachees yet"
          body="Add the first one and the Deck, the Wheel Lab and the session engine all come to life."
          action={
            <Button variant="primary" icon={<Plus size={16} />} onClick={() => setAdding(true)}>
              Add coachee
            </Button>
          }
        />
      ) : (
        <>
          <div className="mb-5 flex flex-wrap items-end gap-3">
            <div className="min-w-56 flex-1">
              <TextInput label="Search" value={query} onChange={setQuery} placeholder="Name, package or tag" />
            </div>
            <div className="flex flex-wrap gap-1.5 pb-1">
              {FILTERS.map((option) => (
                <Chip
                  key={option.value}
                  tone={filter === option.value ? 'accent' : 'neutral'}
                  pressed={filter === option.value}
                  onClick={() => setFilter(option.value)}
                >
                  {option.label}
                </Chip>
              ))}
            </div>
          </div>

          {visible.length === 0 ? (
            <EmptyState
              title="Nothing matches"
              body="No coachee matches that search and filter. Try clearing one of them."
              icon={<Search size={28} />}
              action={
                <Button
                  variant="quiet"
                  onClick={() => {
                    setQuery('');
                    setFilter('all');
                  }}
                >
                  Clear filters
                </Button>
              }
            />
          ) : (
            <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {visible.map((coachee, index) => {
                const snapshot = latestSnapshot(wheelRowsFor(data, coachee.id), coachee.id);
                const average = wheelAverage(snapshot);
                const risk = coacheeRisk(coachee.id, actionsFor(data, coachee.id), today);
                const sessions = sessionsFor(data, coachee.id);
                const open = actionsFor(data, coachee.id).filter((a) => a.status !== 'done');
                const upcoming = sessions.find((s) => s.date >= today);

                return (
                  <li key={coachee.id}>
                    <Reveal delay={Math.min(index, 8) * 0.04}>
                      <a href={hrefFor({ name: 'client', id: coachee.id, tab: 'overview' })} className="block h-full">
                        <Card interactive className="flex h-full flex-col">
                          <div className="flex items-start gap-3">
                            <Avatar name={coachee.name} />
                            <div className="min-w-0 flex-1">
                              <p className="truncate font-medium text-hi">{coachee.name}</p>
                              <p className="truncate text-sm text-lo">
                                {coachee.package ?? 'No package set'}
                              </p>
                            </div>
                            {snapshot ? (
                              <MiniWheel
                                scores={snapshot.domains.map((d) => d.score)}
                                title={`Wheel average ${average}`}
                              />
                            ) : null}
                          </div>

                          <div className="mt-3 flex flex-wrap gap-1.5">
                            <Chip
                              tone={
                                coachee.status === 'active'
                                  ? 'success'
                                  : coachee.status === 'paused'
                                    ? 'warn'
                                    : 'neutral'
                              }
                            >
                              {coachee.status}
                            </Chip>
                            {/* Risk is stated in words, never by colour alone. */}
                            {risk.level !== 'none' ? (
                              <Chip tone={risk.level === 'at_risk' ? 'danger' : 'warn'}>
                                {risk.level === 'at_risk' ? 'At risk' : 'Watch'}
                              </Chip>
                            ) : null}
                            {average !== null ? (
                              <Chip tone="neutral">
                                <Numeric>{average}</Numeric> avg
                              </Chip>
                            ) : null}
                          </div>

                          <dl className="mt-auto grid grid-cols-3 gap-2 border-t border-edge pt-3 text-xs">
                            <div>
                              <dt className="text-lo">Sessions</dt>
                              <dd className="cmw-numeric mt-0.5 text-hi">{sessions.length}</dd>
                            </div>
                            <div>
                              <dt className="text-lo">Open actions</dt>
                              <dd
                                className={cn(
                                  'cmw-numeric mt-0.5',
                                  risk.overdue_count > 0 ? 'text-warn-ink' : 'text-hi',
                                )}
                              >
                                {open.length}
                              </dd>
                            </div>
                            <div>
                              <dt className="text-lo">Next</dt>
                              <dd className="mt-0.5 truncate text-hi">
                                {upcoming ? upcoming.date.slice(5) : '—'}
                              </dd>
                            </div>
                          </dl>
                        </Card>
                      </a>
                    </Reveal>
                  </li>
                );
              })}
            </ul>
          )}
        </>
      )}

      <AddCoacheeModal open={adding} onClose={() => setAdding(false)} onAdd={onAdd} />
    </div>
  );
}

function AddCoacheeModal({
  open,
  onClose,
  onAdd,
}: {
  open: boolean;
  onClose: () => void;
  onAdd: (input: { name: string; package?: string; contact?: string }) => Promise<string>;
}) {
  const [name, setName] = useState('');
  const [pkg, setPkg] = useState('');
  const [contact, setContact] = useState('');
  const [error, setError] = useState<string | undefined>();

  const submit = async (): Promise<void> => {
    if (name.trim().length < 2) {
      setError('A name needs at least two characters.');
      return;
    }
    const id = await onAdd({ name, package: pkg, contact });
    setName('');
    setPkg('');
    setContact('');
    setError(undefined);
    onClose();
    window.location.hash = hrefFor({ name: 'client', id, tab: 'overview' });
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Add a coachee"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" onClick={submit}>
            Add coachee
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <TextInput
          label="Name"
          value={name}
          onChange={(value) => {
            setName(value);
            setError(undefined);
          }}
          placeholder="Naledi Mokoena"
          error={error}
          hint="Client-facing pages show the first name only."
          onEnter={submit}
          autoFocus
        />
        <TextInput
          label="Package"
          value={pkg}
          onChange={setPkg}
          placeholder="12-session transformation"
          hint="Optional."
        />
        <TextInput
          label="Contact"
          value={contact}
          onChange={setContact}
          placeholder="Email or phone"
          hint="Optional. Stored on this device only."
        />
      </div>
    </Modal>
  );
}
