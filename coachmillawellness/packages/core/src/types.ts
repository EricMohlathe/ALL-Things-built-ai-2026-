/**
 * Entities — compendium §3.1. One schema, four targets.
 *
 * Field names are snake_case on purpose. These types are the same shape that
 * becomes Postgres columns in P5 and SQLite columns in P7, so keeping the names
 * identical everywhere removes an entire class of mapping bug (and an entire
 * translation layer) at the cost of looking slightly un-idiomatic in TS.
 *
 * Conventions (§3.1): UUIDv7 ids · ISO-8601 UTC timestamps · `updated_at` on
 * every row because it is what drives last-write-wins sync · enums as string
 * unions here, CHECK constraints in SQL.
 */

/** UUIDv7. Time-ordered, so a plain sort on id is chronological. */
export type Uuid = string;

/** Calendar day, `YYYY-MM-DD`. Used where a wall-clock date is the fact. */
export type IsoDate = string;

/** Full ISO-8601 instant in UTC, `YYYY-MM-DDTHH:mm:ss.sssZ`. */
export type IsoDateTime = string;

/** Every row carries this. Soft-delete only — nothing is ever truly dropped. */
export interface RowMeta {
  updated_at: IsoDateTime;
  deleted_at?: IsoDateTime | null;
}

// ── People ────────────────────────────────────────────────────────────────

export type CoacheeStatus = 'active' | 'paused' | 'alumni';

export interface Coachee extends RowMeta {
  id: Uuid;
  name: string;
  avatar?: string | null;
  status: CoacheeStatus;
  package?: string | null;
  start_date: IsoDate;
  tags: string[];
  contact?: string | null;
  notes?: string | null;
}

// ── Goals & SMARTER ───────────────────────────────────────────────────────

/**
 * SMARTER flags. `E` (Exciting) and `Rw` (Rewarded) get their own booleans
 * because the compendium identifies them as the two she does not explicitly
 * name — the whole point is that the gap becomes visible rather than assumed.
 */
export interface SmarterFlags {
  S: boolean;
  M: boolean;
  A: boolean;
  R: boolean;
  T: boolean;
  E: boolean;
  Rw: boolean;
}

export type GoalStatus = 'open' | 'achieved' | 'dropped';

export interface Goal extends RowMeta {
  id: Uuid;
  coachee_id: Uuid;
  statement: string;
  smarter: SmarterFlags;
  target_date?: IsoDate | null;
  status: GoalStatus;
}

// ── Sessions ──────────────────────────────────────────────────────────────

export type Framework = 'GROW' | 'GREAT';

/** GROW: Goal → Reality → Options → Will. */
export type GrowElement = 'goal' | 'reality' | 'options' | 'will';

/** GREAT: Goals → Reality & Rapport → Explore → Achieve → Take action. */
export type GreatElement = 'goals' | 'reality_rapport' | 'explore' | 'achieve' | 'take_action';

export type ElementKey = GrowElement | GreatElement;

/** Appendix B rubric. */
export type Rating = 'Strong' | 'Adequate' | 'Weak' | 'Met' | 'N/A';

export interface Session extends RowMeta {
  id: Uuid;
  date: IsoDate;
  duration_min: number;
  framework: Framework;
  /** Joint sessions are the real pattern — 2+ coachees on one session. */
  participants: Uuid[];
  summary?: string | null;
  confidence?: number | null;
  commitment?: number | null;
  review_dates: IsoDate[];
  transcript_ref?: string | null;
  /** Wheel domains she called out as low during Reality, for checklist grading. */
  flagged_domains?: string[];
}

export interface SessionElementScore extends RowMeta {
  id: Uuid;
  session_id: Uuid;
  /** Per participant: a joint session grades each cycle separately. */
  coachee_id: Uuid;
  element: ElementKey;
  rating: Rating;
  notes?: string | null;
  /** Quote or paraphrase the rating rests on. AI fills it; coach can edit. */
  evidence?: string | null;
}

export type ChecklistItem =
  | 'smarter_met'
  | 'low_scores_flagged'
  | 'will_step'
  | 'review_date_set';

export type ChecklistState = 'pass' | 'fail' | 'na';

export interface SessionChecklist extends RowMeta {
  id: Uuid;
  session_id: Uuid;
  item: ChecklistItem;
  state: ChecklistState;
  notes?: string | null;
}

// ── Wheel of Life ─────────────────────────────────────────────────────────

/** One row per domain per date — ten rows make one snapshot. */
export interface WheelSnapshotRow extends RowMeta {
  id: Uuid;
  coachee_id: Uuid;
  date: IsoDate;
  domain: string;
  score: number;
  target: number;
}

/** The grouped view the UI and the wheel maths actually work with. */
export interface WheelSnapshot {
  coachee_id: Uuid;
  date: IsoDate;
  domains: Array<{ domain: string; score: number; target: number }>;
}

// ── Actions ───────────────────────────────────────────────────────────────

export type ActionStatus = 'open' | 'in_review' | 'done';

export interface ActionItem extends RowMeta {
  id: Uuid;
  coachee_id: Uuid;
  session_id?: Uuid | null;
  title: string;
  due_date?: IsoDate | null;
  /** First-class, not a tag — the Wed/Sat review rhythm is the discipline. */
  review_date?: IsoDate | null;
  status: ActionStatus;
  completed_at?: IsoDateTime | null;
}

// ── Content ───────────────────────────────────────────────────────────────

export interface Pillar extends RowMeta {
  id: Uuid;
  name: string;
  color: string;
  core_message: string;
  keywords: string[];
}

export type ContentType = 'Reel' | 'Story' | 'Video' | 'Post' | 'Short';

export type ContentPlatform =
  | 'IG'
  | 'TikTok'
  | 'YouTube'
  | 'WhatsApp Status'
  | 'LinkedIn';

export type ContentStatus = 'idea' | 'script' | 'filmed' | 'posted' | 'analyzed';

export interface ContentItem extends RowMeta {
  id: Uuid;
  title: string;
  type: ContentType;
  platform: ContentPlatform;
  pillar_id?: Uuid | null;
  status: ContentStatus;
  hook?: string | null;
  cta?: string | null;
  script?: string | null;
  publish_date?: IsoDate | null;
  link?: string | null;
  metrics?: ContentMetrics | null;
}

/** Manual in v1 — no platform APIs until the coherence loop has earned them. */
export interface ContentMetrics {
  views?: number;
  likes?: number;
  saves?: number;
  comments?: number;
}

export interface Inquiry extends RowMeta {
  id: Uuid;
  date: IsoDate;
  source: string;
  pillar_guess?: Uuid | null;
  converted: boolean;
}

// ── AI ledger ─────────────────────────────────────────────────────────────

export type AiRunKind =
  | 'session_analyzer'
  | 'coherence_checker'
  | 'weekly_digest'
  | 'prep_whisperer';

export interface AiRun extends RowMeta {
  id: Uuid;
  kind: AiRunKind;
  input_ref?: string | null;
  output?: string | null;
  model: string;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  created_at: IsoDateTime;
}

// ── Engage (M8 — schema lands now, surfaces ship in P3/P4) ────────────────

export type ShareLinkKind = 'progress' | 'pulse';

export interface ShareLink extends RowMeta {
  id: Uuid;
  coachee_id: Uuid;
  kind: ShareLinkKind;
  /** 128-bit, never derivable from any id. */
  token: string;
  consent_at?: IsoDateTime | null;
  revoked_at?: IsoDateTime | null;
  expires_at?: IsoDateTime | null;
  view_count: number;
}

export interface PulseResponse extends RowMeta {
  id: Uuid;
  share_link_id: Uuid;
  coachee_id: Uuid;
  date: IsoDate;
  actions_done: Uuid[];
  mini_wheel?: Record<string, number> | null;
  reflection?: string | null;
}

export type NudgeKind = 'review_date' | 'pre_session' | 'streak' | 'pulse_received';

export interface Nudge extends RowMeta {
  id: Uuid;
  kind: NudgeKind;
  entity_ref: string;
  scheduled_at: IsoDateTime;
  sent_at?: IsoDateTime | null;
  opened_at?: IsoDateTime | null;
}

// ── Settings ──────────────────────────────────────────────────────────────

export interface Setting extends RowMeta {
  key: string;
  value: unknown;
}

// ── The whole dataset ─────────────────────────────────────────────────────

/**
 * Everything, in one object. This is the unit of export/import (§6 safety net)
 * and therefore the contract the round-trip gate G2 tests against.
 */
export interface CmwDataset {
  coachees: Coachee[];
  goals: Goal[];
  sessions: Session[];
  session_element_scores: SessionElementScore[];
  session_checklists: SessionChecklist[];
  wheel_snapshots: WheelSnapshotRow[];
  action_items: ActionItem[];
  pillars: Pillar[];
  content_items: ContentItem[];
  inquiries: Inquiry[];
  ai_runs: AiRun[];
  share_links: ShareLink[];
  pulse_responses: PulseResponse[];
  nudges: Nudge[];
  settings: Setting[];
}

export const DATASET_TABLES = [
  'coachees',
  'goals',
  'sessions',
  'session_element_scores',
  'session_checklists',
  'wheel_snapshots',
  'action_items',
  'pillars',
  'content_items',
  'inquiries',
  'ai_runs',
  'share_links',
  'pulse_responses',
  'nudges',
  'settings',
] as const satisfies ReadonlyArray<keyof CmwDataset>;

export type DatasetTable = (typeof DATASET_TABLES)[number];

export function emptyDataset(): CmwDataset {
  return {
    coachees: [],
    goals: [],
    sessions: [],
    session_element_scores: [],
    session_checklists: [],
    wheel_snapshots: [],
    action_items: [],
    pillars: [],
    content_items: [],
    inquiries: [],
    ai_runs: [],
    share_links: [],
    pulse_responses: [],
    nudges: [],
    settings: [],
  };
}
