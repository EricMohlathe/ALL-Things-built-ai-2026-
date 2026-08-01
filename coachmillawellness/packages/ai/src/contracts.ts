/**
 * The four output contracts from §9, as JSON Schema plus a validator.
 *
 * Both halves are hand-written and sit side by side deliberately. The schema is
 * what the API constrains generation with; the validator is what this package
 * trusts. Generating one from the other would need a JSON-Schema interpreter in
 * a bundle that has to stay under 1.2MB, and deriving the schema from a runtime
 * validator library would put a dependency in the hot path of every screen. The
 * cost of two copies is drift, so `__tests__/contracts.test.ts` fails the build
 * if a required key exists in one and not the other — the same trick that keeps
 * the three copies of every design token honest.
 *
 * The validators are strict about shape and forgiving about emptiness. A model
 * that returns `evidence: ""` for one element has still produced a usable
 * analysis; a model that returns `elements: {}` has not.
 */

import {
  RATINGS,
  elementsOf,
  isElementOf,
  isIsoDate,
  type ChecklistState,
  type ElementKey,
  type Framework,
  type IsoDate,
  type Rating,
} from '@cmw/core';

/** A JSON Schema object, as the Messages API takes it. */
export type JsonSchema = Record<string, unknown>;

export interface AiContract<T> {
  schema: JsonSchema;
  /** Throws `AiContractError` rather than returning a partial result. */
  validate(value: unknown): T;
}

/**
 * A response that did not match the contract.
 *
 * Carries the path so the toast can say *which* field, which is the difference
 * between "the AI response was invalid" and "the AI graded an element that is
 * not part of this framework".
 */
export class AiContractError extends Error {
  constructor(
    readonly path: string,
    readonly detail: string,
    readonly received?: unknown,
  ) {
    super(`${path}: ${detail}`);
    this.name = 'AiContractError';
  }
}

// ── Reading helpers ───────────────────────────────────────────────────────

function record(value: unknown, path: string): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new AiContractError(path, 'expected an object', value);
  }
  return value as Record<string, unknown>;
}

function list(value: unknown, path: string): unknown[] {
  if (!Array.isArray(value)) throw new AiContractError(path, 'expected an array', value);
  return value;
}

function text(source: Record<string, unknown>, key: string, path: string): string {
  const found = source[key];
  if (typeof found !== 'string') {
    throw new AiContractError(`${path}.${key}`, 'expected a string', found);
  }
  return found.trim();
}

/** For the narrative fields whose whole value is the sentence. */
function sentence(source: Record<string, unknown>, key: string, path: string): string {
  const found = text(source, key, path);
  if (found === '') throw new AiContractError(`${path}.${key}`, 'expected some text', found);
  return found;
}

function textList(source: Record<string, unknown>, key: string, path: string): string[] {
  return list(source[key], `${path}.${key}`).map((entry, i) => {
    if (typeof entry !== 'string') {
      throw new AiContractError(`${path}.${key}[${i}]`, 'expected a string', entry);
    }
    return entry.trim();
  });
}

function member<T extends string>(
  source: Record<string, unknown>,
  key: string,
  path: string,
  allowed: readonly T[],
): T {
  const found = source[key];
  if (typeof found !== 'string' || !allowed.includes(found as T)) {
    throw new AiContractError(`${path}.${key}`, `expected one of ${allowed.join(', ')}`, found);
  }
  return found as T;
}

/**
 * A date the model proposed, or null.
 *
 * A malformed date is nulled rather than thrown on: she is about to see and edit
 * every one of these before saving, and losing a whole session analysis because
 * the model wrote "next Wednesday" in a date field would be the wrong trade.
 */
function maybeDate(source: Record<string, unknown>, key: string): IsoDate | null {
  const found = source[key];
  if (typeof found !== 'string') return null;
  const trimmed = found.trim();
  return isIsoDate(trimmed) ? trimmed : null;
}

const CHECKLIST_STATES: readonly ChecklistState[] = ['pass', 'fail', 'na'];

const NULLABLE_DATE = {
  type: ['string', 'null'],
  description: 'ISO calendar date, YYYY-MM-DD, or null if not stated in the session.',
};

// ── 1 · Session Analyzer ──────────────────────────────────────────────────

export interface AnalyzedElement {
  element: ElementKey;
  rating: Rating;
  /** The quote or paraphrase the rating rests on. */
  evidence: string;
  note: string;
}

export interface AnalyzedChecklist {
  smarter_met: ChecklistState;
  low_scores_flagged: ChecklistState;
  will_step: ChecklistState;
  review_date_set: ChecklistState;
}

export interface SuggestedAction {
  title: string;
  due: IsoDate | null;
  review: IsoDate | null;
}

export interface SessionAnalysis {
  elements: AnalyzedElement[];
  checklist: AnalyzedChecklist;
  suggested_actions: SuggestedAction[];
  one_growth_tip: string;
}

/**
 * Framework-specific, because the element enum is the strongest constraint in
 * the whole contract: a GROW session cannot be graded on `explore`, and encoding
 * that in the schema removes the failure mode instead of validating it after the
 * fact.
 */
export function sessionAnalysisContract(framework: Framework): AiContract<SessionAnalysis> {
  const elements = elementsOf(framework);

  return {
    schema: {
      type: 'object',
      additionalProperties: false,
      required: ['elements', 'checklist', 'suggested_actions', 'one_growth_tip'],
      properties: {
        elements: {
          type: 'array',
          description: `One entry per ${framework} element, in order. Grade every element.`,
          items: {
            type: 'object',
            additionalProperties: false,
            required: ['element', 'rating', 'evidence', 'note'],
            properties: {
              element: { type: 'string', enum: elements },
              rating: { type: 'string', enum: RATINGS },
              evidence: {
                type: 'string',
                description: 'A short quote or paraphrase from the notes that the rating rests on.',
              },
              note: {
                type: 'string',
                description: 'One sentence to the coach about this element.',
              },
            },
          },
        },
        checklist: {
          type: 'object',
          additionalProperties: false,
          required: ['smarter_met', 'low_scores_flagged', 'will_step', 'review_date_set'],
          properties: {
            smarter_met: { type: 'string', enum: CHECKLIST_STATES },
            low_scores_flagged: { type: 'string', enum: CHECKLIST_STATES },
            will_step: { type: 'string', enum: CHECKLIST_STATES },
            review_date_set: { type: 'string', enum: CHECKLIST_STATES },
          },
        },
        suggested_actions: {
          type: 'array',
          items: {
            type: 'object',
            additionalProperties: false,
            required: ['title', 'due', 'review'],
            properties: {
              title: { type: 'string' },
              due: NULLABLE_DATE,
              review: NULLABLE_DATE,
            },
          },
        },
        one_growth_tip: {
          type: 'string',
          description: 'One thing the coach could do differently next time. Specific, kind, actionable.',
        },
      },
    },

    validate(value) {
      const root = record(value, 'analysis');

      const parsedElements = list(root.elements, 'analysis.elements').map((entry, i) => {
        const path = `analysis.elements[${i}]`;
        const row = record(entry, path);
        const element = text(row, 'element', path) as ElementKey;
        if (!isElementOf(framework, element)) {
          throw new AiContractError(
            `${path}.element`,
            `not a ${framework} element`,
            row.element,
          );
        }
        return {
          element,
          rating: member(row, 'rating', path, RATINGS),
          evidence: text(row, 'evidence', path),
          note: text(row, 'note', path),
        };
      });

      const checklistPath = 'analysis.checklist';
      const checklistRow = record(root.checklist, checklistPath);

      return {
        elements: parsedElements,
        checklist: {
          smarter_met: member(checklistRow, 'smarter_met', checklistPath, CHECKLIST_STATES),
          low_scores_flagged: member(
            checklistRow,
            'low_scores_flagged',
            checklistPath,
            CHECKLIST_STATES,
          ),
          will_step: member(checklistRow, 'will_step', checklistPath, CHECKLIST_STATES),
          review_date_set: member(
            checklistRow,
            'review_date_set',
            checklistPath,
            CHECKLIST_STATES,
          ),
        },
        suggested_actions: list(root.suggested_actions, 'analysis.suggested_actions').map(
          (entry, i) => {
            const path = `analysis.suggested_actions[${i}]`;
            const row = record(entry, path);
            return {
              title: sentence(row, 'title', path),
              due: maybeDate(row, 'due'),
              review: maybeDate(row, 'review'),
            };
          },
        ),
        one_growth_tip: sentence(root, 'one_growth_tip', 'analysis'),
      };
    },
  };
}

// ── 2 · Coherence Checker ─────────────────────────────────────────────────

export type CoherenceVerdictLevel = 'on' | 'drifting' | 'off';

const VERDICTS: readonly CoherenceVerdictLevel[] = ['on', 'drifting', 'off'];

export interface CoherenceVerdict {
  verdict: CoherenceVerdictLevel;
  why: string;
  one_line_fix: string;
  suggested_hook: string;
}

export function coherenceContract(): AiContract<CoherenceVerdict> {
  return {
    schema: {
      type: 'object',
      additionalProperties: false,
      required: ['verdict', 'why', 'one_line_fix', 'suggested_hook'],
      properties: {
        verdict: {
          type: 'string',
          enum: VERDICTS,
          description:
            "'on' if the piece carries the pillar's core message, 'drifting' if it is adjacent, 'off' if it belongs to a different pillar or none.",
        },
        why: { type: 'string', description: 'One or two sentences, quoting the piece.' },
        one_line_fix: {
          type: 'string',
          description: 'The smallest edit that would pull it back on message.',
        },
        suggested_hook: {
          type: 'string',
          description: 'An opening line in her voice — warm, plain, not salesy.',
        },
      },
    },

    validate(value) {
      const root = record(value, 'coherence');
      return {
        verdict: member(root, 'verdict', 'coherence', VERDICTS),
        why: sentence(root, 'why', 'coherence'),
        one_line_fix: sentence(root, 'one_line_fix', 'coherence'),
        suggested_hook: sentence(root, 'suggested_hook', 'coherence'),
      };
    },
  };
}

// ── 3 · Weekly Digest ─────────────────────────────────────────────────────

export interface DigestClient {
  /** First name only — it is all the prompt was given (§13). */
  first_name: string;
  why: string;
}

export interface WeeklyDigest {
  clients_needing_attention: DigestClient[];
  content_gaps: string[];
  coach_tip: string;
  focus_sentence: string;
}

export function digestContract(): AiContract<WeeklyDigest> {
  return {
    schema: {
      type: 'object',
      additionalProperties: false,
      required: ['clients_needing_attention', 'content_gaps', 'coach_tip', 'focus_sentence'],
      properties: {
        clients_needing_attention: {
          type: 'array',
          items: {
            type: 'object',
            additionalProperties: false,
            required: ['first_name', 'why'],
            properties: {
              first_name: {
                type: 'string',
                description: 'Use exactly the first name given in the rollup. Never invent a surname.',
              },
              why: { type: 'string', description: 'One clause. What has slipped.' },
            },
          },
        },
        content_gaps: {
          type: 'array',
          items: { type: 'string' },
          description: 'Starved pillars or missed platforms, named in words.',
        },
        coach_tip: {
          type: 'string',
          description:
            'One coaching-skill tip drawn from her own adherence data, naming the element.',
        },
        focus_sentence: {
          type: 'string',
          description:
            'The single sentence for the top of her Deck. Under 140 characters, second person, no greeting.',
        },
      },
    },

    validate(value) {
      const root = record(value, 'digest');
      return {
        clients_needing_attention: list(
          root.clients_needing_attention,
          'digest.clients_needing_attention',
        ).map((entry, i) => {
          const path = `digest.clients_needing_attention[${i}]`;
          const row = record(entry, path);
          return {
            first_name: sentence(row, 'first_name', path),
            why: sentence(row, 'why', path),
          };
        }),
        content_gaps: textList(root, 'content_gaps', 'digest').filter((gap) => gap !== ''),
        coach_tip: sentence(root, 'coach_tip', 'digest'),
        focus_sentence: sentence(root, 'focus_sentence', 'digest'),
      };
    },
  };
}

// ── 4 · Prep Whisperer ────────────────────────────────────────────────────

export interface PrepBrief {
  recap_3_lines: string[];
  suggested_opening_question: string;
  watchouts: string[];
}

export function prepContract(): AiContract<PrepBrief> {
  return {
    schema: {
      type: 'object',
      additionalProperties: false,
      required: ['recap_3_lines', 'suggested_opening_question', 'watchouts'],
      properties: {
        recap_3_lines: {
          type: 'array',
          items: { type: 'string' },
          minItems: 1,
          maxItems: 3,
          description: 'Exactly what she needs to remember, in three lines or fewer.',
        },
        suggested_opening_question: {
          type: 'string',
          description: 'Drawn from her own question bank where one fits.',
        },
        watchouts: {
          type: 'array',
          items: { type: 'string' },
          description: 'Things to hold lightly — a slipped action, a domain still low, a dropped thread.',
        },
      },
    },

    validate(value) {
      const root = record(value, 'prep');
      const recap = textList(root, 'recap_3_lines', 'prep').filter((line) => line !== '');
      if (recap.length === 0) {
        throw new AiContractError('prep.recap_3_lines', 'expected at least one line', root.recap_3_lines);
      }
      return {
        // Truncated rather than rejected: the field is named for its ceiling, and
        // a fourth useful line is not a reason to throw the brief away.
        recap_3_lines: recap.slice(0, 3),
        suggested_opening_question: sentence(root, 'suggested_opening_question', 'prep'),
        watchouts: textList(root, 'watchouts', 'prep').filter((w) => w !== ''),
      };
    },
  };
}
