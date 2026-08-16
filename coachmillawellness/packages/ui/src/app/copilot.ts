/**
 * Wiring the Copilot to the app (§9, prompt P4).
 *
 * `@cmw/ai` knows nothing about storage or React; this file is the only place
 * the two meet. It reads her settings, hands the ledger in as a getter so the
 * budget guardrail sees spend from this second rather than from mount, and gives
 * every screen one hook that cannot forget to write the ledger row.
 *
 * The key never leaves this device. It lives in IndexedDB under a setting that
 * `UNEXPORTED_SETTING_KEYS` excludes from every backup file, so a backup she
 * forwards over WhatsApp does not carry her credential (§6).
 */

import {
  DEFAULT_BUDGET_USD,
  DEFAULT_MODELS,
  MODELS,
  anthropicTransport,
  createCopilot,
  isAiModelId,
  proxyTransport,
  AiError,
  type AiModelId,
  type Copilot,
  type CopilotResult,
  type RunOptions,
} from '@cmw/ai';
import type { AiRunKind } from '@cmw/core';
import { SETTING_KEYS } from '@cmw/data';
import { useMemo, useState } from 'react';

import { useStore } from './store.js';

/**
 * Per-feature model choice, stored as one setting rather than four.
 *
 * One row keeps the Settings screen's save path simple and means an older
 * backup restoring a partial object still resolves — anything absent falls back
 * to §9's default for that feature.
 */
export const AI_MODELS_SETTING = 'ai_models';

/** Where the proxy lives, for the hosted builds. Empty in Build 1. */
export const AI_PROXY_SETTING = 'ai_proxy_endpoint';

export function useAiSettings() {
  const settings = useStore((state) => state.data.settings);

  return useMemo(() => {
    const read = <T,>(key: string, fallback: T): T => {
      const found = settings.find((s) => s.key === key);
      return found === undefined || found.value === null ? fallback : (found.value as T);
    };

    const stored = read<Partial<Record<AiRunKind, string>>>(AI_MODELS_SETTING, {});
    const models: Partial<Record<AiRunKind, AiModelId>> = {};
    for (const [kind, id] of Object.entries(stored)) {
      if (isAiModelId(id)) models[kind as AiRunKind] = id;
    }

    return {
      apiKey: read<string>(SETTING_KEYS.anthropicApiKey, '').trim(),
      proxyEndpoint: read<string>(AI_PROXY_SETTING, '').trim(),
      budgetUsd: read<number>(SETTING_KEYS.aiBudgetUsd, DEFAULT_BUDGET_USD),
      wheelDomains: read<string[]>(SETTING_KEYS.wheelDomains, []),
      models,
    };
  }, [settings]);
}

/**
 * The live Copilot.
 *
 * Rebuilt only when something that changes its behaviour changes — not on every
 * ledger write, which would otherwise rebuild it after each call it makes. The
 * ledger is therefore read through `useStore.getState()` at call time rather
 * than captured, which is also what lets the guardrail count a run made seconds
 * ago in another tab.
 */
export function useCopilot(): Copilot {
  const { apiKey, proxyEndpoint, budgetUsd, wheelDomains, models } = useAiSettings();
  const modelKey = JSON.stringify(models);

  return useMemo(() => {
    const transport = proxyEndpoint
      ? proxyTransport({ endpoint: proxyEndpoint })
      : apiKey
        ? anthropicTransport({ apiKey })
        : null;

    return createCopilot({
      transport,
      models: JSON.parse(modelKey) as Partial<Record<AiRunKind, AiModelId>>,
      budgetUsd,
      wheelDomains,
      ledger: () => useStore.getState().data.ai_runs,
    });
    // `modelKey` and the joined domains stand in for two objects that are rebuilt
    // on every settings read — comparing them by identity would rebuild the
    // Copilot, and its cached methodology prompt, on every keystroke in Settings.
  }, [apiKey, proxyEndpoint, budgetUsd, modelKey, wheelDomains.join('|')]);
}

export interface CopilotRunState<T> {
  data: T | null;
  running: boolean;
  /** Plain-language guidance, already resolved from the failure's cause. */
  error: string | null;
  /** Present when the failure is one she can choose to override. */
  overBudget: boolean;
}

export interface CopilotRunApi<T> extends CopilotRunState<T> {
  run: (allowOverBudget?: boolean) => Promise<void>;
  reset: () => void;
  /** Replaces the proposal in place, so every AI field stays editable (§9). */
  edit: (next: T) => void;
}

/**
 * Runs one Copilot call and keeps the app honest about it.
 *
 * Three things happen here that must never be left to a call site: the ledger
 * row is persisted whether the call succeeded or produced an unusable answer,
 * the budget refusal is surfaced as a choice rather than an error, and the
 * result stays editable after it arrives.
 */
export function useCopilotRun<T>(
  call: (options: RunOptions) => Promise<CopilotResult<T>>,
): CopilotRunApi<T> {
  const [state, setState] = useState<CopilotRunState<T>>({
    data: null,
    running: false,
    error: null,
    overBudget: false,
  });

  const run = async (allowOverBudget = false): Promise<void> => {
    setState((prev) => ({ ...prev, running: true, error: null, overBudget: false }));
    try {
      const { data, run: ledgerRow } = await call(allowOverBudget ? { allowOverBudget } : {});
      await useStore.getState().logAiRun(ledgerRow);
      setState({ data, running: false, error: null, overBudget: false });
    } catch (cause) {
      // A billed call that failed validation still carries its row. Dropping it
      // would make the month's spend read lower than her card statement.
      if (cause instanceof AiError && cause.run) {
        await useStore.getState().logAiRun(cause.run);
      }
      const failure = cause instanceof AiError ? cause : null;
      setState({
        data: null,
        running: false,
        error: failure?.hint ?? (cause instanceof Error ? cause.message : String(cause)),
        overBudget: failure?.code === 'budget',
      });
    }
  };

  return {
    ...state,
    run,
    reset: () => setState({ data: null, running: false, error: null, overBudget: false }),
    edit: (next) => setState((prev) => ({ ...prev, data: next })),
  };
}

/** Model choices for the Settings pickers, with §9's default marked. */
export function modelOptions(kind: AiRunKind): Array<{ value: AiModelId; label: string }> {
  return (Object.keys(MODELS) as AiModelId[]).map((id) => ({
    value: id,
    label: id === DEFAULT_MODELS[kind] ? `${MODELS[id].label} (default)` : MODELS[id].label,
  }));
}
