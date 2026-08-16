import { describe, expect, it } from 'vitest';

import { firstName, initials } from '../people.js';

describe('firstName', () => {
  it('takes the first name only — the client-facing default', () => {
    expect(firstName('Naledi Mokoena')).toBe('Naledi');
    expect(firstName('Naledi M.')).toBe('Naledi');
    expect(firstName('Naledi')).toBe('Naledi');
  });

  it('survives untidy input', () => {
    expect(firstName('  Naledi   Mokoena  ')).toBe('Naledi');
    expect(firstName('')).toBe('');
    expect(firstName('   ')).toBe('');
  });
});

describe('initials', () => {
  it('uses the first and last name', () => {
    expect(initials('Naledi Mokoena')).toBe('NM');
    expect(initials('Thabo Kgosi Molefe')).toBe('TM');
  });

  it('handles a single name and blank input', () => {
    expect(initials('Naledi')).toBe('N');
    expect(initials('')).toBe('');
    expect(initials('   ')).toBe('');
  });
});
