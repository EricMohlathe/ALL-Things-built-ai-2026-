import { elementsOf } from '@cmw/core';
import { describe, expect, it } from 'vitest';

import {
  AiContractError,
  coherenceContract,
  digestContract,
  prepContract,
  sessionAnalysisContract,
  type AiContract,
  type JsonSchema,
} from '../contracts.js';
import { analysisFixture, coherenceFixture, digestFixture, prepFixture } from './fixtures.js';

/**
 * The parity harness.
 *
 * `contracts.ts` holds two hand-written copies of every shape — the JSON Schema
 * the API constrains generation with, and the validator this package trusts. The
 * risk of two copies is drift, so this table drives the same three checks over
 * all four contracts: the schema is closed, the fixture validates, and dropping
 * any key the schema calls required makes the validator throw.
 */
const CONTRACTS: Array<{
  name: string;
  contract: AiContract<unknown>;
  fixture: () => Record<string, unknown>;
}> = [
  { name: 'session analyzer (GROW)', contract: sessionAnalysisContract('GROW'), fixture: analysisFixture },
  { name: 'coherence checker', contract: coherenceContract(), fixture: coherenceFixture },
  { name: 'weekly digest', contract: digestContract(), fixture: digestFixture },
  { name: 'prep whisperer', contract: prepContract(), fixture: prepFixture },
];

function requiredOf(schema: JsonSchema): string[] {
  return (schema.required as string[] | undefined) ?? [];
}

describe.each(CONTRACTS)('$name', ({ contract, fixture }) => {
  it('closes the object so the model cannot add fields', () => {
    expect(contract.schema.additionalProperties).toBe(false);
    expect(requiredOf(contract.schema).length).toBeGreaterThan(0);
  });

  it('accepts a well-formed response', () => {
    expect(() => contract.validate(fixture())).not.toThrow();
  });

  it('declares every required key in the schema as required by the validator too', () => {
    for (const key of requiredOf(contract.schema)) {
      const partial = fixture();
      delete partial[key];
      expect(() => contract.validate(partial), `missing ${key} should be rejected`).toThrow(
        AiContractError,
      );
    }
  });

  it('rejects anything that is not an object', () => {
    for (const junk of [null, 'text', 42, []]) {
      expect(() => contract.validate(junk)).toThrow(AiContractError);
    }
  });

  it('names the field in the error, not just the failure', () => {
    const partial = fixture();
    const key = requiredOf(contract.schema)[0]!;
    delete partial[key];
    try {
      contract.validate(partial);
      expect.unreachable('should have thrown');
    } catch (error) {
      expect(error).toBeInstanceOf(AiContractError);
      expect((error as AiContractError).path).toContain(key);
    }
  });
});

describe('session analyzer', () => {
  const grow = sessionAnalysisContract('GROW');

  it('constrains the element enum to the framework in play', () => {
    const items = (grow.schema.properties as Record<string, JsonSchema>).elements!.items as JsonSchema;
    const element = (items.properties as Record<string, JsonSchema>).element!;
    expect(element.enum).toEqual(elementsOf('GROW'));

    const great = sessionAnalysisContract('GREAT');
    const greatItems = (great.schema.properties as Record<string, JsonSchema>).elements!.items as JsonSchema;
    expect(((greatItems.properties as Record<string, JsonSchema>).element!).enum).toEqual(
      elementsOf('GREAT'),
    );
  });

  it('rejects an element that belongs to the other framework', () => {
    const wrong = analysisFixture();
    (wrong.elements as Array<Record<string, unknown>>)[0]!.element = 'explore';
    expect(() => grow.validate(wrong)).toThrow(/not a GROW element/);
  });

  it('keeps the ratings and checklist states the domain already knows', () => {
    const parsed = grow.validate(analysisFixture());
    expect(parsed.elements.map((e) => e.rating)).toEqual(['Adequate', 'Strong', 'Weak', 'Met']);
    expect(parsed.checklist).toEqual({
      smarter_met: 'fail',
      low_scores_flagged: 'pass',
      will_step: 'pass',
      review_date_set: 'pass',
    });
  });

  it('rejects a rating outside the rubric', () => {
    const wrong = analysisFixture();
    (wrong.elements as Array<Record<string, unknown>>)[0]!.rating = 'Excellent';
    expect(() => grow.validate(wrong)).toThrow(/expected one of Strong/);
  });

  it('nulls a date the model wrote in prose rather than losing the analysis', () => {
    // "next week" in a date field is not worth discarding a good grading over —
    // she edits every one of these before saving anyway.
    const parsed = grow.validate(analysisFixture());
    expect(parsed.suggested_actions[0]!.due).toBe('2099-03-14');
    expect(parsed.suggested_actions[1]!.due).toBeNull();
    expect(parsed.suggested_actions[1]!.review).toBeNull();
  });

  it('allows empty evidence but not an empty growth tip', () => {
    const thin = analysisFixture();
    (thin.elements as Array<Record<string, unknown>>)[0]!.evidence = '';
    expect(() => grow.validate(thin)).not.toThrow();

    const useless = analysisFixture();
    useless.one_growth_tip = '   ';
    expect(() => grow.validate(useless)).toThrow(AiContractError);
  });

  it('rejects a checklist that is not an object', () => {
    const wrong = analysisFixture();
    wrong.checklist = 'all good';
    expect(() => grow.validate(wrong)).toThrow(AiContractError);
  });

  it('rejects elements that are not a list', () => {
    const wrong = analysisFixture();
    wrong.elements = { goal: 'Strong' };
    expect(() => grow.validate(wrong)).toThrow(AiContractError);
  });

  it('trims what it keeps', () => {
    const padded = analysisFixture();
    padded.one_growth_tip = '  ask for pros and cons  ';
    expect(grow.validate(padded).one_growth_tip).toBe('ask for pros and cons');
  });
});

describe('coherence checker', () => {
  const contract = coherenceContract();

  it('accepts only the three verdicts', () => {
    for (const verdict of ['on', 'drifting', 'off']) {
      expect(contract.validate({ ...coherenceFixture(), verdict }).verdict).toBe(verdict);
    }
    expect(() => contract.validate({ ...coherenceFixture(), verdict: 'maybe' })).toThrow(
      AiContractError,
    );
  });

  it('requires every field to carry text', () => {
    expect(() => contract.validate({ ...coherenceFixture(), one_line_fix: '' })).toThrow(
      AiContractError,
    );
  });
});

describe('weekly digest', () => {
  const contract = digestContract();

  it('drops the blank gap the model padded the array with', () => {
    const parsed = contract.validate(digestFixture());
    expect(parsed.content_gaps).toEqual(['Nothing published under Sustainable energy in 30 days']);
  });

  it('keeps client names as the first names it was given', () => {
    const parsed = contract.validate(digestFixture());
    expect(parsed.clients_needing_attention).toEqual([
      { first_name: 'Thabo', why: 'no session in three weeks' },
    ]);
  });

  it('rejects a client entry with no reason', () => {
    const wrong = digestFixture();
    wrong.clients_needing_attention = [{ first_name: 'Thabo', why: '' }];
    expect(() => contract.validate(wrong)).toThrow(AiContractError);
  });

  it('rejects a non-string inside a string array', () => {
    const wrong = digestFixture();
    wrong.content_gaps = ['fine', 7];
    expect(() => contract.validate(wrong)).toThrow(/content_gaps\[1\]/);
  });
});

describe('prep whisperer', () => {
  const contract = prepContract();

  it('trims the recap to three lines instead of rejecting a fourth', () => {
    const parsed = contract.validate(prepFixture());
    expect(parsed.recap_3_lines).toHaveLength(3);
    expect(parsed.recap_3_lines[0]).toContain('Health sat at 3');
  });

  it('rejects a recap with nothing in it', () => {
    expect(() => contract.validate({ ...prepFixture(), recap_3_lines: ['', '  '] })).toThrow(
      AiContractError,
    );
  });

  it('drops blank watchouts', () => {
    expect(contract.validate(prepFixture()).watchouts).toEqual([
      'The parkrun action has no review date.',
    ]);
  });
});
