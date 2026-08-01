/**
 * M4 — CONTENT STUDIO.
 *
 * The third leg of the product triad. Four things on one screen because they only
 * mean something together: the pillars she stands for, the pipeline of work in
 * flight, the consistency of what actually went out, and the coherence map that
 * shows whether the two agree.
 *
 * Everything counts *published* work by default. Counting drafts would let a
 * starved pillar look healthy because she has been meaning to post about it,
 * which is exactly the self-deception the map exists to break.
 */

import {
  PIPELINE_ORDER,
  coherenceMatrix,
  consistencyHeatmap,
  pipelineFunnel,
  publishStreak,
  toIsoDate,
  type CmwDataset,
  type ContentPlatform,
  type ContentStatus,
  type ContentType,
  type Uuid,
} from '@cmw/core';
import { palette } from '@cmw/tokens';
import { Plus, Trash2 } from 'lucide-react';
import { useMemo, useState } from 'react';

import { CoherenceGrid, ConsistencyHeatmap, PipelineFunnel, StatTile } from '../charts/index.js';
import { liveContent, livePillars, useStore } from '../app/store.js';
import {
  Button,
  Card,
  Chip,
  EmptyState,
  Modal,
  PageHeader,
  Reveal,
  SectionHeader,
  Select,
  TextArea,
  TextInput,
  cn,
} from '../primitives/index.js';
import { CoherenceChecker } from './CoherenceChecker.js';

const TYPES: ContentType[] = ['Reel', 'Story', 'Video', 'Post', 'Short'];
const PLATFORMS: ContentPlatform[] = ['IG', 'TikTok', 'YouTube', 'WhatsApp Status', 'LinkedIn'];

const PILLAR_COLOURS = [
  palette.jacaranda400,
  palette.sage400,
  palette.amber400,
  palette.coral400,
  palette.info400,
  palette.jacaranda600,
];

export function Content({ data }: { data: CmwDataset }) {
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<Uuid | null>(null);
  const [filter, setFilter] = useState<ContentStatus | 'all'>('all');
  const [addingPillar, setAddingPillar] = useState(false);

  const pillars = livePillars(data);
  const items = liveContent(data);
  const today = toIsoDate(new Date());

  const matrix = useMemo(
    () => coherenceMatrix(pillars, items, { now: today }),
    [pillars, items, today],
  );
  const heatmap = useMemo(() => consistencyHeatmap(items, { now: today, days: 91 }), [items, today]);
  const funnel = useMemo(() => pipelineFunnel(items), [items]);
  const streak = useMemo(() => publishStreak(items, { now: today }), [items, today]);

  const visible = filter === 'all' ? items : items.filter((i) => i.status === filter);

  return (
    <div>
      <PageHeader
        eyebrow="Content studio"
        title="Content"
        subtitle="Pillars, pipeline and the coherence map — so what you publish stays on message with what you actually stand for."
        action={
          <Button variant="primary" icon={<Plus size={16} />} onClick={() => setCreating(true)}>
            New idea
          </Button>
        }
      />

      <div className="mb-7 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="Published, 30 days" value={matrix.rows.reduce((n, r) => n + (r.cells[0]?.count ?? 0), 0)} />
        <StatTile
          label="Message balance"
          value={`${Math.round(matrix.balance * 100)}%`}
          hint={matrix.drift > 0.35 ? 'One pillar is crowding out the rest' : 'Evenly served'}
          tone={matrix.drift > 0.35 ? 'warn-ink' : 'success-ink'}
        />
        <StatTile
          label="Starved pillars"
          value={matrix.starved_pillars.length}
          hint={matrix.starved_pillars.join(', ') || 'None'}
          tone={matrix.starved_pillars.length > 0 ? 'warn-ink' : 'hi'}
        />
        <StatTile
          label="Publishing streak"
          value={streak.current}
          hint={`best ${streak.longest} ${streak.longest === 1 ? 'day' : 'days'}`}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* ── Coherence map ─────────────────────────────────────────────── */}
        <section>
          <SectionHeader
            title="Coherence map"
            hint="Posts serving each pillar, by window"
            action={
              <Button variant="quiet" onClick={() => setAddingPillar(true)}>
                Add pillar
              </Button>
            }
          />
          <Card>
            {pillars.length === 0 ? (
              <div className="py-2">
                <p className="text-sm text-lo">
                  Pillars are the backbone of coherence — three to six messages you want to be
                  known for. Without them the map has nothing to measure against.
                </p>
                <Button variant="primary" className="mt-3" onClick={() => setAddingPillar(true)}>
                  Add your first pillar
                </Button>
              </div>
            ) : (
              <>
                <CoherenceGrid rows={matrix.rows} windows={matrix.windows} />
                {matrix.unassigned > 0 ? (
                  <p className="mt-3 border-t border-edge pt-3 text-sm text-warn-ink">
                    {matrix.unassigned} published post
                    {matrix.unassigned === 1 ? '' : 's'} serve no pillar — invisible to the
                    coherence story.
                  </p>
                ) : null}
                {matrix.dominant_pillar && matrix.drift > 0.35 ? (
                  <p className="mt-3 text-sm text-lo">
                    “{matrix.dominant_pillar}” is doing most of the talking. That is fine if it is
                    deliberate.
                  </p>
                ) : null}
              </>
            )}
          </Card>

          {pillars.length > 0 ? (
            <ul className="mt-3 flex flex-col gap-2">
              {pillars.map((pillar) => (
                <li key={pillar.id}>
                  <Card>
                    <div className="flex items-start gap-2.5">
                      <span
                        aria-hidden="true"
                        className="mt-1 size-3 shrink-0 rounded-pill"
                        style={{ backgroundColor: pillar.color }}
                      />
                      <div className="min-w-0 flex-1">
                        <p className="font-medium text-hi">{pillar.name}</p>
                        <p className="mt-0.5 text-sm text-lo">{pillar.core_message}</p>
                      </div>
                      <Button
                        variant="ghost"
                        title={`Remove ${pillar.name}`}
                        className="min-h-9 shrink-0 px-2"
                        icon={<Trash2 size={14} />}
                        onClick={() => void useStore.getState().removePillar(pillar.id)}
                      />
                    </div>
                  </Card>
                </li>
              ))}
            </ul>
          ) : null}
        </section>

        <div className="flex flex-col gap-6">
          {/* ── Consistency ────────────────────────────────────────────── */}
          <section>
            <SectionHeader title="Consistency" hint="Last 13 weeks of publishing" />
            <Card>
              <ConsistencyHeatmap days={heatmap} />
            </Card>
          </section>

          {/* ── Pipeline ───────────────────────────────────────────────── */}
          <section>
            <SectionHeader title="Pipeline" hint="Idea → Script → Filmed → Posted → Analyzed" />
            <Card>
              <PipelineFunnel
                stages={funnel}
                onSelect={(status) =>
                  setFilter((current) => (current === status ? 'all' : (status as ContentStatus)))
                }
              />
            </Card>
          </section>
        </div>
      </div>

      {/* ── The board ────────────────────────────────────────────────────── */}
      <section className="mt-7">
        <SectionHeader
          title="Everything"
          hint={filter === 'all' ? `${items.length} items` : `filtered to ${filter}`}
          action={
            filter !== 'all' ? (
              <Button variant="ghost" onClick={() => setFilter('all')}>
                Clear filter
              </Button>
            ) : undefined
          }
        />

        {items.length === 0 ? (
          <EmptyState
            title="Nothing in the studio yet"
            body="Capture an idea while it is fresh. It can be one line — the pipeline is there to move it along later."
            action={
              <Button variant="primary" icon={<Plus size={16} />} onClick={() => setCreating(true)}>
                New idea
              </Button>
            }
          />
        ) : (
          <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {visible.map((item, index) => {
              const pillar = pillars.find((p) => p.id === item.pillar_id);
              return (
                <li key={item.id}>
                  <Reveal delay={Math.min(index, 8) * 0.04}>
                    <Card className="flex h-full flex-col">
                      <button
                        type="button"
                        onClick={() => setEditing(item.id)}
                        className="text-left"
                      >
                        <p className="font-medium text-hi">{item.title}</p>
                        {item.hook ? (
                          <p className="cmw-clamp-2 mt-1 text-sm text-lo">{item.hook}</p>
                        ) : null}
                      </button>

                      <div className="mt-3 flex flex-wrap gap-1.5">
                        <Chip tone="neutral">{item.type}</Chip>
                        <Chip tone="neutral">{item.platform}</Chip>
                        {pillar ? (
                          <Chip tone="accent" title={pillar.core_message}>
                            {pillar.name}
                          </Chip>
                        ) : (
                          <Chip tone="warn">No pillar</Chip>
                        )}
                      </div>

                      {/* Moving a card to Posted stamps today's date if it has
                          none — otherwise it stays invisible to the map. */}
                      <div className="mt-auto flex flex-wrap items-center gap-1 border-t border-edge pt-3">
                        {PIPELINE_ORDER.map((status) => (
                          <button
                            key={status}
                            type="button"
                            onClick={() => void useStore.getState().setContentStatus(item.id, status)}
                            aria-current={item.status === status ? 'true' : undefined}
                            className={cn(
                              'min-h-9 rounded-sm px-1.5 text-xs capitalize transition-colors duration-150',
                              item.status === status
                                ? 'bg-accent-quiet font-medium text-accent-ink'
                                : 'text-lo hover:bg-raised hover:text-hi',
                            )}
                          >
                            {status}
                          </button>
                        ))}
                      </div>

                      {item.publish_date ? (
                        <p className="mt-2 text-xs text-lo">
                          {item.status === 'posted' || item.status === 'analyzed'
                            ? 'Published'
                            : 'Scheduled'}{' '}
                          {item.publish_date}
                        </p>
                      ) : null}
                    </Card>
                  </Reveal>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <ContentModal
        data={data}
        id={editing}
        open={creating || editing !== null}
        onClose={() => {
          setCreating(false);
          setEditing(null);
        }}
      />

      <PillarModal
        open={addingPillar}
        onClose={() => setAddingPillar(false)}
        existing={pillars.length}
      />
    </div>
  );
}

function ContentModal({
  data,
  id,
  open,
  onClose,
}: {
  data: CmwDataset;
  id: Uuid | null;
  open: boolean;
  onClose: () => void;
}) {
  const existing = id ? data.content_items.find((c) => c.id === id) : undefined;
  const pillars = livePillars(data);

  // Newest first, published only — the same rule the coherence map uses, so the
  // "where your message already is" context matches what the map shows.
  const publishedRecently = liveContent(data)
    .filter((c) => c.id !== id && (c.status === 'posted' || c.status === 'analyzed'))
    .sort((a, b) => (b.publish_date ?? '').localeCompare(a.publish_date ?? ''))
    .slice(0, 5);

  const [title, setTitle] = useState(existing?.title ?? '');
  const [type, setType] = useState<ContentType>(existing?.type ?? 'Reel');
  const [platform, setPlatform] = useState<ContentPlatform>(existing?.platform ?? 'IG');
  const [pillarId, setPillarId] = useState<string>(existing?.pillar_id ?? '');
  const [hook, setHook] = useState(existing?.hook ?? '');
  const [cta, setCta] = useState(existing?.cta ?? '');
  const [script, setScript] = useState(existing?.script ?? '');
  const [publishDate, setPublishDate] = useState(existing?.publish_date ?? '');

  // Re-seed the form when a different card is opened.
  const [seeded, setSeeded] = useState<string | null>(id);
  if (seeded !== id) {
    setSeeded(id);
    setTitle(existing?.title ?? '');
    setType(existing?.type ?? 'Reel');
    setPlatform(existing?.platform ?? 'IG');
    setPillarId(existing?.pillar_id ?? '');
    setHook(existing?.hook ?? '');
    setCta(existing?.cta ?? '');
    setScript(existing?.script ?? '');
    setPublishDate(existing?.publish_date ?? '');
  }

  const submit = async (): Promise<void> => {
    if (title.trim().length < 2) return;
    const patch = {
      title,
      type,
      platform,
      pillar_id: pillarId || null,
      hook: hook || null,
      cta: cta || null,
      script: script || null,
      publish_date: publishDate || null,
    };
    if (existing) await useStore.getState().updateContent(existing.id, patch);
    else await useStore.getState().addContent(patch);
    onClose();
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={existing ? 'Edit content' : 'New idea'}
      footer={
        <>
          {existing ? (
            <Button
              variant="danger"
              onClick={() => {
                void useStore.getState().removeContent(existing.id);
                onClose();
              }}
            >
              Delete
            </Button>
          ) : null}
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" onClick={submit}>
            {existing ? 'Save' : 'Add'}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <TextInput
          label="Title"
          value={title}
          onChange={setTitle}
          placeholder="The 20-minute rule"
          autoFocus
        />
        <div className="grid grid-cols-2 gap-3">
          <Select
            label="Type"
            value={type}
            options={TYPES.map((t) => ({ value: t, label: t }))}
            onChange={setType}
          />
          <Select
            label="Platform"
            value={platform}
            options={PLATFORMS.map((p) => ({ value: p, label: p }))}
            onChange={setPlatform}
          />
        </div>
        <Select
          label="Pillar"
          value={pillarId}
          options={[
            { value: '', label: 'No pillar yet' },
            ...pillars.map((p) => ({ value: p.id, label: p.name })),
          ]}
          onChange={setPillarId}
          hint="Unassigned posts do not appear on the coherence map."
        />
        <TextInput label="Hook" value={hook} onChange={setHook} placeholder="First line that stops the scroll" />
        <TextInput label="Call to action" value={cta} onChange={setCta} placeholder="Save this for tomorrow" />
        <TextInput
          label="Publish date"
          type="date"
          value={publishDate}
          onChange={setPublishDate}
          hint="Scheduled, or the day it actually went out."
        />
        <TextArea label="Script" value={script} onChange={setScript} rows={5} />

        {/*
          The check runs on this draft, not on the saved row — the answer is only
          worth having before it goes out.
        */}
        <CoherenceChecker
          draft={{
            id: existing?.id ?? 'draft',
            title,
            type,
            platform,
            pillar_id: pillarId || null,
            status: existing?.status ?? 'idea',
            hook: hook || null,
            cta: cta || null,
            script: script || null,
            publish_date: publishDate || null,
            updated_at: existing?.updated_at ?? '',
          }}
          pillar={pillars.find((p) => p.id === pillarId) ?? null}
          recent={publishedRecently}
          onUseHook={setHook}
        />
      </div>
    </Modal>
  );
}

function PillarModal({
  open,
  onClose,
  existing,
}: {
  open: boolean;
  onClose: () => void;
  existing: number;
}) {
  const [name, setName] = useState('');
  const [message, setMessage] = useState('');

  const submit = async (): Promise<void> => {
    if (name.trim().length < 2) return;
    await useStore.getState().addPillar({
      name,
      core_message: message,
      color: PILLAR_COLOURS[existing % PILLAR_COLOURS.length]!,
    });
    setName('');
    setMessage('');
    onClose();
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Add a message pillar"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" onClick={submit}>
            Add pillar
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {existing >= 6 ? (
          <p className="text-sm text-warn-ink">
            You already have six. More than that and the coherence map stops being a diagnosis and
            becomes a list.
          </p>
        ) : null}
        <TextInput
          label="Pillar name"
          value={name}
          onChange={setName}
          placeholder="Start before you are ready"
          autoFocus
        />
        <TextArea
          label="Core message"
          value={message}
          onChange={setMessage}
          rows={3}
          placeholder="Action creates clarity. Waiting to feel ready is the trap."
          hint="This is what a script gets checked against."
        />
      </div>
    </Modal>
  );
}
