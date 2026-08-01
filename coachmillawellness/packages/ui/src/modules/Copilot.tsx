/**
 * M6 — the Copilot's shared surface.
 *
 * One panel serves all four features, because the promise they make is the same
 * one and it should not be re-argued per screen: **the AI proposes, she
 * disposes.** Every field it returns is editable before anything is saved, the
 * price is visible before the button is pressed, and a run that goes over budget
 * asks rather than either refusing or spending.
 *
 * The "not configured" state is a first-class design, not a fallback. She may
 * never add a key, and the app is complete without one — so this reads as an
 * optional extra she has not switched on, never as something broken.
 */

import { budgetStatus, describeBudget, formatUsd, type PriceEstimate } from '@cmw/ai';
import type { AiRun } from '@cmw/core';
import { Sparkles, TriangleAlert, Wand2 } from 'lucide-react';
import type { ReactNode } from 'react';

import { Button, Card, Chip, Reveal, cn } from '../primitives/index.js';

/**
 * The standing caveat.
 *
 * Shown wherever a proposal is displayed rather than once in Settings: the
 * moment that matters is the one where she is looking at a rating the machine
 * suggested, not the moment she pasted a key.
 */
export function AiCaveat({ className }: { className?: string }) {
  return (
    <p className={cn('flex items-center gap-1.5 text-xs text-lo', className)}>
      <Sparkles size={13} className="shrink-0 text-accent-ink" aria-hidden />
      Drafted by AI. Edit anything before you save — nothing is written until you accept it.
    </p>
  );
}

/** The link between "AI is off" and the one screen that turns it on. */
export function CopilotOffNote({ what }: { what: string }) {
  return (
    <Card className="border-dashed">
      <p className="text-sm text-hi">{what} needs the Copilot.</p>
      <p className="mt-1 text-sm text-lo">
        Add an Anthropic API key under Vault &amp; settings to switch it on. Everything else in the
        app works without it, and always will.
      </p>
      <Button
        variant="quiet"
        className="mt-3"
        onClick={() => {
          window.location.hash = '#/vault';
        }}
      >
        Open settings
      </Button>
    </Card>
  );
}

/**
 * The run control: price, button, error, and the over-budget choice.
 *
 * The estimate sits beside the button rather than behind a tooltip because the
 * decision it informs is made in the same second the button is pressed.
 */
export function CopilotRunBar({
  label,
  estimate,
  running,
  error,
  overBudget,
  onRun,
  disabled,
}: {
  label: string;
  estimate: PriceEstimate | null;
  running: boolean;
  error: string | null;
  overBudget: boolean;
  onRun: (allowOverBudget?: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
        <Button
          variant="primary"
          icon={<Wand2 size={16} />}
          disabled={running || disabled}
          onClick={() => onRun()}
        >
          {running ? 'Reading…' : label}
        </Button>
        {estimate ? (
          <span className="text-xs text-lo">
            about {formatUsd(estimate.cost_usd)} · {estimate.model}
          </span>
        ) : null}
      </div>

      {error ? (
        <Reveal>
          <div className="mt-3 flex items-start gap-2 rounded-md border border-warn/40 bg-raised p-3">
            <TriangleAlert size={16} className="mt-0.5 shrink-0 text-warn-ink" aria-hidden />
            <div className="text-sm text-hi">
              <p role="alert">{error}</p>
              {overBudget ? (
                <Button variant="quiet" className="mt-2" onClick={() => onRun(true)}>
                  Run it anyway
                </Button>
              ) : null}
            </div>
          </div>
        </Reveal>
      ) : null}
    </div>
  );
}

/**
 * Where the month's AI spend stands.
 *
 * §9 asks for a warning at 80%. Rendering the figure continuously rather than
 * only at the threshold means the warning is never the first time she learns
 * there was a meter.
 */
export function BudgetMeter({
  runs,
  capUsd,
  className,
}: {
  runs: readonly AiRun[];
  capUsd: number;
  className?: string;
}) {
  const status = budgetStatus(runs, { cap_usd: capUsd });
  const tone = status.state === 'over' ? 'danger' : status.state === 'warning' ? 'warn' : 'accent';
  // The Chip's tone vocabulary and the CSS custom properties disagree on one
  // name — the token is `--cmw-error` while the tone is `danger` — so the bar
  // maps rather than interpolating the tone straight into a variable name.
  const fill = tone === 'danger' ? 'error' : tone;

  return (
    <div className={className}>
      <div className="mb-1.5 flex items-baseline justify-between gap-3">
        <span className="text-sm text-hi">This month</span>
        <Chip tone={tone}>
          {formatUsd(status.spent_usd)} of {formatUsd(status.cap_usd)}
        </Chip>
      </div>
      <div className="h-2 overflow-hidden rounded-pill bg-raised">
        <div
          className="h-full rounded-pill transition-[width] duration-500"
          style={{
            width: `${Math.min(100, status.pct)}%`,
            backgroundColor: `var(--cmw-${fill})`,
          }}
        />
      </div>
      <p className="mt-2 text-sm text-lo">{describeBudget(status)}</p>
      {status.runs > 0 ? (
        <p className="mt-1 text-xs text-lo">
          {status.runs} run{status.runs === 1 ? '' : 's'} logged. Every call is on the ledger with
          its token count and cost.
        </p>
      ) : null}
    </div>
  );
}

/** A proposal, with its accept/discard pair always in the same place. */
export function ProposalCard({
  title,
  hint,
  children,
  onAccept,
  onDiscard,
  acceptLabel = 'Save these',
  acceptDisabled,
}: {
  title: string;
  hint?: string;
  children: ReactNode;
  onAccept: () => void;
  onDiscard: () => void;
  acceptLabel?: string;
  acceptDisabled?: boolean;
}) {
  return (
    <Reveal>
      <Card className="mt-4 border-accent/40">
        <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="font-display text-lg text-hi">{title}</h3>
            {hint ? <p className="mt-0.5 text-sm text-lo">{hint}</p> : null}
          </div>
          <Chip tone="accent">Draft</Chip>
        </div>

        {children}

        <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-edge pt-4">
          <AiCaveat />
          <div className="flex gap-2">
            <Button variant="ghost" onClick={onDiscard}>
              Discard
            </Button>
            <Button variant="primary" onClick={onAccept} disabled={acceptDisabled}>
              {acceptLabel}
            </Button>
          </div>
        </div>
      </Card>
    </Reveal>
  );
}
