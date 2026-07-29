/**
 * Command Deck composition (§2 M0) — the 8-second answer to "what does today
 * need from me?".
 *
 * Assembled here as a pure function so the Deck screen is a renderer with no
 * logic of its own, and so the same summary can feed the Monday digest (§9) and
 * the mobile nudge scheduler (M8) without any of them re-deriving it.
 */

import {
  coacheeRisk,
  overdueReviews,
  reviewsDueToday,
  reviewsDueWithin,
  sessionStreakWeeks,
  type CoacheeRisk,
} from './actions.js';
import { publishStreak } from './coherence.js';
import { toIsoDate } from './dates.js';
import { firstName } from './people.js';
import type {
  ActionItem,
  Coachee,
  ContentItem,
  IsoDate,
  Session,
  WheelSnapshotRow,
} from './types.js';

export type GreetingKey = 'morning' | 'afternoon' | 'evening';

export interface DeckSummary {
  date: IsoDate;
  greeting: GreetingKey;
  today_sessions: Session[];
  next_session: Session | null;
  overdue_reviews: ActionItem[];
  reviews_due_today: ActionItem[];
  reviews_due_soon: ActionItem[];
  content_due_today: ContentItem[];
  session_streak_weeks: number;
  publish_streak_days: number;
  at_risk: CoacheeRisk[];
  /** One sentence. Deterministic in v1; the Copilot replaces it in P2 (§9). */
  focus: string;
  /** True when there is genuinely nothing to do — earns a real empty state. */
  all_clear: boolean;
}

export interface DeckInput {
  coachees: Coachee[];
  sessions: Session[];
  actions: ActionItem[];
  content: ContentItem[];
  wheels?: WheelSnapshotRow[];
  now?: IsoDate;
  /** Local hour, 0–23. Drives the greeting only. */
  hour?: number;
}

export function greetingFor(hour: number): GreetingKey {
  if (hour < 12) return 'morning';
  if (hour < 17) return 'afternoon';
  return 'evening';
}

export function buildDeck(input: DeckInput): DeckSummary {
  const today = input.now ?? toIsoDate(new Date());
  const hour = input.hour ?? new Date().getHours();

  const liveSessions = input.sessions.filter((s) => !s.deleted_at);
  const todaySessions = liveSessions
    .filter((s) => s.date === today)
    .sort((a, b) => a.id.localeCompare(b.id));

  const nextSession =
    liveSessions
      .filter((s) => s.date > today)
      .sort((a, b) => a.date.localeCompare(b.date))[0] ?? null;

  const overdue = overdueReviews(input.actions, today);
  const dueToday = reviewsDueToday(input.actions, today);
  const dueSoon = reviewsDueWithin(input.actions, 7, today).filter(
    (a) => a.review_date !== today,
  );

  const contentDue = input.content.filter(
    (c) =>
      !c.deleted_at &&
      c.publish_date === today &&
      c.status !== 'posted' &&
      c.status !== 'analyzed',
  );

  const risks = input.coachees
    .filter((c) => !c.deleted_at && c.status === 'active')
    .map((c) => coacheeRisk(c.id, input.actions, today))
    .filter((r) => r.level !== 'none')
    .sort((a, b) => b.days_slipped - a.days_slipped);

  const allClear =
    todaySessions.length === 0 &&
    overdue.length === 0 &&
    dueToday.length === 0 &&
    contentDue.length === 0;

  return {
    date: today,
    greeting: greetingFor(hour),
    today_sessions: todaySessions,
    next_session: nextSession,
    overdue_reviews: overdue,
    reviews_due_today: dueToday,
    reviews_due_soon: dueSoon,
    content_due_today: contentDue,
    session_streak_weeks: sessionStreakWeeks(liveSessions, today),
    publish_streak_days: publishStreak(input.content, { now: today }).current,
    at_risk: risks,
    focus: focusSentence({
      todaySessions,
      overdue,
      dueToday,
      contentDue,
      risks,
      coachees: input.coachees,
      allClear,
    }),
    all_clear: allClear,
  };
}

/**
 * The "Focus for today" line.
 *
 * §2 specifies this as AI-generated, and P2 wires the Copilot to it. Shipping a
 * deterministic version first is not a placeholder: it means the Deck is useful
 * on day one with no API key, it gives the AI a quality bar to beat, and it
 * keeps working when she is offline or over her monthly budget cap.
 *
 * Ordering is a priority ladder — a session about to happen outranks admin, and
 * a slipped review outranks a content slot, because a person is waiting on one
 * and an algorithm on the other.
 */
function focusSentence(input: {
  todaySessions: Session[];
  overdue: ActionItem[];
  dueToday: ActionItem[];
  contentDue: ContentItem[];
  risks: CoacheeRisk[];
  coachees: Coachee[];
  allClear: boolean;
}): string {
  const nameOf = (id: string): string => {
    const found = input.coachees.find((c) => c.id === id);
    return found ? firstName(found.name) : 'your coachee';
  };

  if (input.todaySessions.length > 0) {
    const first = input.todaySessions[0]!;
    const who = first.participants.map(nameOf).join(' and ');
    const rest = input.todaySessions.length - 1;
    const tail = rest > 0 ? `, then ${rest} more session${rest === 1 ? '' : 's'}` : '';
    return `${first.framework} with ${who} today${tail} — open the prep card before you start.`;
  }

  if (input.risks.length > 0) {
    const worst = input.risks[0]!;
    return `${nameOf(worst.coachee_id)} needs a nudge — ${worst.reason?.toLowerCase()}.`;
  }

  if (input.overdue.length > 0) {
    const n = input.overdue.length;
    return `${n} review${n === 1 ? '' : 's'} slipped past their date. Clear those first.`;
  }

  if (input.dueToday.length > 0) {
    const n = input.dueToday.length;
    return `${n} action${n === 1 ? ' is' : 's are'} up for review today — a quick pass keeps the rhythm.`;
  }

  if (input.contentDue.length > 0) {
    const first = input.contentDue[0]!;
    return `"${first.title}" is scheduled for today and still sitting at ${first.status}.`;
  }

  return 'No sessions, no slipped reviews, nothing due. Use the space to get ahead on content.';
}
