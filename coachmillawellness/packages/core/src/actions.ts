/**
 * Action items and the review-date discipline (§2 M1, M0).
 *
 * `review_date` is first-class in the schema, and this module is why: her
 * practice is built on setting a specific review date before closing, so a
 * slipped review is the single most useful risk signal in the product. It
 * drives the Deck's overdue widget, the client card's risk flag and (in P4) the
 * review-date push notification.
 */

import { addDays, daysBetween, toIsoDate } from './dates.js';
import type { ActionItem, IsoDate, Session, Uuid } from './types.js';

function live(actions: ActionItem[]): ActionItem[] {
  return actions.filter((a) => !a.deleted_at);
}

function outstanding(actions: ActionItem[]): ActionItem[] {
  return live(actions).filter((a) => a.status !== 'done');
}

/**
 * Narrowing the optional date once, here, keeps every query below to a single
 * comparison — and means the sort never needs an `?? ''` for a value the filter
 * has already guaranteed.
 */
/** An action that definitely carries a review date. */
export type Reviewable = ActionItem & { review_date: IsoDate };
export type Dated = ActionItem & { due_date: IsoDate };

function withReview(actions: ActionItem[]): Reviewable[] {
  return outstanding(actions).filter((a): a is Reviewable => Boolean(a.review_date));
}

function byReviewDate(a: Reviewable, b: Reviewable): number {
  return a.review_date.localeCompare(b.review_date);
}

/** Review date has passed and the action is still not done. */
export function overdueReviews(actions: ActionItem[], now?: IsoDate): Reviewable[] {
  const today = now ?? toIsoDate(new Date());
  return withReview(actions)
    .filter((a) => a.review_date < today)
    .sort(byReviewDate);
}

export function reviewsDueToday(actions: ActionItem[], now?: IsoDate): Reviewable[] {
  const today = now ?? toIsoDate(new Date());
  return withReview(actions).filter((a) => a.review_date === today);
}

export function reviewsDueWithin(
  actions: ActionItem[],
  days: number,
  now?: IsoDate,
): Reviewable[] {
  const today = now ?? toIsoDate(new Date());
  const horizon = addDays(today, days);
  return withReview(actions)
    .filter((a) => a.review_date >= today && a.review_date <= horizon)
    .sort(byReviewDate);
}

export function overdueDue(actions: ActionItem[], now?: IsoDate): Dated[] {
  const today = now ?? toIsoDate(new Date());
  return outstanding(actions)
    .filter((a): a is Dated => Boolean(a.due_date))
    .filter((a) => a.due_date < today)
    .sort((a, b) => a.due_date.localeCompare(b.due_date));
}

/** Actions with no review date at all — the discipline gap, not a slip. */
export function missingReviewDate(actions: ActionItem[]): ActionItem[] {
  return outstanding(actions).filter((a) => !a.review_date);
}

export interface CompletionStats {
  total: number;
  done: number;
  open: number;
  in_review: number;
  /** 0–1 across all non-deleted actions. `null` when there are none. */
  rate: number | null;
}

export function actionCompletionRate(actions: ActionItem[]): CompletionStats {
  const all = live(actions);
  const done = all.filter((a) => a.status === 'done').length;
  return {
    total: all.length,
    done,
    open: all.filter((a) => a.status === 'open').length,
    in_review: all.filter((a) => a.status === 'in_review').length,
    rate: all.length === 0 ? null : Number((done / all.length).toFixed(4)),
  };
}

// ── Risk ──────────────────────────────────────────────────────────────────

export type RiskLevel = 'none' | 'watch' | 'at_risk';

export interface CoacheeRisk {
  coachee_id: Uuid;
  level: RiskLevel;
  /** Plain-language reason, ready to render on the client card. */
  reason: string | null;
  days_slipped: number;
  overdue_count: number;
}

/**
 * Risk flag for the client card (§2 M1).
 *
 * Thresholds are deliberately gentle: one review a day late is a normal week,
 * not a crisis. `watch` starts at a day slipped, `at_risk` at a week — or as
 * soon as three reviews are outstanding at once, because volume is its own
 * signal even when nothing has slipped far.
 */
export function coacheeRisk(
  coacheeId: Uuid,
  actions: ActionItem[],
  now?: IsoDate,
): CoacheeRisk {
  const today = now ?? toIsoDate(new Date());
  const mine = actions.filter((a) => a.coachee_id === coacheeId);
  const overdue = overdueReviews(mine, today);

  if (overdue.length === 0) {
    return { coachee_id: coacheeId, level: 'none', reason: null, days_slipped: 0, overdue_count: 0 };
  }

  const oldest = overdue[0]!.review_date;
  const slipped = daysBetween(oldest, today);
  const level: RiskLevel = slipped >= 7 || overdue.length >= 3 ? 'at_risk' : 'watch';
  const plural = overdue.length === 1 ? 'review' : 'reviews';

  return {
    coachee_id: coacheeId,
    level,
    reason:
      overdue.length === 1
        ? `Review slipped ${slipped} day${slipped === 1 ? '' : 's'} ago`
        : `${overdue.length} ${plural} outstanding, oldest ${slipped} days ago`,
    days_slipped: slipped,
    overdue_count: overdue.length,
  };
}

// ── Streaks ───────────────────────────────────────────────────────────────

/**
 * Consecutive weeks with at least one logged session, counting back from the
 * current week.
 *
 * Weekly rather than daily on purpose: a coach running 60-minute sessions does
 * not work daily, so a daily streak would read as broken during a perfectly
 * healthy week and quietly train her to distrust the number.
 */
export function sessionStreakWeeks(sessions: Session[], now?: IsoDate): number {
  const today = now ?? toIsoDate(new Date());
  const weeks = new Set(
    sessions.filter((s) => !s.deleted_at).map((s) => weekKey(s.date)),
  );
  let streak = 0;
  for (let i = 0; ; i += 1) {
    if (!weeks.has(weekKey(addDays(today, -7 * i)))) break;
    streak += 1;
  }
  return streak;
}

/** ISO-ish week bucket: the Monday of the week containing `date`. */
export function weekKey(date: IsoDate): IsoDate {
  const day = new Date(`${date}T00:00:00.000Z`).getUTCDay();
  const backToMonday = (day + 6) % 7;
  return addDays(date, -backToMonday);
}
