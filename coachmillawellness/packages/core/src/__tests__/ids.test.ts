import { describe, expect, it, vi } from 'vitest';

import { isUuidv7, shareToken, timestampOf, uuidv7 } from '../ids.js';

describe('uuidv7', () => {
  it('produces a well-formed v7 id', () => {
    const id = uuidv7();
    expect(isUuidv7(id)).toBe(true);
    expect(id).toHaveLength(36);
  });

  it('encodes the creation instant so it can be read back', () => {
    const now = Date.parse('2026-07-30T12:00:00.000Z');
    expect(timestampOf(uuidv7({ now }))).toBe(now);
  });

  it('sorts chronologically as a plain string', () => {
    // The reason for choosing v7: `ORDER BY id` is already `ORDER BY created_at`.
    const early = uuidv7({ now: Date.parse('2026-01-01T00:00:00.000Z') });
    const late = uuidv7({ now: Date.parse('2026-12-31T00:00:00.000Z') });
    expect([late, early].sort()).toEqual([early, late]);
  });

  it('is deterministic when both clock and randomness are supplied', () => {
    const options = { now: 1_700_000_000_000, random: () => 0.5 };
    expect(uuidv7(options)).toBe(uuidv7(options));
  });

  it('is unique across a tight loop on a single millisecond', () => {
    const ids = new Set(Array.from({ length: 500 }, () => uuidv7({ now: 1_700_000_000_000 })));
    expect(ids.size).toBe(500);
  });

  it('clamps a negative or fractional clock rather than emitting a malformed id', () => {
    expect(isUuidv7(uuidv7({ now: -5 }))).toBe(true);
    expect(isUuidv7(uuidv7({ now: 1.9 }))).toBe(true);
  });

  it('still generates ids where no CSPRNG exists', () => {
    // Unlike a share token, an id only needs to be unique, not unguessable —
    // so this degrades to Math.random rather than refusing to work.
    const original = globalThis.crypto;
    try {
      Reflect.deleteProperty(globalThis, 'crypto');
      expect(isUuidv7(uuidv7())).toBe(true);
    } finally {
      Object.defineProperty(globalThis, 'crypto', {
        value: original,
        configurable: true,
        writable: true,
      });
    }
  });

  it('rejects things that are not v7 ids', () => {
    expect(isUuidv7('not-a-uuid')).toBe(false);
    // A valid v4 uuid — right shape, wrong version.
    expect(isUuidv7('9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d')).toBe(false);
  });
});

describe('shareToken', () => {
  it('mints a 128-bit url-safe token', () => {
    const token = shareToken();
    // 16 bytes of base64url, padding stripped.
    expect(token).toHaveLength(22);
    expect(token).toMatch(/^[A-Za-z0-9_-]+$/);
  });

  it('does not repeat', () => {
    const tokens = new Set(Array.from({ length: 500 }, () => shareToken()));
    expect(tokens.size).toBe(500);
  });

  it('refuses to mint a token without cryptographic randomness', () => {
    // Gate G10 requires unguessable tokens. Falling back to Math.random here
    // would produce a link that looks fine and protects nobody, so this throws
    // instead — a loud failure beats a quiet one when client data is behind it.
    const original = globalThis.crypto;
    try {
      Reflect.deleteProperty(globalThis, 'crypto');
      expect(() => shareToken()).toThrow(/cryptographic randomness/i);
    } finally {
      Object.defineProperty(globalThis, 'crypto', {
        value: original,
        configurable: true,
        writable: true,
      });
    }
  });

  it('still honours injected randomness for reproducible tests', () => {
    expect(shareToken(() => 0.25)).toBe(shareToken(() => 0.25));
  });

  it('falls back to Buffer where btoa is unavailable', () => {
    const original = globalThis.btoa;
    try {
      Reflect.deleteProperty(globalThis, 'btoa');
      expect(shareToken(() => 0.5)).toMatch(/^[A-Za-z0-9_-]{22}$/);
    } finally {
      Object.defineProperty(globalThis, 'btoa', {
        value: original,
        configurable: true,
        writable: true,
      });
    }
  });

  it('uses the platform CSPRNG when no randomness is injected', () => {
    const spy = vi.spyOn(globalThis.crypto, 'getRandomValues');
    shareToken();
    expect(spy).toHaveBeenCalled();
    spy.mockRestore();
  });
});
