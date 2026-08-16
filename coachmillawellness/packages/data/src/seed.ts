/**
 * Sample data — fictional coachees only (§0, and law #8: never a real client
 * name in a repo).
 *
 * Two things this is careful about:
 *
 * 1. Ids are fixed, so loading the sample twice replaces it rather than
 *    duplicating it, and tests can assert on exact rows.
 * 2. Dates are relative to `now`, so the Deck is alive the moment she loads it —
 *    a session today, a review that slipped on Wednesday, a Reel due this
 *    afternoon. Hard-coded dates would show her an empty Deck and a Wheel that
 *    stopped moving months ago, which teaches her the app is dead.
 *
 * This is not loaded on first run. §2 M0 specifies a guided three-step empty
 * state for that; the sample is an explicit choice in the Vault, so her own
 * first coachee is never sitting next to two strangers.
 */

import {
  WHEEL_DOMAINS_DEFAULT,
  addDays,
  emptyDataset,
  suggestReviewDates,
  toIsoDate,
  toIsoDateTime,
  type CmwDataset,
  type SessionElementScore,
  type SmarterFlags,
} from '@cmw/core';

import { SETTING_KEYS } from './schema.js';

const NALEDI = '01917f00-0001-7000-8000-000000000001';
const THABO = '01917f00-0001-7000-8000-000000000002';

const P_MOMENTUM = '01917f00-0002-7000-8000-000000000001';
const P_BODY = '01917f00-0002-7000-8000-000000000002';
const P_BOUNDARIES = '01917f00-0002-7000-8000-000000000003';
const P_MONEY = '01917f00-0002-7000-8000-000000000004';

function flags(overrides: Partial<SmarterFlags> = {}): SmarterFlags {
  return { S: true, M: true, A: true, R: true, T: true, E: true, Rw: true, ...overrides };
}

export function seedDataset(now: Date = new Date()): CmwDataset {
  const today = toIsoDate(now);
  const stamp = toIsoDateTime(now);
  const dataset = emptyDataset();

  const lastSession = addDays(today, -14);
  const olderSession = addDays(today, -42);
  const firstWheel = addDays(today, -70);
  const [nextWednesday] = suggestReviewDates(today);

  dataset.coachees = [
    {
      id: NALEDI,
      name: 'Naledi M.',
      status: 'active',
      package: '12-session transformation',
      start_date: addDays(today, -98),
      tags: ['Client A', 'GROW'],
      contact: 'naledi@example.test',
      notes: 'Prefers early-morning sessions. Responds well to being asked what success looks like.',
      updated_at: stamp,
    },
    {
      id: THABO,
      name: 'Thabo K.',
      status: 'active',
      package: '6-session reset',
      start_date: addDays(today, -35),
      tags: ['Client B', 'GREAT'],
      contact: 'thabo@example.test',
      notes: 'Tends to answer "no, nothing" to the obstacle question. Push past it.',
      updated_at: stamp,
    },
  ];

  dataset.goals = [
    {
      id: '01917f00-0003-7000-8000-000000000001',
      coachee_id: NALEDI,
      statement: 'Run a 5km without walking by the end of the quarter',
      smarter: flags(),
      target_date: addDays(today, 60),
      status: 'open',
      updated_at: stamp,
    },
    {
      id: '01917f00-0003-7000-8000-000000000002',
      coachee_id: NALEDI,
      statement: 'Move my savings to a separate account each payday',
      // Deliberately missing Exciting and Rewarded — this is the gap the
      // checklist is built to make visible, so the sample shows it failing.
      smarter: flags({ E: false, Rw: false }),
      target_date: addDays(today, 90),
      status: 'open',
      updated_at: stamp,
    },
    {
      id: '01917f00-0003-7000-8000-000000000003',
      coachee_id: THABO,
      statement: 'Leave the office by 17:30 three days a week',
      smarter: flags({ Rw: false }),
      target_date: addDays(today, 45),
      status: 'open',
      updated_at: stamp,
    },
  ];

  const solo = '01917f00-0004-7000-8000-000000000001';
  const great = '01917f00-0004-7000-8000-000000000002';
  const joint = '01917f00-0004-7000-8000-000000000003';
  const todaySession = '01917f00-0004-7000-8000-000000000004';

  dataset.sessions = [
    {
      id: solo,
      date: olderSession,
      duration_min: 60,
      framework: 'GROW',
      participants: [NALEDI],
      summary:
        'Opened on the 5km goal. Wheel showed Health at 3 and Finances at 4 — named both as honest reporting. Options stayed narrow; we did not weigh them.',
      confidence: 7,
      commitment: 8,
      review_dates: [addDays(olderSession, 5)],
      flagged_domains: ['Health', 'Finances'],
      updated_at: stamp,
    },
    {
      id: great,
      date: lastSession,
      duration_min: 60,
      framework: 'GREAT',
      participants: [THABO],
      summary:
        'Heavy reflective listening on the workload reality. Negotiated a targeted HOW. Obstacle question got a dismissive answer and I let it stand.',
      confidence: 8,
      commitment: 9,
      review_dates: suggestReviewDates(lastSession),
      flagged_domains: ['Fun & Recreation'],
      updated_at: stamp,
    },
    {
      id: joint,
      date: addDays(today, -7),
      duration_min: 90,
      framework: 'GROW',
      // A joint session — each participant still gets their own full cycle.
      participants: [NALEDI, THABO],
      summary: 'Joint accountability session. Each ran their own GROW cycle on the same theme.',
      confidence: 9,
      commitment: 9,
      review_dates: [nextWednesday],
      updated_at: stamp,
    },
    {
      id: todaySession,
      date: today,
      duration_min: 60,
      framework: 'GROW',
      participants: [NALEDI],
      review_dates: [],
      updated_at: stamp,
    },
  ];

  let scoreIndex = 0;
  const graded = (
    fields: Omit<SessionElementScore, 'id' | 'updated_at'>,
  ): SessionElementScore => {
    scoreIndex += 1;
    return {
      id: `01917f00-0005-7000-8000-${String(scoreIndex).padStart(12, '0')}`,
      updated_at: stamp,
      ...fields,
    };
  };

  dataset.session_element_scores = [
    // The older GROW session: strong opening, weak Options — the pattern the
    // Coach Growth Curve is meant to surface over months.
    graded({
      session_id: solo,
      coachee_id: NALEDI,
      element: 'goal',
      rating: 'Adequate',
      notes: 'Session goal named, but no separate pass on what success looks like.',
      evidence: '"What would you like to take out of today?"',
    }),
    graded({
      session_id: solo,
      coachee_id: NALEDI,
      element: 'reality',
      rating: 'Strong',
      notes: 'Wheel scored across all ten domains, low scores reframed as honesty.',
    }),
    graded({
      session_id: solo,
      coachee_id: NALEDI,
      element: 'options',
      rating: 'Weak',
      notes: 'Two options generated, neither weighed. Pros and cons skipped.',
    }),
    graded({
      session_id: solo,
      coachee_id: NALEDI,
      element: 'will',
      rating: 'Met',
      notes: 'Commitment 8/10 honoured with a dated action, though the closing script went unused.',
    }),

    // The GREAT session: rapport is her signature strength, Achieve the gap.
    graded({ session_id: great, coachee_id: THABO, element: 'goals', rating: 'Strong' }),
    graded({
      session_id: great,
      coachee_id: THABO,
      element: 'reality_rapport',
      rating: 'Strong',
      notes: 'Reflective listening throughout — "what I\'m hearing you say" three times.',
    }),
    graded({ session_id: great, coachee_id: THABO, element: 'explore', rating: 'Adequate' }),
    graded({
      session_id: great,
      coachee_id: THABO,
      element: 'achieve',
      rating: 'Weak',
      notes: 'Obstacle question accepted "no, nothing" and moved on.',
    }),
    graded({
      session_id: great,
      coachee_id: THABO,
      element: 'take_action',
      rating: 'Strong',
      notes: 'Both scores ≥8 and the agreement was cemented out loud.',
    }),

    // The joint session, graded separately per participant — a shared session
    // must not collapse into one cycle (Appendix A).
    graded({ session_id: joint, coachee_id: NALEDI, element: 'goal', rating: 'Strong' }),
    graded({ session_id: joint, coachee_id: NALEDI, element: 'reality', rating: 'Strong' }),
    graded({ session_id: joint, coachee_id: NALEDI, element: 'options', rating: 'Adequate' }),
    graded({ session_id: joint, coachee_id: NALEDI, element: 'will', rating: 'Strong' }),
    graded({ session_id: joint, coachee_id: THABO, element: 'goal', rating: 'Adequate' }),
    graded({ session_id: joint, coachee_id: THABO, element: 'reality', rating: 'Strong' }),
    graded({ session_id: joint, coachee_id: THABO, element: 'options', rating: 'Weak' }),
    graded({ session_id: joint, coachee_id: THABO, element: 'will', rating: 'Met' }),
  ];

  // Three wheel snapshots for Naledi so the timeline scrubber has something to
  // morph between, and one for Thabo.
  dataset.wheel_snapshots = [
    ...wheelFor(NALEDI, firstWheel, [3, 4, 3, 7, 5, 6, 4, 6, 7, 5], stamp, 1),
    ...wheelFor(NALEDI, olderSession, [4, 4, 5, 7, 5, 7, 4, 6, 7, 6], stamp, 2),
    ...wheelFor(NALEDI, addDays(today, -7), [5, 6, 7, 8, 6, 8, 6, 7, 8, 7], stamp, 3),
    ...wheelFor(THABO, lastSession, [7, 6, 5, 6, 6, 5, 2, 6, 5, 4], stamp, 4),
  ];

  dataset.action_items = [
    {
      id: '01917f00-0007-7000-8000-000000000001',
      coachee_id: NALEDI,
      session_id: joint,
      title: 'Walk 20 minutes before work, Monday to Thursday',
      due_date: addDays(today, -2),
      // Slipped, so the client card carries a risk flag and the Deck a nudge.
      review_date: addDays(today, -3),
      status: 'open',
      updated_at: stamp,
    },
    {
      id: '01917f00-0007-7000-8000-000000000002',
      coachee_id: NALEDI,
      session_id: joint,
      title: 'Move R500 to the savings account on payday',
      due_date: addDays(today, 5),
      review_date: nextWednesday,
      status: 'open',
      updated_at: stamp,
    },
    {
      id: '01917f00-0007-7000-8000-000000000003',
      coachee_id: THABO,
      session_id: great,
      title: 'Block 17:30 in the calendar on Tuesday, Wednesday and Thursday',
      due_date: addDays(today, 3),
      review_date: today,
      status: 'in_review',
      updated_at: stamp,
    },
    {
      id: '01917f00-0007-7000-8000-000000000004',
      coachee_id: THABO,
      session_id: great,
      title: 'Tell one colleague about the 17:30 boundary',
      due_date: addDays(today, -10),
      review_date: addDays(today, -8),
      status: 'done',
      completed_at: toIsoDateTime(new Date(Date.parse(`${addDays(today, -9)}T09:00:00.000Z`))),
      updated_at: stamp,
    },
  ];

  dataset.pillars = [
    {
      id: P_MOMENTUM,
      name: 'Start before you are ready',
      color: '#9A7BFF',
      core_message: 'Action creates clarity. Waiting to feel ready is the trap.',
      keywords: ['momentum', 'start', 'imperfect action'],
      updated_at: stamp,
    },
    {
      id: P_BODY,
      name: 'Your body keeps the score',
      color: '#5FBF9F',
      core_message: 'Energy is the foundation every other goal is built on.',
      keywords: ['health', 'sleep', 'movement'],
      updated_at: stamp,
    },
    {
      id: P_BOUNDARIES,
      name: 'Boundaries are kindness',
      color: '#F5A524',
      core_message: 'A clear no protects the yes that matters.',
      keywords: ['boundaries', 'burnout', 'saying no'],
      updated_at: stamp,
    },
    {
      id: P_MONEY,
      name: 'Money is a habit, not a windfall',
      color: '#F87A6D',
      core_message: 'Small repeatable money moves beat one heroic decision.',
      keywords: ['finances', 'savings', 'habits'],
      updated_at: stamp,
    },
  ];

  dataset.content_items = [
    {
      id: '01917f00-0009-7000-8000-000000000001',
      title: 'The 20-minute rule',
      type: 'Reel',
      platform: 'IG',
      pillar_id: P_MOMENTUM,
      status: 'analyzed',
      hook: 'You do not need an hour. You need twenty minutes and your shoes on.',
      cta: 'Save this for tomorrow morning.',
      publish_date: addDays(today, -12),
      link: 'https://example.test/reel/20-minute-rule',
      metrics: { views: 8400, likes: 612, saves: 214, comments: 38 },
      updated_at: stamp,
    },
    {
      id: '01917f00-0009-7000-8000-000000000002',
      title: 'What your 3am wake-up is telling you',
      type: 'Video',
      platform: 'YouTube',
      pillar_id: P_BODY,
      status: 'posted',
      hook: 'Waking at 3am is not random.',
      cta: 'Full sleep reset in the description.',
      publish_date: addDays(today, -5),
      metrics: { views: 1900, likes: 145, saves: 61 },
      updated_at: stamp,
    },
    {
      id: '01917f00-0009-7000-8000-000000000003',
      title: 'Say no without the paragraph',
      type: 'Short',
      platform: 'TikTok',
      pillar_id: P_BOUNDARIES,
      status: 'posted',
      hook: 'Your no does not need a footnote.',
      cta: 'Try it once this week.',
      publish_date: addDays(today, -2),
      updated_at: stamp,
    },
    {
      id: '01917f00-0009-7000-8000-000000000004',
      title: 'The payday transfer',
      type: 'Reel',
      platform: 'IG',
      pillar_id: P_MONEY,
      // Scheduled for today and not out yet — the Deck's content widget.
      status: 'filmed',
      hook: 'Move it before you can feel it leave.',
      cta: 'Set the recurring transfer today.',
      publish_date: today,
      updated_at: stamp,
    },
    {
      id: '01917f00-0009-7000-8000-000000000005',
      title: 'Wheel of Life, explained in 60 seconds',
      type: 'Story',
      platform: 'WhatsApp Status',
      pillar_id: P_MOMENTUM,
      status: 'script',
      hook: 'Ten numbers that show you where your life actually is.',
      cta: 'DM me WHEEL for the template.',
      script:
        'Open on the wheel. Ten domains. Score each 0 to 10 — honestly, not aspirationally. The low ones are not failures, they are information.',
      publish_date: addDays(today, 3),
      updated_at: stamp,
    },
    {
      id: '01917f00-0009-7000-8000-000000000006',
      title: 'Why I ask "what does success look like"',
      type: 'Post',
      platform: 'LinkedIn',
      // No pillar yet — shows up as unassigned on the Coherence Map.
      pillar_id: null,
      status: 'idea',
      hook: 'The goal you name first is rarely the goal.',
      updated_at: stamp,
    },
  ];

  dataset.inquiries = [
    {
      id: '01917f00-000a-7000-8000-000000000001',
      date: addDays(today, -9),
      source: 'Instagram DM',
      pillar_guess: P_MOMENTUM,
      converted: true,
      updated_at: stamp,
    },
    {
      id: '01917f00-000a-7000-8000-000000000002',
      date: addDays(today, -4),
      source: 'Referral',
      pillar_guess: P_BOUNDARIES,
      converted: false,
      updated_at: stamp,
    },
  ];

  dataset.settings = [
    { key: SETTING_KEYS.theme, value: 'dawn', updated_at: stamp },
    { key: SETTING_KEYS.wheelDomains, value: [...WHEEL_DOMAINS_DEFAULT], updated_at: stamp },
    { key: SETTING_KEYS.onboardingComplete, value: true, updated_at: stamp },
    { key: SETTING_KEYS.lastBackupAt, value: null, updated_at: stamp },
  ];

  return dataset;
}

function wheelFor(
  coacheeId: string,
  date: string,
  scores: number[],
  stamp: string,
  group: number,
): CmwDataset['wheel_snapshots'] {
  // Targets sit a realistic distance above the score rather than all at 10 —
  // a ghost ring pinned at maximum tells her nothing.
  const targets = [8, 8, 9, 9, 8, 9, 7, 7, 8, 8];
  return WHEEL_DOMAINS_DEFAULT.map((domain, i) => ({
    id: `01917f00-0006-7${String(group).padStart(3, '0')}-8000-${String(i + 1).padStart(12, '0')}`,
    coachee_id: coacheeId,
    date,
    domain,
    score: scores[i] ?? 5,
    target: targets[i] ?? 8,
    updated_at: stamp,
  }));
}
