/**
 * Session adherence scoring — the "app coaches the coach" engine.
 *
 * Deterministic and pure. The AI (§9) proposes *ratings*; this module turns
 * ratings into a scorecard, and nothing here depends on the AI having run — a
 * session graded by hand produces exactly the same shape. That separation is
 * what lets the single-HTML build ship the whole Session Engine in week 1 with
 * the Copilot arriving in week 2 and changing nothing downstream.
 */

import { CEMENT_THRESHOLD, RATING_POINTS, RATINGS, frameworkFor, isElementOf } from './frameworks.js';
import type {
  ElementKey,
  Framework,
  Rating,
  Session,
  SessionElementScore,
  Uuid,
} from './types.js';

export interface ElementScoreLine {
  element: ElementKey;
  letter: string;
  label: string;
  /** `null` when this element has not been graded yet. */
  rating: Rating | null;
  /** Adherence weight, or `null` when unscored or `N/A`. */
  points: number | null;
  /** Whether this line contributes to `adherence_pct`. */
  counted: boolean;
  notes?: string | null;
  evidence?: string | null;
  /** A move the compendium records her as tending to skip. */
  historically_skipped: boolean;
}

export interface ClosingCheck {
  confidence: number | null;
  commitment: number | null;
  threshold: number;
  /** Both scores at or above the threshold — the script is owed. */
  cement_expected: boolean;
  review_date_set: boolean;
}

export interface SessionScorecard {
  session_id: Uuid;
  coachee_id: Uuid | null;
  framework: Framework;
  lines: ElementScoreLine[];
  /** 0–100 across graded, non-`N/A` elements. `null` when nothing is graded. */
  adherence_pct: number | null;
  counted_elements: number;
  rating_counts: Record<Rating, number>;
  /** Best and worst graded elements. Both empty when every element ties. */
  strongest: ElementKey[];
  weakest: ElementKey[];
  /** Framework elements with no rating yet. */
  unscored: ElementKey[];
  closing: ClosingCheck;
  /** Every element of the framework has a rating. */
  complete: boolean;
}

export interface ScoreSessionInput {
  session: Session;
  scores: SessionElementScore[];
  /**
   * Which participant's cycle to grade. A joint session must not collapse into
   * one cycle (Appendix A), so callers grade each participant separately.
   * Omit only for a solo session.
   */
  coachee_id?: Uuid;
}

function pointsFor(rating: Rating): number | null {
  return rating === 'N/A' ? null : RATING_POINTS[rating];
}

/** Latest edit wins when an element has been re-rated. */
function newest(a: SessionElementScore, b: SessionElementScore): SessionElementScore {
  return b.updated_at >= a.updated_at ? b : a;
}

export function scoreSession(input: ScoreSessionInput): SessionScorecard {
  const { session } = input;
  const framework = session.framework;
  const coacheeId = input.coachee_id ?? null;

  const relevant = input.scores.filter(
    (s) =>
      s.session_id === session.id &&
      !s.deleted_at &&
      isElementOf(framework, s.element) &&
      (coacheeId === null || s.coachee_id === coacheeId),
  );

  const byElement = new Map<ElementKey, SessionElementScore>();
  for (const score of relevant) {
    const existing = byElement.get(score.element);
    byElement.set(score.element, existing ? newest(existing, score) : score);
  }

  const ratingCounts = Object.fromEntries(RATINGS.map((r) => [r, 0])) as Record<Rating, number>;

  // Iterating the definitions rather than the keys keeps `def` non-optional —
  // the framework table is the source of both, so a missing definition is not a
  // real state and should not be handled as if it were.
  const lines: ElementScoreLine[] = frameworkFor(framework).elements.map((def) => {
    const score = byElement.get(def.key);
    const rating = score?.rating ?? null;
    if (rating) ratingCounts[rating] += 1;
    const points = rating ? pointsFor(rating) : null;

    return {
      element: def.key,
      letter: def.letter,
      label: def.label,
      rating,
      points,
      counted: points !== null,
      notes: score?.notes ?? null,
      evidence: score?.evidence ?? null,
      historically_skipped: def.historically_skipped ?? false,
    };
  });

  // Narrowing to a non-null `points` here rather than filtering on `counted`
  // keeps the arithmetic below free of `?? 0` guards that could never fire.
  const counted = lines.flatMap((l) =>
    l.points === null ? [] : [{ element: l.element, points: l.points }],
  );

  const adherencePct =
    counted.length === 0
      ? null
      : Math.round((counted.reduce((sum, l) => sum + l.points, 0) / counted.length) * 100);

  // When every graded element ties there is no "weakest" worth naming — saying
  // so would put a false finding in front of her.
  const values = counted.map((l) => l.points);
  const max = values.length ? Math.max(...values) : 0;
  const min = values.length ? Math.min(...values) : 0;
  const spread = max !== min;

  return {
    session_id: session.id,
    coachee_id: coacheeId,
    framework,
    lines,
    adherence_pct: adherencePct,
    counted_elements: counted.length,
    rating_counts: ratingCounts,
    strongest: spread ? counted.filter((l) => l.points === max).map((l) => l.element) : [],
    weakest: spread ? counted.filter((l) => l.points === min).map((l) => l.element) : [],
    unscored: lines.filter((l) => l.rating === null).map((l) => l.element),
    closing: closingCheck(session),
    complete: lines.every((l) => l.rating !== null),
  };
}

export function closingCheck(session: Session): ClosingCheck {
  const confidence = session.confidence ?? null;
  const commitment = session.commitment ?? null;
  return {
    confidence,
    commitment,
    threshold: CEMENT_THRESHOLD,
    cement_expected:
      confidence !== null &&
      commitment !== null &&
      confidence >= CEMENT_THRESHOLD &&
      commitment >= CEMENT_THRESHOLD,
    review_date_set: session.review_dates.length > 0,
  };
}

// ── Coach Growth Curve (M5 / P2) ──────────────────────────────────────────

export interface GrowthPoint {
  /** `YYYY-MM`. */
  month: string;
  element: ElementKey;
  label: string;
  /** Mean adherence for this element in this month, 0–100. */
  adherence_pct: number;
  sessions: number;
}

export interface GrowthCurve {
  framework: Framework;
  points: GrowthPoint[];
  /** Per element, across the whole window. */
  averages: Array<{ element: ElementKey; label: string; adherence_pct: number; sessions: number }>;
  /** Lowest-scoring element overall — the one to work on. */
  weakest_element: ElementKey | null;
}

/**
 * Her own adherence per element, charted monthly (§2 M5). This is the feature
 * that grades the coach, so it deliberately reports thin months honestly via
 * `sessions` rather than smoothing a single session into a trend.
 */
export function coachGrowthCurve(
  sessions: Session[],
  scores: SessionElementScore[],
  framework: Framework,
): GrowthCurve {
  const relevant = sessions.filter((s) => s.framework === framework && !s.deleted_at);

  interface Bucket {
    month: string;
    element: ElementKey;
    label: string;
    total: number;
    count: number;
  }
  const buckets = new Map<string, Bucket>();

  for (const session of relevant) {
    const month = session.date.slice(0, 7);
    // A joint session yields one cycle per participant; grade them all.
    const participants = session.participants.length > 0 ? session.participants : [null];
    for (const participant of participants) {
      const card = scoreSession({
        session,
        scores,
        ...(participant ? { coachee_id: participant } : {}),
      });
      for (const line of card.lines) {
        if (line.points === null) continue;
        const key = `${month}|${line.element}`;
        let bucket = buckets.get(key);
        if (!bucket) {
          // The label travels with the bucket, so the point list never has to
          // look an element back up and handle a miss that cannot happen.
          bucket = { month, element: line.element, label: line.label, total: 0, count: 0 };
          buckets.set(key, bucket);
        }
        bucket.total += line.points;
        bucket.count += 1;
      }
    }
  }

  const points: GrowthPoint[] = [...buckets.values()]
    .map((b) => ({
      month: b.month,
      element: b.element,
      label: b.label,
      adherence_pct: Math.round((b.total / b.count) * 100),
      sessions: b.count,
    }))
    .sort((a, b) => a.month.localeCompare(b.month) || a.element.localeCompare(b.element));

  const averages = frameworkFor(framework).elements.map((def) => {
    const forElement = points.filter((p) => p.element === def.key);
    const sessionsCount = forElement.reduce((n, p) => n + p.sessions, 0);
    const weighted = forElement.reduce((n, p) => n + p.adherence_pct * p.sessions, 0);
    return {
      element: def.key,
      label: def.label,
      adherence_pct: sessionsCount ? Math.round(weighted / sessionsCount) : 0,
      sessions: sessionsCount,
    };
  });

  const graded = averages.filter((a) => a.sessions > 0);
  const weakest = graded.length
    ? graded.reduce((lowest, a) => (a.adherence_pct < lowest.adherence_pct ? a : lowest))
    : null;

  return { framework, points, averages, weakest_element: weakest?.element ?? null };
}
