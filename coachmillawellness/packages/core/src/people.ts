/**
 * Name handling.
 *
 * Small, but it carries a privacy obligation: M8 progress links default to
 * first-name-only, and POPIA (§13) makes that default a real commitment rather
 * than a nicety. Keeping the rule in one tested place means a client-facing
 * surface cannot accidentally leak a surname by formatting a name itself.
 */

/** First name only — the default identity on any client-facing surface. */
export function firstName(fullName: string): string {
  const trimmed = fullName.trim();
  if (trimmed === '') return '';
  return trimmed.split(/\s+/)[0]!;
}

/** Up to two initials, for avatar fallbacks. */
export function initials(fullName: string): string {
  const parts = fullName.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '';
  const letters = [parts[0]!, parts.length > 1 ? parts[parts.length - 1]! : '']
    .filter(Boolean)
    .map((p) => p[0]!.toUpperCase());
  return letters.join('');
}
