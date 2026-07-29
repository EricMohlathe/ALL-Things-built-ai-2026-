/**
 * UUIDv7 (§3.1 convention).
 *
 * v7 puts a 48-bit millisecond timestamp in the high bits, so ids sort
 * chronologically as plain strings. That is worth more than it sounds: session
 * lists, sync ordering and IndexedDB cursors all become correct by default
 * instead of needing a secondary index on `created_at`.
 *
 * Clock and randomness are injectable so tests are deterministic and so a
 * generated id can be replayed exactly.
 */

export interface IdOptions {
  now?: number;
  random?: () => number;
}

/**
 * Prefers the platform CSPRNG. An injected `random` overrides it, because a
 * caller supplying randomness is a test asserting on exact output — and because
 * share tokens must never fall back to `Math.random` silently, `secureOnly`
 * makes the absence of a CSPRNG an error rather than a weak token.
 */
function randomBytes(
  count: number,
  random: (() => number) | undefined,
  secureOnly = false,
): number[] {
  if (!random) {
    const csprng = globalThis.crypto;
    if (csprng?.getRandomValues) {
      return Array.from(csprng.getRandomValues(new Uint8Array(count)));
    }
    if (secureOnly) {
      throw new Error(
        'No cryptographic randomness available — refusing to mint a guessable share token.',
      );
    }
  }
  const source = random ?? (() => Math.random());
  return Array.from({ length: count }, () => Math.floor(source() * 256) & 0xff);
}

export function uuidv7(options: IdOptions = {}): string {
  const now = options.now ?? Date.now();
  const random = options.random;
  const bytes = new Uint8Array(16);

  // 48-bit big-endian timestamp.
  const ms = Math.max(0, Math.floor(now));
  bytes[0] = (ms / 2 ** 40) & 0xff;
  bytes[1] = (ms / 2 ** 32) & 0xff;
  bytes[2] = (ms / 2 ** 24) & 0xff;
  bytes[3] = (ms / 2 ** 16) & 0xff;
  bytes[4] = (ms / 2 ** 8) & 0xff;
  bytes[5] = ms & 0xff;

  const rand = randomBytes(10, random);
  for (let i = 0; i < 10; i += 1) bytes[6 + i] = rand[i]!;

  // Version 7 in the high nibble of byte 6; RFC 4122 variant in byte 8.
  bytes[6] = (bytes[6]! & 0x0f) | 0x70;
  bytes[8] = (bytes[8]! & 0x3f) | 0x80;

  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

const UUID_SHAPE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

export function isUuidv7(value: string): boolean {
  return UUID_SHAPE.test(value);
}

/** Recovers the creation instant encoded in a v7 id. */
export function timestampOf(uuid: string): number {
  const hex = uuid.replace(/-/g, '').slice(0, 12);
  return Number.parseInt(hex, 16);
}

/**
 * 128-bit share token (§3.1 `share_link.token`, and the G10 security gate).
 *
 * Never derived from a coachee id — a client link that can be guessed from a
 * row id is the same as no link at all. Base64url keeps it short enough to sit
 * in a WhatsApp message without wrapping.
 */
export function shareToken(random?: () => number): string {
  const bytes = randomBytes(16, random, true);
  let binary = '';
  for (const b of bytes) binary += String.fromCharCode(b);
  const base64 =
    typeof btoa === 'function'
      ? btoa(binary)
      : Buffer.from(bytes).toString('base64');
  return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
