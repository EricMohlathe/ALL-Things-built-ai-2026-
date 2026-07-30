/**
 * M3 — WHEEL OF LIFE LAB.
 *
 * The wheel gets its own room, for the two things the client-detail tab is the
 * wrong shape for: the before/after split view she screenshots into a client
 * report, and editing the domain list itself (the ten domains are per-coachee and
 * editable, not fixed).
 */

import {
  WHEEL_DOMAINS_DEFAULT,
  groupWheelRows,
  toIsoDate,
  wheelAverage,
  wheelDelta,
  type CmwDataset,
  type Uuid,
} from '@cmw/core';
import { ArrowRight, Download, Plus, Trash2 } from 'lucide-react';
import { useState } from 'react';

import { StatTile } from '../charts/index.js';
import { navigate } from '../app/router.js';
import { liveCoachees, useStore, wheelRowsFor } from '../app/store.js';
import {
  Button,
  Card,
  Chip,
  EmptyState,
  Numeric,
  PageHeader,
  Reveal,
  SectionHeader,
  TextInput,
  cn,
} from '../primitives/index.js';
import { LivingWheel } from '../wheel/LivingWheel.js';
import { downloadBlob, wheelPngBlob } from '../wheel/export.js';

export function WheelLab({ data, id }: { data: CmwDataset; id?: Uuid }) {
  const coachees = liveCoachees(data);
  const selected = id ?? coachees[0]?.id;
  const [compare, setCompare] = useState(false);

  if (coachees.length === 0) {
    return (
      <div>
        <PageHeader eyebrow="Signature" title="Wheel Lab" />
        <EmptyState
          title="No coachees yet"
          body="The wheel needs someone to be about. Add a coachee and their first snapshot appears here."
          action={
            <Button variant="primary" onClick={() => navigate({ name: 'clients' })}>
              Add a coachee
            </Button>
          }
        />
      </div>
    );
  }

  const coachee = coachees.find((c) => c.id === selected) ?? coachees[0]!;
  const snapshots = groupWheelRows(wheelRowsFor(data, coachee.id), coachee.id);
  const latest = snapshots[snapshots.length - 1] ?? null;
  const first = snapshots[0] ?? null;
  const delta = wheelDelta(first, latest);

  const domains = useStore
    .getState()
    .setting<string[]>('wheel_domains', [...WHEEL_DOMAINS_DEFAULT]);

  const values = latest?.domains ?? domains.map((domain) => ({ domain, score: 5, target: 8 }));

  const exportPng = async (): Promise<void> => {
    try {
      const blob = await wheelPngBlob({
        domains: values,
        title: coachee.name.split(/\s+/)[0],
        subtitle: latest ? `Wheel of Life · ${latest.date}` : 'Wheel of Life',
      });
      downloadBlob(blob, `wheel-${coachee.id.slice(0, 8)}.png`);
      useStore.getState().toast('success', 'Wheel exported.');
    } catch (cause) {
      useStore.getState().toast('error', cause instanceof Error ? cause.message : 'Export failed.');
    }
  };

  return (
    <div>
      <PageHeader
        eyebrow="Signature"
        title="Wheel Lab"
        subtitle="Ten domains, scored 0–10 against a target. Drag a spoke or use the sliders — both write the same snapshot."
        action={
          <Button variant="quiet" icon={<Download size={16} />} onClick={exportPng}>
            Export PNG
          </Button>
        }
      />

      <div className="mb-5 flex flex-wrap gap-1.5">
        {coachees.map((option) => (
          <Chip
            key={option.id}
            tone={option.id === coachee.id ? 'accent' : 'neutral'}
            pressed={option.id === coachee.id}
            onClick={() => navigate({ name: 'wheel', id: option.id })}
          >
            {option.name}
          </Chip>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <Card>
          {/*
            Before/after split — the shape that makes progress legible in a
            client report. Only offered when there is genuinely something to
            compare, so it never shows the same wheel twice.
          */}
          {compare && first && latest && first.date !== latest.date ? (
            <div className="grid gap-6 sm:grid-cols-2">
              <div className="flex flex-col items-center">
                <p className="mb-2 text-sm text-lo">{first.date}</p>
                <LivingWheel
                  domains={first.domains}
                  size={300}
                  showLabels={false}
                  ariaLabel={`Wheel on ${first.date}, average ${wheelAverage(first)}`}
                />
                <Numeric className="mt-2 text-xl text-hi">{wheelAverage(first)}</Numeric>
              </div>
              <div className="flex flex-col items-center">
                <p className="mb-2 text-sm text-lo">{latest.date}</p>
                <LivingWheel
                  domains={latest.domains}
                  size={300}
                  showLabels={false}
                  improved={delta.improved}
                  snapshotKey={latest.date}
                  ariaLabel={`Wheel on ${latest.date}, average ${wheelAverage(latest)}`}
                />
                <Numeric className="mt-2 text-xl text-success-ink">
                  {wheelAverage(latest)}
                </Numeric>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center">
              <LivingWheel
                domains={values}
                editable
                size={480}
                improved={delta.improved}
                snapshotKey={latest?.date}
                onScoreChange={(domain, score) => {
                  const next = values.map((v) => (v.domain === domain ? { ...v, score } : v));
                  void useStore.getState().saveWheelSnapshot({
                    coachee_id: coachee.id,
                    date: latest?.date ?? toIsoDate(new Date()),
                    domains: next,
                  });
                }}
              />
            </div>
          )}

          {snapshots.length > 1 ? (
            <div className="mt-5 flex justify-center border-t border-edge pt-4">
              <Button variant="quiet" onClick={() => setCompare((current) => !current)}>
                {compare ? 'Back to scoring' : 'Before and after'}
              </Button>
            </div>
          ) : null}
        </Card>

        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-2 gap-2">
            <StatTile
              label="Snapshots"
              value={snapshots.length}
              hint={latest ? `latest ${latest.date}` : 'none yet'}
            />
            <StatTile
              label="Average"
              value={wheelAverage(latest) ?? '—'}
              hint={
                delta.average_delta === null
                  ? undefined
                  : `${delta.average_delta > 0 ? '+' : ''}${delta.average_delta} all time`
              }
              tone={
                delta.average_delta !== null && delta.average_delta > 0 ? 'success-ink' : 'hi'
              }
            />
          </div>

          {delta.improved.length > 0 || delta.declined.length > 0 ? (
            <Card>
              <SectionHeader title="Movement" hint="First snapshot to latest" />
              {delta.improved.length > 0 ? (
                <div className="mb-2">
                  <p className="text-sm text-success-ink">Improved</p>
                  <p className="text-sm text-lo">{delta.improved.join(', ')}</p>
                </div>
              ) : null}
              {delta.declined.length > 0 ? (
                <div>
                  <p className="text-sm text-warn-ink">Declined</p>
                  <p className="text-sm text-lo">{delta.declined.join(', ')}</p>
                </div>
              ) : null}
            </Card>
          ) : null}

          <DomainEditor domains={domains} />

          <Button
            variant="primary"
            onClick={() =>
              void useStore.getState().saveWheelSnapshot({
                coachee_id: coachee.id,
                date: toIsoDate(new Date()),
                domains: values.map((v) => ({ ...v })),
              })
            }
            full
          >
            Save today's snapshot
          </Button>
        </div>
      </div>
    </div>
  );
}

/**
 * Domain editor. The list is a setting rather than a constant because her
 * practice varies it per client — someone with no partner does not need a
 * Romance spoke scored at zero every month.
 */
function DomainEditor({ domains }: { domains: string[] }) {
  const [adding, setAdding] = useState('');

  const save = (next: string[]): void => {
    void useStore.getState().setWheelDomains(next);
  };

  return (
    <Card>
      <SectionHeader title="Domains" hint={`${domains.length} on the wheel`} />
      <ul className="flex flex-col gap-1">
        {domains.map((domain, index) => (
          <li key={domain} className="flex items-center gap-2">
            <span
              aria-hidden="true"
              className="size-2.5 shrink-0 rounded-pill"
              style={{ backgroundColor: `var(--cmw-wheel-${(index % 10) + 1})` }}
            />
            <span className="flex-1 truncate text-sm text-hi">{domain}</span>
            <Button
              variant="ghost"
              title={`Remove ${domain}`}
              className="min-h-9 px-2"
              icon={<Trash2 size={14} />}
              onClick={() => save(domains.filter((d) => d !== domain))}
            />
          </li>
        ))}
      </ul>

      <div className="mt-3 flex items-end gap-2 border-t border-edge pt-3">
        <div className="flex-1">
          <TextInput
            label="Add a domain"
            value={adding}
            onChange={setAdding}
            placeholder="Creativity"
            onEnter={() => {
              const name = adding.trim();
              if (name && !domains.includes(name)) {
                save([...domains, name]);
                setAdding('');
              }
            }}
          />
        </div>
        <Button
          variant="quiet"
          label="Add domain"
          icon={<Plus size={16} />}
          onClick={() => {
            const name = adding.trim();
            if (name && !domains.includes(name)) {
              save([...domains, name]);
              setAdding('');
            }
          }}
        />
      </div>

      {domains.length !== WHEEL_DOMAINS_DEFAULT.length ? (
        <Button
          variant="ghost"
          className="mt-2 text-xs"
          onClick={() => save([...WHEEL_DOMAINS_DEFAULT])}
        >
          Reset to the standard ten
        </Button>
      ) : null}
    </Card>
  );
}
