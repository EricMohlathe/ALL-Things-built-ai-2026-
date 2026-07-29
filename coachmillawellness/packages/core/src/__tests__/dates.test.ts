import { describe, expect, it } from 'vitest';

import {
  SATURDAY,
  WEDNESDAY,
  addDays,
  dateRange,
  dayStart,
  daysBetween,
  isAfter,
  isBefore,
  isIsoDate,
  monthKey,
  nextWeekday,
  relativeDay,
  suggestReviewDates,
  toIsoDate,
  toIsoDateTime,
  weekdayOf,
} from '../dates.js';

describe('isIsoDate', () => {
  it('accepts real calendar days', () => {
    expect(isIsoDate('2026-07-30')).toBe(true);
    expect(isIsoDate('2024-02-29')).toBe(true);
  });

  it('rejects malformed strings and dates that do not exist', () => {
    expect(isIsoDate('2026-7-30')).toBe(false);
    expect(isIsoDate('30-07-2026')).toBe(false);
    expect(isIsoDate('')).toBe(false);
    // Would silently roll forward to 1 March if handed straight to Date.
    expect(isIsoDate('2026-02-30')).toBe(false);
    expect(isIsoDate('2026-13-01')).toBe(false);
  });
});

describe('conversion', () => {
  it('passes a calendar date through untouched', () => {
    expect(toIsoDate('2026-07-30')).toBe('2026-07-30');
  });

  it('narrows an instant to its UTC calendar day', () => {
    expect(toIsoDate('2026-07-30T22:45:00.000Z')).toBe('2026-07-30');
    expect(toIsoDate(new Date('2026-07-30T05:00:00.000Z'))).toBe('2026-07-30');
  });

  it('produces full UTC instants', () => {
    expect(toIsoDateTime(new Date('2026-07-30T10:00:00.000Z'))).toBe('2026-07-30T10:00:00.000Z');
    expect(toIsoDateTime(0)).toBe('1970-01-01T00:00:00.000Z');
    expect(toIsoDateTime()).toMatch(/^\d{4}-\d{2}-\d{2}T/);
  });

  it('anchors a calendar day at midnight UTC', () => {
    expect(dayStart('2026-07-30').toISOString()).toBe('2026-07-30T00:00:00.000Z');
  });
});

describe('arithmetic', () => {
  it('adds and subtracts days across month and year boundaries', () => {
    expect(addDays('2026-07-30', 3)).toBe('2026-08-02');
    expect(addDays('2026-01-01', -1)).toBe('2025-12-31');
    expect(addDays('2024-02-28', 1)).toBe('2024-02-29');
    expect(addDays('2026-07-30', 0)).toBe('2026-07-30');
  });

  it('counts whole days in both directions', () => {
    expect(daysBetween('2026-07-01', '2026-07-30')).toBe(29);
    expect(daysBetween('2026-07-30', '2026-07-01')).toBe(-29);
    expect(daysBetween('2026-07-30', '2026-07-30')).toBe(0);
  });

  it('compares calendar days as strings', () => {
    expect(isBefore('2026-07-01', '2026-07-30')).toBe(true);
    expect(isBefore('2026-07-30', '2026-07-01')).toBe(false);
    expect(isAfter('2026-07-30', '2026-07-01')).toBe(true);
    expect(isAfter('2026-07-01', '2026-07-30')).toBe(false);
  });

  it('lists an inclusive range and nothing for a backwards one', () => {
    expect(dateRange('2026-07-28', '2026-07-30')).toEqual([
      '2026-07-28',
      '2026-07-29',
      '2026-07-30',
    ]);
    expect(dateRange('2026-07-30', '2026-07-30')).toEqual(['2026-07-30']);
    expect(dateRange('2026-07-30', '2026-07-28')).toEqual([]);
  });

  it('buckets by month', () => {
    expect(monthKey('2026-07-30')).toBe('2026-07');
  });
});

describe('weekdays and her review rhythm', () => {
  it('knows the weekday of a date', () => {
    // 2026-07-30 is a Thursday.
    expect(weekdayOf('2026-07-30')).toBe(4);
  });

  it('always moves strictly forward, never landing on the same day', () => {
    // A review date equal to the session date is not a review — it is the session.
    expect(nextWeekday('2026-07-29', WEDNESDAY)).toBe('2026-08-05');
    expect(nextWeekday('2026-07-30', WEDNESDAY)).toBe('2026-08-05');
    expect(nextWeekday('2026-07-30', SATURDAY)).toBe('2026-08-01');
  });

  it('suggests the coming Wednesday and the Saturday after it', () => {
    const [wednesday, saturday] = suggestReviewDates('2026-07-30');
    expect(wednesday).toBe('2026-08-05');
    expect(saturday).toBe('2026-08-08');
    expect(weekdayOf(wednesday)).toBe(WEDNESDAY);
    expect(weekdayOf(saturday)).toBe(SATURDAY);
    expect(saturday > wednesday).toBe(true);
  });

  it('keeps the pair in order even when the session is on a Wednesday', () => {
    const [wednesday, saturday] = suggestReviewDates('2026-08-05');
    expect(wednesday).toBe('2026-08-12');
    expect(saturday).toBe('2026-08-15');
  });
});

describe('relativeDay', () => {
  it('reads naturally for the days around now', () => {
    expect(relativeDay('2026-07-30', '2026-07-30')).toBe('today');
    expect(relativeDay('2026-07-30', '2026-07-31')).toBe('tomorrow');
    expect(relativeDay('2026-07-30', '2026-07-29')).toBe('yesterday');
    expect(relativeDay('2026-07-30', '2026-08-03')).toBe('in 4 days');
    expect(relativeDay('2026-07-30', '2026-07-27')).toBe('3 days ago');
  });
});
