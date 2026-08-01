/**
 * Reading a past run back out of the ledger.
 *
 * The `ai_run` table already stores each call's JSON output, so a digest written
 * on Monday can be shown on Wednesday without a second call and without a second
 * table to keep in sync. That is the whole mechanism: the ledger is the cache.
 *
 * Stored output is re-validated through the same contract rather than trusted.
 * A row can outlive the version of the app that wrote it — restored from an old
 * backup, or synced from a device on an older build — and a shape that has since
 * changed should render as "nothing stored" rather than crash a screen.
 */

import type { AiRun, AiRunKind } from '@cmw/core';

import { AiContractError, type AiContract } from './contracts.js';

export interface StoredRun<T> {
  data: T;
  run: AiRun;
}

/**
 * The newest usable run of a kind, optionally for one subject.
 *
 * `inputRef` is matched exactly, so `week:2099-03-09` finds that week's digest
 * and nothing else — the Deck must never show last week's brief as if it were
 * today's.
 */
export function latestRun<T>(
  runs: readonly AiRun[],
  kind: AiRunKind,
  contract: AiContract<T>,
  inputRef?: string,
): StoredRun<T> | null {
  const candidates = runs
    .filter(
      (run) =>
        !run.deleted_at &&
        run.kind === kind &&
        run.output !== null &&
        run.output !== undefined &&
        (inputRef === undefined || run.input_ref === inputRef),
    )
    .sort((a, b) => b.created_at.localeCompare(a.created_at));

  for (const run of candidates) {
    const parsed = readOutput(run, contract);
    if (parsed !== null) return { data: parsed, run };
  }
  return null;
}

/** `null` for anything unreadable — malformed JSON or a since-changed shape. */
function readOutput<T>(run: AiRun, contract: AiContract<T>): T | null {
  if (!run.output) return null;
  let json: unknown;
  try {
    json = JSON.parse(run.output) as unknown;
  } catch {
    return null;
  }
  try {
    return contract.validate(json);
  } catch (cause) {
    if (cause instanceof AiContractError) return null;
    throw cause;
  }
}
