/**
 * Fixtures for the AI tests.
 *
 * Fictional coachees only, and fixed dates — the same two rules the seed data
 * follows. Dates are in 2099 so no assertion here can start failing because the
 * real calendar moved past a window.
 */

import type {
  ActionItem,
  Coachee,
  ContentItem,
  Goal,
  Pillar,
  Session,
  WheelSnapshot,
} from '@cmw/core';

export const NOW = new Date('2099-03-10T08:00:00.000Z');
export const TODAY = '2099-03-10';

const stamp = { updated_at: '2099-03-01T00:00:00.000Z' };

export const naledi: Coachee = {
  id: 'c-naledi',
  name: 'Naledi Mokoena',
  status: 'active',
  start_date: '2099-01-05',
  tags: ['Client A'],
  contact: 'naledi@example.com',
  ...stamp,
};

export const thabo: Coachee = {
  id: 'c-thabo',
  name: 'Thabo Khumalo',
  status: 'active',
  start_date: '2099-01-12',
  tags: ['Client B'],
  ...stamp,
};

export const goal: Goal = {
  id: 'g-1',
  coachee_id: naledi.id,
  statement: 'Walk 30 minutes before work, four mornings a week',
  // Missing E and Rw on purpose — the gap the checklist exists to surface.
  smarter: { S: true, M: true, A: true, R: true, T: true, E: false, Rw: false },
  target_date: '2099-06-30',
  status: 'open',
  ...stamp,
};

export const session: Session = {
  id: 's-1',
  date: '2099-03-08',
  duration_min: 60,
  framework: 'GROW',
  participants: [naledi.id],
  summary: 'Naledi Mokoena named Health and Fun as her low domains.',
  confidence: 9,
  commitment: 8,
  review_dates: ['2099-03-11', '2099-03-14'],
  flagged_domains: ['Health'],
  ...stamp,
};

export const greatSession: Session = {
  ...session,
  id: 's-2',
  framework: 'GREAT',
  participants: [naledi.id, thabo.id],
};

export const action: ActionItem = {
  id: 'a-1',
  coachee_id: naledi.id,
  session_id: session.id,
  title: 'Book the Saturday parkrun',
  due_date: '2099-03-14',
  review_date: '2099-03-11',
  status: 'open',
  ...stamp,
};

export const wheel: WheelSnapshot = {
  coachee_id: naledi.id,
  date: '2099-03-08',
  domains: [
    { domain: 'Career', score: 7, target: 8 },
    { domain: 'Health', score: 3, target: 8 },
    { domain: 'Fun & Recreation', score: 4, target: 9 },
    { domain: 'Finances', score: 6, target: 7 },
  ],
};

export const pillar: Pillar = {
  id: 'p-1',
  name: 'Sustainable energy',
  color: '#8FB39B',
  core_message: 'Small daily habits beat heroic resets',
  keywords: ['habits', 'energy', 'sleep'],
  ...stamp,
};

export const content: ContentItem = {
  id: 'ct-1',
  title: 'The 5am myth',
  type: 'Reel',
  platform: 'IG',
  pillar_id: pillar.id,
  status: 'script',
  hook: 'You do not need a 5am alarm.',
  cta: 'Save this for Monday.',
  script: 'Everyone sells you the 5am club. Here is what actually moved the needle for my clients.',
  publish_date: '2099-03-12',
  link: null,
  metrics: null,
  ...stamp,
};

/** A contract-shaped Session Analyzer response, as the model would return it. */
export function analysisFixture(): Record<string, unknown> {
  return {
    elements: [
      { element: 'goal', rating: 'Adequate', evidence: '"what do you want from today"', note: 'Session goal named, deeper goal not asked.' },
      { element: 'reality', rating: 'Strong', evidence: '"what I am hearing you say"', note: 'Reflective listening throughout.' },
      { element: 'options', rating: 'Weak', evidence: 'Three options listed, none weighed.', note: 'Pros and cons never asked.' },
      { element: 'will', rating: 'Met', evidence: '9 and 8 out of 10.', note: 'Threshold met, closing script not used.' },
    ],
    checklist: {
      smarter_met: 'fail',
      low_scores_flagged: 'pass',
      will_step: 'pass',
      review_date_set: 'pass',
    },
    suggested_actions: [
      { title: 'Walk on Tuesday and Thursday mornings', due: '2099-03-14', review: '2099-03-11' },
      { title: 'Ask a friend to join the parkrun', due: 'next week', review: null },
    ],
    one_growth_tip: 'You listed options but never weighed them — ask for pros and cons next time.',
  };
}

export function coherenceFixture(): Record<string, unknown> {
  return {
    verdict: 'on',
    why: 'The hook rejects heroic resets, which is the pillar in one line.',
    one_line_fix: 'Name the one habit explicitly in the first five seconds.',
    suggested_hook: 'You do not need a 5am alarm. You need one thing you can repeat.',
  };
}

export function digestFixture(): Record<string, unknown> {
  return {
    clients_needing_attention: [{ first_name: 'Thabo', why: 'no session in three weeks' }],
    content_gaps: ['Nothing published under Sustainable energy in 30 days', ''],
    coach_tip: 'Options averaged 41% across four cycles — ask for pros and cons before you close.',
    focus_sentence: 'Two reviews slipped past their date. Clear those before you open anything else.',
  };
}

export function prepFixture(): Record<string, unknown> {
  return {
    recap_3_lines: [
      'Health sat at 3 and she called it honestly.',
      'Committed to four morning walks.',
      'Review was set for Wednesday.',
      'A fourth line the contract should trim.',
    ],
    suggested_opening_question: 'What would you like to take out of this session?',
    watchouts: ['The parkrun action has no review date.', ''],
  };
}
