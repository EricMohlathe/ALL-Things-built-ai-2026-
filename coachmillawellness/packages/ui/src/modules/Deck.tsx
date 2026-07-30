/**
 * M0 — COMMAND DECK.
 *
 * One job: answer "what does today need from me?" in about eight seconds. So the
 * order of this page is a priority ladder, not a menu — a session about to happen
 * outranks admin, and a person waiting on a slipped review outranks a content
 * slot. `buildDeck` in @cmw/core decides that ordering; this file only renders it.
 */

import {
  buildDeck,
  firstName,
  frameworkFor,
  relativeDay,
  toIsoDate,
  type CmwDataset,
} from '@cmw/core';
import { AlertTriangle, ArrowRight, CalendarClock, Flame, Plus, Video } from 'lucide-react';

import { StatTile } from '../charts/index.js';
import {
  Button,
  Card,
  Chip,
  EmptyState,
  Numeric,
  Reveal,
  SectionHeader,
  cn,
} from '../primitives/index.js';
import { hrefFor } from '../app/router.js';
import { liveCoachees } from '../app/store.js';

const GREETINGS = {
  morning: 'Good morning',
  afternoon: 'Good afternoon',
  evening: 'Good evening',
} as const;

export function Deck({ data, onStart }: { data: CmwDataset; onStart: () => void }) {
  const coachees = liveCoachees(data);

  const deck = buildDeck({
    coachees: data.coachees,
    sessions: data.sessions,
    actions: data.action_items,
    content: data.content_items,
    now: toIsoDate(new Date()),
    hour: new Date().getHours(),
  });

  const nameOf = (id: string): string =>
    coachees.find((c) => c.id === id)?.name ?? 'Unknown coachee';

  if (coachees.length === 0) {
    return <FirstRun onStart={onStart} />;
  }

  return (
    <div>
      {/* Hero — greeting over a slow dawn sweep (§2 M0). */}
      <div className="relative mb-7 overflow-hidden rounded-lg border border-edge bg-surface px-5 py-6">
        <div className="cmw-dawn-sweep" aria-hidden="true" />
        <div className="relative">
          <p className="text-sm text-lo">
            {new Date().toLocaleDateString(undefined, {
              weekday: 'long',
              day: 'numeric',
              month: 'long',
            })}
          </p>
          <h1 className="mt-1 font-display text-3xl text-hi sm:text-4xl">
            {GREETINGS[deck.greeting]}
          </h1>
          <p className="mt-3 max-w-2xl text-lg text-hi">{deck.focus}</p>
        </div>
      </div>

      {/* Streaks and load, at a glance. */}
      <div className="mb-7 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile
          label="Session streak"
          value={
            <span className="flex items-baseline gap-1.5">
              {deck.session_streak_weeks}
              <span className="text-sm font-normal text-lo">
                {deck.session_streak_weeks === 1 ? 'week' : 'weeks'}
              </span>
            </span>
          }
          hint="Weeks in a row with a logged session"
          icon={
            <Flame
              size={13}
              className={cn(deck.session_streak_weeks > 0 && 'cmw-streak-live text-energy-ink')}
            />
          }
        />
        <StatTile
          label="Publishing streak"
          value={
            <span className="flex items-baseline gap-1.5">
              {deck.publish_streak_days}
              <span className="text-sm font-normal text-lo">
                {deck.publish_streak_days === 1 ? 'day' : 'days'}
              </span>
            </span>
          }
          hint="Consecutive days published"
          icon={<Video size={13} />}
        />
        <StatTile
          label="Reviews slipped"
          value={deck.overdue_reviews.length}
          hint={deck.overdue_reviews.length === 0 ? 'All on schedule' : 'Needs a pass today'}
          tone={deck.overdue_reviews.length > 0 ? 'warn-ink' : 'hi'}
          icon={<CalendarClock size={13} />}
        />
        <StatTile
          label="Active coachees"
          value={coachees.filter((c) => c.status === 'active').length}
          hint={`${coachees.length} in the constellation`}
          icon={<ArrowRight size={13} />}
        />
      </div>

      {deck.all_clear ? (
        <Reveal>
          <Card className="mb-7 border-success/40">
            <p className="text-hi">
              Nothing is waiting on you. No sessions today, no slipped reviews, nothing due.
            </p>
            <p className="mt-1 text-sm text-lo">
              This is the moment to get ahead on content rather than to find something to worry
              about.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button variant="quiet" onClick={() => (window.location.hash = hrefFor({ name: 'content' }))}>
                Open the content studio
              </Button>
            </div>
          </Card>
        </Reveal>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* ── Today's sessions ──────────────────────────────────────────── */}
        <section>
          <SectionHeader
            title="Today"
            hint={
              deck.today_sessions.length === 0
                ? deck.next_session
                  ? `Next session ${relativeDay(deck.date, deck.next_session.date)}`
                  : 'No sessions scheduled'
                : `${deck.today_sessions.length} session${deck.today_sessions.length === 1 ? '' : 's'}`
            }
            action={
              <Button
                variant="quiet"
                icon={<Plus size={16} />}
                onClick={() => (window.location.hash = hrefFor({ name: 'session-new' }))}
              >
                Log
              </Button>
            }
          />

          {deck.today_sessions.length === 0 ? (
            <Card>
              <p className="text-sm text-lo">
                {deck.next_session
                  ? `Your next session is ${relativeDay(deck.date, deck.next_session.date)} — ${deck.next_session.participants.map((id) => firstName(nameOf(id))).join(' and ')}.`
                  : 'Nothing on the calendar. Logging a past session works just as well.'}
              </p>
            </Card>
          ) : (
            <ul className="flex flex-col gap-2">
              {deck.today_sessions.map((session) => (
                <li key={session.id}>
                  <a href={hrefFor({ name: 'session', id: session.id })} className="block">
                    <Card interactive>
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate font-medium text-hi">
                            {session.participants.map((id) => firstName(nameOf(id))).join(' and ')}
                          </p>
                          <p className="mt-0.5 text-sm text-lo">
                            {frameworkFor(session.framework).expansion}
                          </p>
                        </div>
                        <Chip tone="accent">{session.framework}</Chip>
                      </div>
                    </Card>
                  </a>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* ── Reviews ───────────────────────────────────────────────────── */}
        <section>
          <SectionHeader
            title="Reviews"
            hint="The Wednesday and Saturday rhythm"
          />
          {deck.overdue_reviews.length === 0 && deck.reviews_due_today.length === 0 ? (
            <Card>
              <p className="text-sm text-lo">
                No reviews due or overdue.
                {deck.reviews_due_soon.length > 0
                  ? ` ${deck.reviews_due_soon.length} coming this week.`
                  : ''}
              </p>
            </Card>
          ) : (
            <ul className="flex flex-col gap-2">
              {deck.overdue_reviews.map((action) => (
                <li key={action.id}>
                  <a href={hrefFor({ name: 'client', id: action.coachee_id, tab: 'actions' })}>
                    <Card interactive className="border-warn/40">
                      <div className="flex items-start gap-3">
                        <AlertTriangle size={16} className="mt-0.5 shrink-0 text-warn-ink" />
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-hi">{action.title}</p>
                          <p className="mt-0.5 text-sm text-lo">
                            {firstName(nameOf(action.coachee_id))} · review was{' '}
                            {relativeDay(deck.date, action.review_date)}
                          </p>
                        </div>
                      </div>
                    </Card>
                  </a>
                </li>
              ))}
              {deck.reviews_due_today.map((action) => (
                <li key={action.id}>
                  <a href={hrefFor({ name: 'client', id: action.coachee_id, tab: 'actions' })}>
                    <Card interactive>
                      <div className="flex items-start gap-3">
                        <CalendarClock size={16} className="mt-0.5 shrink-0 text-accent-ink" />
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-hi">{action.title}</p>
                          <p className="mt-0.5 text-sm text-lo">
                            {firstName(nameOf(action.coachee_id))} · due for review today
                          </p>
                        </div>
                      </div>
                    </Card>
                  </a>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* ── Needs attention ──────────────────────────────────────────── */}
        {deck.at_risk.length > 0 ? (
          <section>
            <SectionHeader title="Needs a nudge" hint="Where retention is actually won" />
            <ul className="flex flex-col gap-2">
              {deck.at_risk.map((risk) => (
                <li key={risk.coachee_id}>
                  <a href={hrefFor({ name: 'client', id: risk.coachee_id, tab: 'overview' })}>
                    <Card interactive>
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate font-medium text-hi">
                            {nameOf(risk.coachee_id)}
                          </p>
                          <p className="mt-0.5 text-sm text-lo">{risk.reason}</p>
                        </div>
                        <Chip tone={risk.level === 'at_risk' ? 'danger' : 'warn'}>
                          {risk.level === 'at_risk' ? 'At risk' : 'Watch'}
                        </Chip>
                      </div>
                    </Card>
                  </a>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {/* ── Content due ──────────────────────────────────────────────── */}
        {deck.content_due_today.length > 0 ? (
          <section>
            <SectionHeader title="Due today" hint="Scheduled but not out yet" />
            <ul className="flex flex-col gap-2">
              {deck.content_due_today.map((item) => (
                <li key={item.id}>
                  <a href={hrefFor({ name: 'content' })}>
                    <Card interactive>
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate font-medium text-hi">{item.title}</p>
                          <p className="mt-0.5 text-sm text-lo">
                            {item.type} · {item.platform}
                          </p>
                        </div>
                        <Chip tone="warn">{item.status}</Chip>
                      </div>
                    </Card>
                  </a>
                </li>
              ))}
            </ul>
          </section>
        ) : null}
      </div>
    </div>
  );
}

/**
 * First run (§2 M0): a guided three-step setup rather than an empty dashboard.
 * The sample practice is offered beside it, because seeing a populated Deck is
 * the fastest way to understand what the app is for.
 */
function FirstRun({ onStart }: { onStart: () => void }) {
  const steps = [
    { n: 1, title: 'Add a coachee', body: 'One screen per human — goals, wheel, sessions, actions.' },
    { n: 2, title: 'Set your message pillars', body: 'Three to six. They become the coherence backbone.' },
    { n: 3, title: 'Log your first session', body: 'GROW or GREAT, scored against your own framework.' },
  ];

  return (
    <div>
      <div className="relative mb-7 overflow-hidden rounded-lg border border-edge bg-surface px-5 py-8">
        <div className="cmw-dawn-sweep" aria-hidden="true" />
        <div className="relative">
          <p className="text-sm tracking-[0.14em] text-lo uppercase">First light</p>
          <h1 className="mt-2 font-display text-3xl text-hi sm:text-4xl">
            Let's set up your practice
          </h1>
          <p className="mt-3 max-w-xl text-lo">
            Three steps and the Deck starts working for you. Everything stays on this device — no
            account, no subscription, and your data exports whenever you want it.
          </p>
        </div>
      </div>

      <ol className="mb-6 grid gap-3 sm:grid-cols-3">
        {steps.map((step, i) => (
          <li key={step.n}>
            <Reveal delay={i * 0.06}>
              <Card className="h-full">
                <Numeric className="text-2xl font-semibold text-accent-ink">
                  {String(step.n).padStart(2, '0')}
                </Numeric>
                <h2 className="mt-2 font-display text-lg text-hi">{step.title}</h2>
                <p className="mt-1 text-sm text-lo">{step.body}</p>
              </Card>
            </Reveal>
          </li>
        ))}
      </ol>

      <EmptyState
        title="No coachees yet"
        body="Add your first coachee to begin, or load a sample practice to see how everything fits together before you put real names in."
        action={
          <div className="flex flex-wrap justify-center gap-2">
            <Button
              variant="primary"
              icon={<Plus size={16} />}
              onClick={() => (window.location.hash = hrefFor({ name: 'clients' }))}
            >
              Add a coachee
            </Button>
            <Button variant="quiet" onClick={onStart}>
              Load the sample practice
            </Button>
          </div>
        }
      />
    </div>
  );
}
