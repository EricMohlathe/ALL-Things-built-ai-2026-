/**
 * HER METHODOLOGY — Appendix A, as data.
 *
 * This file is the reason the product beats a generic coaching app: the AI
 * grades against *her* frameworks, and the Session Engine surfaces *her*
 * questions. Both read from here, so there is exactly one copy of her practice
 * in the system.
 *
 * The `historically_skipped` flag is the sharpest thing in this file. The
 * compendium records which moves she tends to drop — the deeper-goal pass, the
 * pros-and-cons question, obstacle-proofing past a dismissive answer, and the
 * closing script. Marking them as data lets the UI lift them prominently
 * instead of leaving them buried in a question list she can scroll past.
 */

import type { ElementKey, Framework, Rating } from './types.js';

export interface FrameworkElement {
  key: ElementKey;
  /** Letter shown in the stepper: G, R, O, W / G, R, E, A, T. */
  letter: string;
  label: string;
  /** What this step is actually for, in one line, for the prep card. */
  purpose: string;
  questions: string[];
  /** A move the compendium records her as tending to skip. Surface it loudly. */
  historically_skipped?: boolean;
  /** Coaching note shown alongside the questions during live capture. */
  note?: string;
}

export interface FrameworkDefinition {
  name: Framework;
  label: string;
  /** Expansion, for headers and the AI system prompt. */
  expansion: string;
  elements: FrameworkElement[];
}

const REALITY_QUESTIONS = [
  'Wheel of Life scores across the 10 domains — is there anything that stands out to you?',
  'How does that make you feel?',
  "If I recall… what's happening now?",
  "What I'm hearing you say…",
];

export const GROW: FrameworkDefinition = {
  name: 'GROW',
  label: 'GROW',
  expansion: 'Goal → Reality → Options → Will',
  elements: [
    {
      key: 'goal',
      letter: 'G',
      label: 'Goal',
      purpose: 'Name what this hour is for — and then the goal underneath it.',
      questions: [
        'What would you like to take out of this session?',
        "What's your number one goal for today?",
        'What does success look like?',
      ],
      historically_skipped: true,
      note: 'The deeper goal needs its own explicit pass. "What does success look like?" is not a rephrase of the session goal — ask it separately.',
    },
    {
      key: 'reality',
      letter: 'R',
      label: 'Reality',
      purpose: 'Score the wheel, then work the emotional reality behind the numbers.',
      questions: REALITY_QUESTIONS,
      note: 'Low scores are a good sign — name them as honesty, not failure.',
    },
    {
      key: 'options',
      letter: 'O',
      label: 'Options',
      purpose: 'Widen before narrowing. Generate, then weigh.',
      questions: [
        'What would you do with no constraints?',
        'What would those close to you suggest?',
        'What are the pros and cons of each option?',
      ],
      historically_skipped: true,
      note: 'Pros and cons is the step that gets skipped. Weighing the options is what turns a list into a decision.',
    },
    {
      key: 'will',
      letter: 'W',
      label: 'Will',
      purpose: 'Convert intent into dated action, and cement it.',
      questions: [
        'On a scale of 1–10, how confident are you?',
        'On a scale of 1–10, how committed are you?',
        'What will you do, and by when — week by week?',
        'Which date this week will we review this?',
      ],
      historically_skipped: true,
      note: 'Both scores ≥8 means the agreement gets cemented out loud. Set the specific review date before closing — Wednesday and the following Saturday is the rhythm.',
    },
  ],
};

export const GREAT: FrameworkDefinition = {
  name: 'GREAT',
  label: 'GREAT',
  expansion: 'Goals → Reality & Rapport → Explore → Achieve → Take action',
  elements: [
    {
      key: 'goals',
      letter: 'G',
      label: 'Goals',
      purpose: 'Name what this hour is for — and then the goal underneath it.',
      questions: [
        'What would you like to take out of this session?',
        "What's your number one goal for today?",
        'What does success look like?',
      ],
      historically_skipped: true,
      note: 'The deeper goal needs its own explicit pass.',
    },
    {
      key: 'reality_rapport',
      letter: 'R',
      label: 'Reality & Rapport',
      purpose: 'Where they actually are — held with heavy reflective listening.',
      questions: REALITY_QUESTIONS,
      note: 'Reflective listening is the signature move of this element. "What I\'m hearing you say…" earns a Strong here.',
    },
    {
      key: 'explore',
      letter: 'E',
      label: 'Explore',
      purpose: 'Widen the field of possibility before committing to one path.',
      questions: [
        'What would you do with no constraints?',
        'What would those close to you suggest?',
        'What are the pros and cons of each option?',
      ],
      historically_skipped: true,
      note: 'Weigh the options explicitly — pros and cons is the step that gets skipped.',
    },
    {
      key: 'achieve',
      letter: 'A',
      label: 'Achieve',
      purpose: 'Negotiate the HOW, then obstacle-proof it.',
      questions: [
        'How exactly will you do this — targeted, or spray-and-pray?',
        'Is there anything that could stop you?',
        'And if that happened, what would you do?',
      ],
      historically_skipped: true,
      note: 'Push past a dismissive "no, nothing" — an unexamined obstacle is the most common reason the action does not happen.',
    },
    {
      key: 'take_action',
      letter: 'T',
      label: 'Take action',
      purpose: 'Convert intent into dated action, and cement it.',
      questions: [
        'On a scale of 1–10, how confident are you?',
        'On a scale of 1–10, how committed are you?',
        'What will you do, and by when — week by week?',
        'Which date this week will we review this?',
      ],
      historically_skipped: true,
      note: 'Both scores ≥8 means the agreement gets cemented out loud. Review date before closing.',
    },
  ],
};

export const FRAMEWORKS: Record<Framework, FrameworkDefinition> = { GROW, GREAT };

export const FRAMEWORK_NAMES: Framework[] = ['GROW', 'GREAT'];

export function frameworkFor(name: Framework): FrameworkDefinition {
  return FRAMEWORKS[name];
}

export function elementsOf(name: Framework): ElementKey[] {
  return FRAMEWORKS[name].elements.map((e) => e.key);
}

export function elementDefinition(
  name: Framework,
  key: ElementKey,
): FrameworkElement | undefined {
  return FRAMEWORKS[name].elements.find((e) => e.key === key);
}

export function elementLabel(key: ElementKey): string {
  for (const framework of FRAMEWORK_NAMES) {
    const found = elementDefinition(framework, key);
    if (found) return found.label;
  }
  return key;
}

/** True when `key` belongs to `framework` — guards cross-framework score rows. */
export function isElementOf(framework: Framework, key: ElementKey): boolean {
  return elementsOf(framework).includes(key);
}

// ── Closing rules ─────────────────────────────────────────────────────────

/** Both confidence and commitment at or above this trigger the closing script. */
export const CEMENT_THRESHOLD = 8;

/**
 * The closing script she is recorded as skipping. Held here as copy so the
 * Session Engine can put the actual words in front of her at the moment they
 * are needed, rather than reminding her that a script exists.
 */
export const CEMENT_SCRIPT = [
  'So let me make sure I have this right — you are going to…',
  '…and you will have that done by…',
  'We will review it on… and again on…',
  'On a scale of 1–10 you said confidence and commitment are both at least 8. Hold onto that number.',
] as const;

/** A wheel domain at or below this is "low" and should be named in Reality. */
export const LOW_SCORE_THRESHOLD = 4;

// ── Rubric (Appendix B) ───────────────────────────────────────────────────

export const RATINGS: Rating[] = ['Strong', 'Adequate', 'Weak', 'Met', 'N/A'];

export const RATING_RUBRIC: Record<Rating, string> = {
  Strong: 'Element fully executed with her signature moves (e.g. heavy reflective listening in Rapport).',
  Adequate: 'Present but partial (e.g. goal front-loaded only, no success-definition pass).',
  Weak: 'Attempted but thin (e.g. obstacle question accepted a dismissive answer).',
  Met: 'Threshold behaviours satisfied (e.g. the 8/10 trigger honoured) even if the script went unused.',
  'N/A': "Conditions didn't arise (e.g. no low scores to flag).",
};

/**
 * Rating → adherence weight.
 *
 * `Met` sits just below `Strong` deliberately. Both are passes, but `Met` means
 * the threshold behaviour happened *without* her signature move — and the Coach
 * Growth Curve (M5) exists to show her that difference over months. Collapsing
 * them to 1.0 would make the curve blind to the exact improvement it is meant
 * to coach. `N/A` is excluded from the denominator rather than scored.
 */
export const RATING_POINTS: Record<Exclude<Rating, 'N/A'>, number> = {
  Strong: 1,
  Met: 0.9,
  Adequate: 0.6,
  Weak: 0.25,
};

export const WHEEL_DOMAINS_DEFAULT = [
  'Career',
  'Finances',
  'Health',
  'Family',
  'Romance/Partner',
  'Personal Growth',
  'Fun & Recreation',
  'Physical Environment',
  'Friends & Community',
  'Spirituality/Purpose',
] as const;

export const SMARTER_FLAGS = [
  { key: 'S', label: 'Specific' },
  { key: 'M', label: 'Measurable' },
  { key: 'A', label: 'Achievable' },
  { key: 'R', label: 'Relevant' },
  { key: 'T', label: 'Time-bound' },
  { key: 'E', label: 'Exciting' },
  { key: 'Rw', label: 'Rewarded' },
] as const;

/** The two she does not tend to name out loud — the visible gap. */
export const SMARTER_OFTEN_MISSED = ['E', 'Rw'] as const;
