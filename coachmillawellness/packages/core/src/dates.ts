/**
 * Date helpers. Deliberately dependency-free — `packages/core` stays pure so it
 * can run in a browser, a Tauri Rust host's webview, React Native and a Node
 * test runner without carrying a date library into every bundle.
 *
 * Everything works in UTC. Calendar dates are compared as `YYYY-MM-DD` strings,
 * which sorts and equates correctly without ever constructing a local-time Date
 * — the bug that makes a review date land a day early for half the year.
 */

import type { IsoDate, IsoDateTime } from './types.js';

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

export function isIsoDate(value: string): boolean {
  if (!ISO_DATE.test(value)) return false;
  const time = Date.parse(`${value}T00:00:00.000Z`);
  if (Number.isNaN(time)) return false;
  // Rejects 2026-02-30, which Date.parse would otherwise roll forward.
  return new Date(time).toISOString().slice(0, 10) === value;
}

export function toIsoDate(value: Date | IsoDateTime | IsoDate): IsoDate {
  if (typeof value === 'string') {
    if (ISO_DATE.test(value)) return value;
    return new Date(value).toISOString().slice(0, 10);
  }
  return value.toISOString().slice(0, 10);
}

export function toIsoDateTime(value: Date | number = new Date()): IsoDateTime {
  return new Date(value).toISOString();
}

/** Midnight UTC on the given calendar day. */
export function dayStart(date: IsoDate): Date {
  return new Date(`${date}T00:00:00.000Z`);
}

export function addDays(date: IsoDate, days: number): IsoDate {
  const d = dayStart(date);
  d.setUTCDate(d.getUTCDate() + days);
  return toIsoDate(d);
}

/** Whole days from `a` to `b`. Negative when `b` is earlier. */
export function daysBetween(a: IsoDate, b: IsoDate): number {
  const ms = dayStart(b).getTime() - dayStart(a).getTime();
  return Math.round(ms / 86_400_000);
}

export function isBefore(a: IsoDate, b: IsoDate): boolean {
  return a < b;
}

export function isAfter(a: IsoDate, b: IsoDate): boolean {
  return a > b;
}

/** 0 = Sunday … 6 = Saturday, matching `Date.prototype.getUTCDay`. */
export type Weekday = 0 | 1 | 2 | 3 | 4 | 5 | 6;

export const WEDNESDAY: Weekday = 3;
export const SATURDAY: Weekday = 6;

export function weekdayOf(date: IsoDate): Weekday {
  return dayStart(date).getUTCDay() as Weekday;
}

/**
 * The next occurrence of `weekday` strictly after `from`. Strictly, because a
 * review date set on the same day as the session is not a review — it is the
 * session.
 */
export function nextWeekday(from: IsoDate, weekday: Weekday): IsoDate {
  const current = weekdayOf(from);
  const delta = (weekday - current + 7) % 7 || 7;
  return addDays(from, delta);
}

/**
 * Her review rhythm from Appendix A: the coming Wednesday, then the Saturday
 * after it. Returned as a pair so "review date set before closing" can be
 * satisfied with one tap.
 */
export function suggestReviewDates(sessionDate: IsoDate): [IsoDate, IsoDate] {
  const wednesday = nextWeekday(sessionDate, WEDNESDAY);
  const saturday = nextWeekday(wednesday, SATURDAY);
  return [wednesday, saturday];
}

/** Inclusive list of calendar days from `start` to `end`. */
export function dateRange(start: IsoDate, end: IsoDate): IsoDate[] {
  const span = daysBetween(start, end);
  if (span < 0) return [];
  return Array.from({ length: span + 1 }, (_, i) => addDays(start, i));
}

/** `YYYY-MM` — the bucket key for monthly trend charts. */
export function monthKey(date: IsoDate): string {
  return date.slice(0, 7);
}

/** Human-facing relative day, for "review slipped 3 days ago" copy. */
export function relativeDay(from: IsoDate, to: IsoDate): string {
  const days = daysBetween(from, to);
  if (days === 0) return 'today';
  if (days === 1) return 'tomorrow';
  if (days === -1) return 'yesterday';
  if (days > 0) return `in ${days} days`;
  return `${Math.abs(days)} days ago`;
}
