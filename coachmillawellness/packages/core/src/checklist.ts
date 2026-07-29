/**
 * The ✅ reminders checklist (Appendix A), auto-graded.
 *
 * This is the piece of her existing manual Claude workflow with the clearest
 * rules, so it is the piece that should never need the AI at all. Four items,
 * each with an honest `na` state — a checklist that reports `fail` for a
 * condition that never arose trains her to ignore it.
 */

import { LOW_SCORE_THRESHOLD, SMARTER_FLAGS, SMARTER_OFTEN_MISSED } from './frameworks.js';
import type {
  ActionItem,
  ChecklistItem,
  ChecklistState,
  Goal,
  Session,
  SmarterFlags,
  Uuid,
  WheelSnapshot,
} from './types.js';

export interface ChecklistLine {
  item: ChecklistItem;
  label: string;
  state: ChecklistState;
  /** Why it landed this way, in language she can act on. */
  detail: string;
}

export interface ChecklistResult {
  session_id: Uuid;
  lines: ChecklistLine[];
  passed: number;
  failed: number;
  na: number;
  /** No failures. `na` items do not spoil a clear run. */
  all_clear: boolean;
  /** Low domains present in the wheel but not named during Reality. */
  unflagged_low_domains: string[];
  /** SMARTER letters missing across the session's goals. */
  missing_smarter: string[];
}

export interface ChecklistInput {
  session: Session;
  /** Goals belonging to this session's participants. */
  goals: Goal[];
  /** Actions created from this session. */
  actions: ActionItem[];
  /** The wheel snapshot in play during Reality, if there was one. */
  wheel?: WheelSnapshot | null;
}

const LABELS: Record<ChecklistItem, string> = {
  smarter_met: 'SMARTER goals met — including Exciting and Rewarded, named out loud',
  low_scores_flagged: 'Low Wheel scores flagged as a good sign',
  will_step: 'Ended with a Will / Take-action step',
  review_date_set: 'Review date set before closing',
};

export function missingSmarterFlags(smarter: SmarterFlags): string[] {
  return SMARTER_FLAGS.filter((f) => !smarter[f.key as keyof SmarterFlags]).map((f) => f.key);
}

export function smarterComplete(goal: Goal): boolean {
  return missingSmarterFlags(goal.smarter).length === 0;
}

export function checklistFromSession(input: ChecklistInput): ChecklistResult {
  const { session, goals, actions, wheel } = input;

  const sessionActions = actions.filter((a) => a.session_id === session.id && !a.deleted_at);
  const openGoals = goals.filter((g) => !g.deleted_at && g.status === 'open');

  // ── SMARTER ──────────────────────────────────────────────────────────
  const missingByGoal = openGoals.map((g) => missingSmarterFlags(g.smarter));
  const missingSmarter = [...new Set(missingByGoal.flat())];
  const smarterState: ChecklistState =
    openGoals.length === 0 ? 'na' : missingSmarter.length === 0 ? 'pass' : 'fail';
  const oftenMissed = missingSmarter.filter((k) =>
    (SMARTER_OFTEN_MISSED as readonly string[]).includes(k),
  );
  const smarterDetail =
    smarterState === 'na'
      ? 'No open goals attached to this session yet.'
      : smarterState === 'pass'
        ? `All seven letters named across ${openGoals.length} goal${openGoals.length === 1 ? '' : 's'}.`
        : oftenMissed.length > 0
          ? `Missing ${labelsFor(missingSmarter)} — ${labelsFor(oftenMissed)} ${
              oftenMissed.length === 1
                ? 'is the one that usually goes unnamed.'
                : 'are the ones that usually go unnamed.'
            }`
          : `Missing ${labelsFor(missingSmarter)}.`;

  // ── Low wheel scores ─────────────────────────────────────────────────
  const lowDomains = (wheel?.domains ?? [])
    .filter((d) => d.score <= LOW_SCORE_THRESHOLD)
    .map((d) => d.domain);
  const flagged = new Set(session.flagged_domains ?? []);
  const unflaggedLow = lowDomains.filter((d) => !flagged.has(d));
  const lowState: ChecklistState =
    lowDomains.length === 0 ? 'na' : unflaggedLow.length < lowDomains.length ? 'pass' : 'fail';
  const lowDetail =
    lowState === 'na'
      ? wheel
        ? `Nothing at or below ${LOW_SCORE_THRESHOLD}/10 — no low scores to reframe.`
        : 'No wheel scored in this session.'
      : lowState === 'pass'
        ? unflaggedLow.length === 0
          ? `All ${lowDomains.length} low domain${lowDomains.length === 1 ? '' : 's'} named.`
          : `Named ${lowDomains.length - unflaggedLow.length} of ${lowDomains.length}. Still unnamed: ${unflaggedLow.join(', ')}.`
        : `${lowDomains.join(', ')} ${lowDomains.length === 1 ? 'is' : 'are'} at or below ${LOW_SCORE_THRESHOLD}/10 and went unnamed. Naming a low score as honesty is the reframe.`;

  // ── Will / Take-action step ──────────────────────────────────────────
  const willState: ChecklistState = sessionActions.length > 0 ? 'pass' : 'fail';
  const willDetail =
    willState === 'pass'
      ? `${sessionActions.length} action${sessionActions.length === 1 ? '' : 's'} committed.`
      : 'No action item came out of this session — the Will step did not land.';

  // ── Review date ──────────────────────────────────────────────────────
  // Satisfied either by a session-level review date or by every action
  // carrying its own. Both are the same discipline expressed differently.
  const actionsWithReview = sessionActions.filter((a) => Boolean(a.review_date));
  const everyActionReviewed =
    sessionActions.length > 0 && actionsWithReview.length === sessionActions.length;
  const reviewState: ChecklistState =
    session.review_dates.length > 0 || everyActionReviewed ? 'pass' : 'fail';
  const reviewDetail =
    reviewState === 'pass'
      ? session.review_dates.length > 0
        ? `Review set for ${session.review_dates.join(' and ')}.`
        : 'Every action carries its own review date.'
      : sessionActions.length === 0
        ? 'No review date, and no actions to hang one on.'
        : `${sessionActions.length - actionsWithReview.length} of ${sessionActions.length} actions have no review date.`;

  const lines: ChecklistLine[] = [
    { item: 'smarter_met', label: LABELS.smarter_met, state: smarterState, detail: smarterDetail },
    {
      item: 'low_scores_flagged',
      label: LABELS.low_scores_flagged,
      state: lowState,
      detail: lowDetail,
    },
    { item: 'will_step', label: LABELS.will_step, state: willState, detail: willDetail },
    {
      item: 'review_date_set',
      label: LABELS.review_date_set,
      state: reviewState,
      detail: reviewDetail,
    },
  ];

  return {
    session_id: session.id,
    lines,
    passed: lines.filter((l) => l.state === 'pass').length,
    failed: lines.filter((l) => l.state === 'fail').length,
    na: lines.filter((l) => l.state === 'na').length,
    all_clear: lines.every((l) => l.state !== 'fail'),
    unflagged_low_domains: unflaggedLow,
    missing_smarter: missingSmarter,
  };
}

/**
 * Renders flag keys as their human labels. Filtering the canonical list rather
 * than mapping the input also fixes the order — "Exciting and Rewarded" always
 * reads in SMARTER order regardless of how the missing keys were collected.
 */
function labelsFor(keys: string[]): string {
  const labels = SMARTER_FLAGS.filter((f) => keys.includes(f.key)).map((f) => f.label);
  if (labels.length <= 1) return labels.join('');
  return `${labels.slice(0, -1).join(', ')} and ${labels[labels.length - 1]!}`;
}
