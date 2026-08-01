/**
 * Prompt construction (§9's prompt doctrine).
 *
 * The system prompt is rendered from `@cmw/core/frameworks.ts`, not re-typed
 * here. That single decision is what makes the Copilot grade against *her*
 * methodology: when she edits a question bank in Settings, the AI's standard
 * moves with it, and there is no second copy of Appendix A to fall out of date.
 *
 * The prompt is split into two blocks because they have different lifetimes. The
 * methodology block is byte-identical on every call of every feature, so it
 * carries the cache breakpoint and is paid for once. The task block changes per
 * feature and is small. (If the methodology ever renders shorter than the model's
 * cache minimum the API simply declines to cache it — the marker is never an
 * error, so this needs no version check.)
 */

import {
  CEMENT_SCRIPT,
  CEMENT_THRESHOLD,
  FRAMEWORK_NAMES,
  LOW_SCORE_THRESHOLD,
  RATING_RUBRIC,
  RATINGS,
  SMARTER_FLAGS,
  SMARTER_OFTEN_MISSED,
  WHEEL_DOMAINS_DEFAULT,
  elementsOf,
  frameworkFor,
  missingSmarterFlags,
  relativeDay,
  type ActionItem,
  type Coachee,
  type ContentItem,
  type DeckSummary,
  type Framework,
  type Goal,
  type GrowthCurve,
  type IsoDate,
  type Pillar,
  type Session,
  type SessionScorecard,
  type WheelSnapshot,
} from '@cmw/core';

import { promptName, promptNames, scrubNotes } from './redact.js';

export interface MethodologyOptions {
  /** Her edited wheel domains, when she has changed them (M7). */
  wheelDomains?: readonly string[];
}

/**
 * Appendix A, rendered.
 *
 * Markdown rather than JSON: this is a document about how a person coaches, and
 * the model reads prose better than it reads a nested object. The ⚠ markers are
 * the load-bearing part — they tell the grader which moves are *hers to work on*,
 * which is what separates "your Options step was thin" from a generic critique.
 */
export function methodologyPrompt(options: MethodologyOptions = {}): string {
  const domains = options.wheelDomains?.length ? options.wheelDomains : WHEEL_DOMAINS_DEFAULT;
  const lines: string[] = [];

  lines.push(
    'You are the copilot inside CoachMillaWellness, a practice tool built for one health and life coach.',
    '',
    'Your standard is her methodology, reproduced below. Grade and advise against *this*, never against generic coaching best practice. When her method differs from what you would otherwise recommend, hers wins.',
    '',
    '# Her frameworks',
    '',
  );

  for (const name of FRAMEWORK_NAMES) {
    const framework = frameworkFor(name);
    lines.push(`## ${framework.label} — ${framework.expansion}`, '');
    for (const element of framework.elements) {
      lines.push(`### ${element.letter} · ${element.label}  \`${element.key}\``);
      lines.push(`Purpose: ${element.purpose}`);
      lines.push('Questions she asks:');
      for (const question of element.questions) lines.push(`- ${question}`);
      if (element.note) lines.push(`Coaching note: ${element.note}`);
      if (element.historically_skipped) {
        lines.push(
          '⚠ She has a recorded pattern of skipping or thinning this element. Look for it specifically, and say so plainly when it is missing.',
        );
      }
      lines.push('');
    }
  }

  lines.push(
    '# Rating rubric',
    '',
    'Use exactly these five values:',
    '',
    ...RATINGS.map((rating) => `- **${rating}** — ${RATING_RUBRIC[rating]}`),
    '',
    'Rate honestly. An inflated Strong makes her adherence chart useless, which is the one thing this tool exists to give her. Use `N/A` only when the conditions for an element genuinely did not arise, never as a way to avoid a judgement.',
    '',
    '# Closing rule',
    '',
    `When confidence and commitment are both at or above ${CEMENT_THRESHOLD} out of 10, the agreement is cemented out loud before the session ends. Her script:`,
    '',
    ...CEMENT_SCRIPT.map((line) => `> ${line}`),
    '',
    'She is recorded as skipping this script. If the threshold was met and the notes show no cementing, that is a `Met` at best — the threshold behaviour happened without her signature move.',
    '',
    'A specific review date is set before closing. Wednesday and the following Saturday is her rhythm.',
    '',
    '# SMARTER goals',
    '',
    ...SMARTER_FLAGS.map((flag) => `- **${flag.key}** — ${flag.label}`),
    '',
    `The two she does not tend to name out loud are ${smarterWords(SMARTER_OFTEN_MISSED).join(
      ' and ',
    )}. A goal missing those is not a failed goal — it is the specific gap to name.`,
    '',
    '# Wheel of Life',
    '',
    `Ten domains: ${domains.join(', ')}.`,
    `Scores run 0–10. A domain at or below ${LOW_SCORE_THRESHOLD} is low and should be named during Reality — she frames low scores as honesty, not failure.`,
    '',
    '# How to behave',
    '',
    '- **You propose, she disposes.** Every field you return is shown to her for editing before anything is saved. Write as a draft for a professional, not as a verdict.',
    '- Her clients are identified by first name only. Never invent a surname, an age, a diagnosis or a detail you were not given.',
    '- These are wellness notes, not medical records. Do not diagnose, do not name conditions, and do not suggest treatment. If notes describe something clinical, the right move is one line advising a referral.',
    '- Quote her notes for evidence. A rating with no evidence is not usable by her.',
    '- Write in plain South African English. Warm, direct, no jargon, no exclamation marks, no "journey".',
    '- Be brief. She reads this between sessions.',
  );

  return lines.join('\n');
}

// ── Task prompts ──────────────────────────────────────────────────────────

export const ANALYZER_TASK = [
  '# Task — Session Analyzer',
  '',
  'Grade one coaching cycle against her framework and return the structured analysis.',
  '',
  'Rules:',
  '- Grade every element of the framework named below. Do not omit one because the notes are thin — that is what `Weak` is for.',
  '- `evidence` is a short quote or close paraphrase from the notes. If there is nothing to quote, say so in one clause rather than inventing support.',
  '- The checklist is four honest states: `pass`, `fail`, or `na` when the condition did not arise.',
  '  - `smarter_met` — does the goal name all seven SMARTER attributes, including Exciting and Rewarded?',
  '  - `low_scores_flagged` — were low wheel domains named during Reality? `na` when there were none.',
  '  - `will_step` — is there a concrete action with a date?',
  '  - `review_date_set` — was a specific review date agreed before closing?',
  '- `suggested_actions` are the actions the session actually produced, phrased as the client would own them. Leave a date `null` rather than guessing one.',
  '- `one_growth_tip` is for the coach, not the client. Name one element and one thing to do differently. Kind and specific.',
].join('\n');

export const COHERENCE_TASK = [
  '# Task — Coherence Checker',
  '',
  'Judge whether a piece of content carries the message pillar it is filed under.',
  '',
  'Rules:',
  "- `on` means a reader would come away with the pillar's core message. `drifting` means adjacent — true to her, but not to this pillar. `off` means it belongs to a different pillar or to none.",
  '- Quote the piece in `why`. One or two sentences.',
  '- `one_line_fix` is the smallest edit that would pull it back, not a rewrite.',
  '- `suggested_hook` is an opening line in her voice: plain, warm, no hype, no "stop scrolling".',
  '- Judge the message, not the production quality. You cannot see the video.',
].join('\n');

export const DIGEST_TASK = [
  '# Task — Weekly Digest',
  '',
  'Write the Monday brief from the rollup below.',
  '',
  'Rules:',
  '- Only name a client the rollup names, using exactly the first name given.',
  '- `why` for each client is one clause about what has slipped — a review date, a session gap, an unfinished action.',
  '- `content_gaps` names starved pillars and missed platforms in words. Empty array if the week was balanced.',
  '- `coach_tip` comes from her own adherence figures. Name the element and the pattern, and give one thing to try this week.',
  '- `focus_sentence` is the single line at the top of her Deck: second person, under 140 characters, no greeting, no emoji. It should name the most important thing today, not summarise the week.',
].join('\n');

export const PREP_TASK = [
  '# Task — Prep Whisperer',
  '',
  'Write the brief she reads in the two minutes before a session starts.',
  '',
  'Rules:',
  '- `recap_3_lines` — at most three lines, each one thing she must remember. Not a summary; a reminder.',
  '- `suggested_opening_question` — prefer a question from her own bank for the framework in use. If none fits, write one in the same register.',
  '- `watchouts` — a slipped action, a domain still low, a commitment that was thin last time. Things to hold lightly, not accusations to level.',
].join('\n');

// ── Input assembly ────────────────────────────────────────────────────────

/**
 * Assembling the user message lives here rather than in a screen so the exact
 * bytes sent are unit-testable and identical on every surface. A prompt built ad
 * hoc in a component is a prompt that differs between web and mobile.
 */

/**
 * SMARTER keys spelled out.
 *
 * `missingSmarterFlags` returns keys because that is what the UI's chips are
 * labelled with, but "not yet named: E, Rw" asks the model to decode an
 * abbreviation before it can grade — and a model that decodes it wrongly grades
 * the wrong gap. The words cost nothing.
 */
function smarterWords(keys: readonly string[]): string[] {
  return keys.map((key) => SMARTER_FLAGS.find((f) => f.key === key)?.label ?? key);
}

function bullet(label: string, value: string | number | null | undefined): string | null {
  if (value === null || value === undefined || value === '') return null;
  return `- ${label}: ${value}`;
}

function block(title: string, body: readonly (string | null)[]): string[] {
  const kept = body.filter((line): line is string => line !== null);
  if (kept.length === 0) return [];
  return [`## ${title}`, ...kept, ''];
}

export interface AnalyzerInput {
  session: Session;
  /** The coachee whose cycle is being graded. A joint session is graded per person. */
  coachee: Coachee;
  /** Every participant, so their names can be scrubbed out of the notes. */
  participants: readonly Coachee[];
  goals: readonly Goal[];
  /** Her session notes or a pasted transcript. */
  notes: string;
  wheel?: WheelSnapshot | null;
  openActions?: readonly ActionItem[];
}

export function analyzerPrompt(input: AnalyzerInput): string {
  const { session, coachee } = input;
  const who = promptName(coachee);
  const framework = frameworkFor(session.framework);
  const low = (input.wheel?.domains ?? [])
    .filter((d) => d.score <= LOW_SCORE_THRESHOLD)
    .map((d) => `${d.domain} ${d.score}/10`);

  const lines: string[] = [
    `Grade the ${framework.label} cycle for **${who}** in the session below.`,
    '',
    ...block('Session', [
      bullet('Date', session.date),
      bullet('Framework', `${framework.label} — ${framework.expansion}`),
      bullet('Elements to grade, in order', elementsOf(session.framework).join(', ')),
      bullet('Length', `${session.duration_min} minutes`),
      bullet(
        'Participants',
        input.participants.length > 1
          ? `${input.participants.map(promptName).join(', ')} (joint session — grade ${who} only)`
          : who,
      ),
      bullet('Confidence out of 10', session.confidence),
      bullet('Commitment out of 10', session.commitment),
      bullet(
        'Review dates agreed',
        session.review_dates.length ? session.review_dates.join(', ') : 'none recorded',
      ),
      bullet(
        'Domains she flagged as low during Reality',
        session.flagged_domains?.length ? session.flagged_domains.join(', ') : 'none recorded',
      ),
    ]),
    ...block(
      'Open goals',
      input.goals.length === 0
        ? ['- none recorded']
        : input.goals.map((goal) => {
            const missing = smarterWords(missingSmarterFlags(goal.smarter));
            const gap = missing.length ? ` — not yet named: ${missing.join(', ')}` : ' — all seven named';
            return `- "${goal.statement}"${gap}`;
          }),
    ),
    ...block(
      'Latest wheel',
      input.wheel
        ? [
            bullet('Dated', input.wheel.date),
            bullet('Low domains', low.length ? low.join(', ') : 'none at or below the threshold'),
          ]
        : ['- no wheel snapshot on file'],
    ),
    ...block(
      'Open actions carried in',
      (input.openActions ?? []).length === 0
        ? ['- none']
        : (input.openActions ?? []).map(
            (a) => `- "${a.title}"${a.review_date ? ` (review ${a.review_date})` : ''}`,
          ),
    ),
    '## Her notes from the session',
    '',
    scrubNotes(input.notes.trim(), input.participants) || '(she recorded no notes)',
  ];

  return lines.join('\n');
}

export interface CoherenceInput {
  item: ContentItem;
  pillar: Pillar | null;
  /** Her last few published pieces, for context on where the message already is. */
  recent: readonly ContentItem[];
}

export function coherencePrompt(input: CoherenceInput): string {
  const { item, pillar } = input;
  return [
    ...block('The piece', [
      bullet('Title', item.title),
      bullet('Format', `${item.type} on ${item.platform}`),
      bullet('Hook', item.hook),
      bullet('Call to action', item.cta),
    ]),
    ...block(
      'Its pillar',
      pillar
        ? [bullet('Name', pillar.name), bullet('Core message', pillar.core_message),
            bullet('Keywords', pillar.keywords.length ? pillar.keywords.join(', ') : null)]
        : [
            '- This piece is filed under no pillar. Judge it against her pillars generally and say which one it belongs to.',
          ],
    ),
    ...block(
      'Her last published pieces',
      input.recent.length === 0
        ? ['- nothing published yet']
        : input.recent.map((r) => `- "${r.title}" (${r.type}, ${r.publish_date ?? 'undated'})`),
    ),
    '## Script or caption',
    '',
    (item.script ?? '').trim() || '(no script written yet — judge the title, hook and CTA)',
  ].join('\n');
}

export interface DigestInput {
  deck: DeckSummary;
  coachees: readonly Coachee[];
  /** Her adherence per element, so `coach_tip` comes from data and not vibes. */
  growth?: GrowthCurve | null;
  /** Pillar names with nothing published in the window. */
  starvedPillars?: readonly string[];
  publishedThisWeek?: number;
  weekOf: IsoDate;
}

export function digestPrompt(input: DigestInput): string {
  const names = promptNames(input.coachees);
  const nameOf = (id: string): string => names.get(id) ?? 'a client';
  const deck = input.deck;

  const growth = input.growth?.averages.filter((a) => a.sessions > 0) ?? [];

  return [
    `Rollup for the week of ${input.weekOf}. Today is ${deck.date}.`,
    '',
    ...block('Sessions', [
      bullet('Today', deck.today_sessions.length),
      bullet(
        'Next scheduled',
        deck.next_session ? `${deck.next_session.date} (${deck.next_session.framework})` : 'nothing booked',
      ),
      bullet('Consecutive weeks with a session', deck.session_streak_weeks),
    ]),
    ...block(
      'Clients drifting',
      deck.at_risk.length === 0
        ? ['- none flagged']
        : deck.at_risk.map(
            (r) => `- ${nameOf(r.coachee_id)} — ${r.reason ?? 'no recent activity'} (${r.days_slipped} days)`,
          ),
    ),
    ...block(
      'Reviews',
      [
        bullet('Slipped past their date', deck.overdue_reviews.length),
        bullet('Due today', deck.reviews_due_today.length),
        bullet('Due in the next week', deck.reviews_due_soon.length),
        ...deck.overdue_reviews
          .slice(0, 6)
          .map((a) => `- overdue: "${a.title}" for ${nameOf(a.coachee_id)}, review was ${relativeDay(deck.date, a.review_date)}`),
      ],
    ),
    ...block('Content', [
      bullet('Published this week', input.publishedThisWeek),
      bullet('Consecutive publishing days', deck.publish_streak_days),
      bullet('Due today and not yet posted', deck.content_due_today.length),
      bullet(
        'Pillars with nothing published in the window',
        input.starvedPillars?.length ? input.starvedPillars.join(', ') : 'none',
      ),
    ]),
    ...block(
      'Her own adherence, by element',
      growth.length === 0
        ? ['- not enough graded sessions yet; skip the coaching tip and say so in one clause']
        : [
            ...growth.map((a) => `- ${a.label}: ${a.adherence_pct}% across ${a.sessions} graded cycles`),
            input.growth?.weakest_element
              ? `- weakest overall: ${
                  growth.find((g) => g.element === input.growth?.weakest_element)?.label ??
                  input.growth.weakest_element
                }`
              : null,
          ],
    ),
  ].join('\n');
}

export interface PrepInput {
  coachee: Coachee;
  framework: Framework;
  lastSession?: Session | null;
  /** Her adherence on that last session, so watchouts can name a thin element. */
  lastScorecard?: SessionScorecard | null;
  openActions?: readonly ActionItem[];
  wheel?: WheelSnapshot | null;
  goals?: readonly Goal[];
  today: IsoDate;
}

export function prepPrompt(input: PrepInput): string {
  const who = promptName(input.coachee);
  const framework = frameworkFor(input.framework);
  const weak = input.lastScorecard?.weakest.map((element) => {
    const found = framework.elements.find((e) => e.key === element);
    return found?.label ?? element;
  });

  return [
    `She is about to run a ${framework.label} session with **${who}**. Today is ${input.today}.`,
    '',
    ...block(
      'Last session',
      input.lastSession
        ? [
            bullet('Date', `${input.lastSession.date} (${relativeDay(input.today, input.lastSession.date)})`),
            bullet('Framework', input.lastSession.framework),
            bullet('Confidence / commitment', `${input.lastSession.confidence ?? '—'} / ${input.lastSession.commitment ?? '—'}`),
            bullet('Adherence', input.lastScorecard?.adherence_pct !== null && input.lastScorecard
              ? `${input.lastScorecard.adherence_pct}%`
              : null),
            bullet('Her thinnest element last time', weak?.length ? weak.join(', ') : null),
            bullet('Summary', scrubNotes(input.lastSession.summary ?? '', [input.coachee]) || null),
          ]
        : ['- this is a first session'],
    ),
    ...block(
      'Open goals',
      (input.goals ?? []).length === 0
        ? ['- none recorded']
        : (input.goals ?? []).map((g) => `- "${g.statement}"`),
    ),
    ...block(
      'Open actions',
      (input.openActions ?? []).length === 0
        ? ['- none outstanding']
        : (input.openActions ?? []).map(
            (a) =>
              `- "${a.title}" — ${a.status}${a.review_date ? `, review was set for ${a.review_date}` : ', no review date'}`,
          ),
    ),
    ...block(
      'Latest wheel',
      input.wheel
        ? [
            bullet('Dated', `${input.wheel.date} (${relativeDay(input.today, input.wheel.date)})`),
            bullet(
              'Low domains',
              input.wheel.domains
                .filter((d) => d.score <= LOW_SCORE_THRESHOLD)
                .map((d) => `${d.domain} ${d.score}/10`)
                .join(', ') || 'none at or below the threshold',
            ),
            bullet(
              'Biggest gap to target',
              [...input.wheel.domains]
                .sort((a, b) => b.target - b.score - (a.target - a.score))
                .slice(0, 2)
                .map((d) => `${d.domain} (${d.score} → ${d.target})`)
                .join(', ') || null,
            ),
          ]
        : ['- no wheel snapshot on file'],
    ),
    ...block(
      'Her question bank for this framework',
      framework.elements.flatMap((element) => [
        `- ${element.label}: ${element.questions.join(' / ')}`,
      ]),
    ),
  ].join('\n');
}
