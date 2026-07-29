/**
 * Test factories. Fictional coachees only — never a real client name in a repo
 * (§0, and law #8 of the prompt pack).
 */

import type {
  ActionItem,
  Coachee,
  ContentItem,
  Goal,
  Pillar,
  Session,
  SessionElementScore,
  SmarterFlags,
  WheelSnapshot,
  WheelSnapshotRow,
} from '../types.js';

let counter = 0;
export function id(prefix = 'id'): string {
  counter += 1;
  return `${prefix}-${String(counter).padStart(4, '0')}`;
}

export function resetIds(): void {
  counter = 0;
}

const AT = '2026-07-01T00:00:00.000Z';

export const NALEDI = 'coachee-naledi';
export const THABO = 'coachee-thabo';

export function smarter(overrides: Partial<SmarterFlags> = {}): SmarterFlags {
  return { S: true, M: true, A: true, R: true, T: true, E: true, Rw: true, ...overrides };
}

/**
 * The compendium's seed people are "Client A – Naledi M." and "Client B –
 * Thabo K.". The "Client A/B" part is the brief labelling them for us, not a
 * display name — storing it in the `name` field would make every greeting read
 * "GROW with Client today", so it lives in `tags` instead.
 */
export function coachee(overrides: Partial<Coachee> = {}): Coachee {
  return {
    id: NALEDI,
    name: 'Naledi M.',
    status: 'active',
    start_date: '2026-01-15',
    tags: [],
    updated_at: AT,
    ...overrides,
  };
}

export function goal(overrides: Partial<Goal> = {}): Goal {
  return {
    id: id('goal'),
    coachee_id: NALEDI,
    statement: 'Run 5km without stopping',
    smarter: smarter(),
    status: 'open',
    updated_at: AT,
    ...overrides,
  };
}

export function session(overrides: Partial<Session> = {}): Session {
  return {
    id: 'session-1',
    date: '2026-07-15',
    duration_min: 60,
    framework: 'GROW',
    participants: [NALEDI],
    review_dates: [],
    updated_at: AT,
    ...overrides,
  };
}

export function score(overrides: Partial<SessionElementScore> = {}): SessionElementScore {
  return {
    id: id('score'),
    session_id: 'session-1',
    coachee_id: NALEDI,
    element: 'goal',
    rating: 'Strong',
    updated_at: AT,
    ...overrides,
  };
}

export function action(overrides: Partial<ActionItem> = {}): ActionItem {
  return {
    id: id('action'),
    coachee_id: NALEDI,
    session_id: 'session-1',
    title: 'Walk 20 minutes before work',
    status: 'open',
    updated_at: AT,
    ...overrides,
  };
}

export function pillar(overrides: Partial<Pillar> = {}): Pillar {
  return {
    id: id('pillar'),
    name: 'Start Before You Are Ready',
    color: '#9A7BFF',
    core_message: 'Action creates clarity; waiting to feel ready is the trap.',
    keywords: ['momentum', 'start'],
    updated_at: AT,
    ...overrides,
  };
}

export function content(overrides: Partial<ContentItem> = {}): ContentItem {
  return {
    id: id('content'),
    title: 'The 20-minute rule',
    type: 'Reel',
    platform: 'IG',
    status: 'posted',
    publish_date: '2026-07-20',
    updated_at: AT,
    ...overrides,
  };
}

export function wheelRow(overrides: Partial<WheelSnapshotRow> = {}): WheelSnapshotRow {
  return {
    id: id('wheel'),
    coachee_id: NALEDI,
    date: '2026-07-15',
    domain: 'Health',
    score: 5,
    target: 8,
    updated_at: AT,
    ...overrides,
  };
}

/** Builds a snapshot from `[domain, score, target]` triples. */
export function snapshot(
  date: string,
  domains: Array<[string, number, number]>,
  coacheeId = NALEDI,
): WheelSnapshot {
  return {
    coachee_id: coacheeId,
    date,
    domains: domains.map(([domain, s, target]) => ({ domain, score: s, target })),
  };
}
