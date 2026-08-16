import { CEMENT_SCRIPT, FRAMEWORK_NAMES, buildDeck, coachGrowthCurve, frameworkFor } from '@cmw/core';
import { describe, expect, it } from 'vitest';

import {
  analyzerPrompt,
  coherencePrompt,
  digestPrompt,
  methodologyPrompt,
  prepPrompt,
} from '../prompts.js';
import { promptName, promptNames, scrubNotes } from '../redact.js';
import { action, content, goal, greatSession, naledi, pillar, session, thabo, wheel, TODAY } from './fixtures.js';

describe('the methodology prompt', () => {
  const prompt = methodologyPrompt();

  it('carries every element of both frameworks, with her own questions', () => {
    // This is the claim the whole product rests on: the AI grades against her
    // method. If a question bank stops reaching the prompt, that claim is false
    // and nothing else in the app would notice.
    for (const name of FRAMEWORK_NAMES) {
      const framework = frameworkFor(name);
      expect(prompt).toContain(framework.expansion);
      for (const element of framework.elements) {
        expect(prompt).toContain(element.label);
        expect(prompt).toContain(element.purpose);
        for (const question of element.questions) expect(prompt).toContain(question);
      }
    }
  });

  it('flags the moves she is recorded as skipping', () => {
    const skipped = FRAMEWORK_NAMES.flatMap((name) =>
      frameworkFor(name).elements.filter((e) => e.historically_skipped),
    );
    expect(skipped.length).toBeGreaterThan(0);
    const warnings = prompt.split('⚠').length - 1;
    expect(warnings).toBe(skipped.length);
  });

  it('includes the closing script verbatim', () => {
    for (const line of CEMENT_SCRIPT) expect(prompt).toContain(line);
    expect(prompt).toContain('at or above 8 out of 10');
  });

  it('names the rubric values and the two SMARTER letters she misses', () => {
    for (const rating of ['Strong', 'Adequate', 'Weak', 'Met', 'N/A']) {
      expect(prompt).toContain(`**${rating}**`);
    }
    expect(prompt).toContain('Exciting and Rewarded');
  });

  it('states the guardrails that keep it a wellness tool', () => {
    expect(prompt).toContain('You propose, she disposes');
    expect(prompt).toContain('not medical records');
    expect(prompt).toContain('first name only');
  });

  it('uses her edited wheel domains when she has changed them', () => {
    const custom = methodologyPrompt({ wheelDomains: ['Ubuntu', 'Rest'] });
    expect(custom).toContain('Ubuntu, Rest');
    expect(custom).not.toContain('Physical Environment');
  });

  it('falls back to the defaults for an empty override', () => {
    expect(methodologyPrompt({ wheelDomains: [] })).toContain('Physical Environment');
  });

  it('is byte-identical between calls, so the cache breakpoint actually hits', () => {
    expect(methodologyPrompt()).toBe(prompt);
  });

  it('is long enough to be worth caching', () => {
    // Not an assertion about the API's minimum — below it the API simply declines
    // to cache — but a canary for the prompt silently collapsing to a stub.
    expect(prompt.length).toBeGreaterThan(3000);
  });
});

describe('the analyzer prompt', () => {
  const prompt = analyzerPrompt({
    session,
    coachee: naledi,
    participants: [naledi],
    goals: [goal],
    notes: 'Naledi Mokoena said Health is at a 3. Reach her on naledi@example.com or 082 555 1234.',
    wheel,
    openActions: [action],
  });

  it('names the framework, the elements and the order to grade them in', () => {
    expect(prompt).toContain('GROW — Goal → Reality → Options → Will');
    expect(prompt).toContain('goal, reality, options, will');
  });

  it('passes the closing numbers so the cementing rule can be applied', () => {
    expect(prompt).toContain('Confidence out of 10: 9');
    expect(prompt).toContain('Commitment out of 10: 8');
    expect(prompt).toContain('2099-03-11, 2099-03-14');
  });

  it('names the SMARTER letters the goal has not earned', () => {
    expect(prompt).toContain('not yet named: Exciting, Rewarded');
  });

  it('carries the low wheel domains rather than making the model infer them', () => {
    expect(prompt).toContain('Health 3/10');
    expect(prompt).toContain('Fun & Recreation 4/10');
  });

  it('sends only the first name, and strips contact details from the notes', () => {
    expect(prompt).toContain('**Naledi**');
    expect(prompt).not.toContain('Mokoena');
    expect(prompt).not.toContain('naledi@example.com');
    expect(prompt).not.toContain('082 555 1234');
    expect(prompt).toContain('[contact removed]');
  });

  it('tells the model to grade one person in a joint session', () => {
    const joint = analyzerPrompt({
      session: greatSession,
      coachee: naledi,
      participants: [naledi, thabo],
      goals: [],
      notes: 'Both present.',
    });
    expect(joint).toContain('joint session — grade Naledi only');
    expect(joint).toContain('Naledi, Thabo');
  });

  it('says so plainly when there is nothing on file', () => {
    const bare = analyzerPrompt({
      session,
      coachee: naledi,
      participants: [naledi],
      goals: [],
      notes: '',
    });
    expect(bare).toContain('no wheel snapshot on file');
    expect(bare).toContain('none recorded');
    expect(bare).toContain('(she recorded no notes)');
  });
});

describe('the coherence prompt', () => {
  it('puts the pillar core message beside the piece', () => {
    const prompt = coherencePrompt({ item: content, pillar, recent: [] });
    expect(prompt).toContain('Small daily habits beat heroic resets');
    expect(prompt).toContain('The 5am myth');
    expect(prompt).toContain('Reel on IG');
    expect(prompt).toContain('nothing published yet');
  });

  it('asks which pillar it belongs to when it is filed under none', () => {
    const prompt = coherencePrompt({ item: { ...content, pillar_id: null }, pillar: null, recent: [content] });
    expect(prompt).toContain('filed under no pillar');
    expect(prompt).toContain('"The 5am myth"');
  });

  it('falls back to the title when there is no script yet', () => {
    const prompt = coherencePrompt({ item: { ...content, script: null }, pillar, recent: [] });
    expect(prompt).toContain('no script written yet');
  });
});

describe('the digest prompt', () => {
  const deck = buildDeck({
    coachees: [naledi, thabo],
    sessions: [session],
    actions: [{ ...action, review_date: '2099-03-01' }],
    content: [content],
    now: TODAY,
    hour: 7,
  });

  it('reports the week in figures the tip can be drawn from', () => {
    const growth = coachGrowthCurve([session], [], 'GROW');
    const prompt = digestPrompt({
      deck,
      coachees: [naledi, thabo],
      growth,
      starvedPillars: ['Sustainable energy'],
      publishedThisWeek: 0,
      weekOf: '2099-03-09',
    });
    expect(prompt).toContain('Rollup for the week of 2099-03-09');
    expect(prompt).toContain('Slipped past their date: 1');
    expect(prompt).toContain('Sustainable energy');
    // No graded cycles in this fixture, so it must say so rather than invent one.
    expect(prompt).toContain('not enough graded sessions yet');
  });

  it('uses first names only, and never a coachee id', () => {
    const prompt = digestPrompt({ deck, coachees: [naledi, thabo], weekOf: '2099-03-09' });
    expect(prompt).not.toContain('c-naledi');
    expect(prompt).not.toContain('Mokoena');
    expect(prompt).toMatch(/Naledi|none flagged/);
  });
});

describe('the prep prompt', () => {
  it('brings the last session, the open actions and her own question bank', () => {
    const prompt = prepPrompt({
      coachee: naledi,
      framework: 'GROW',
      lastSession: session,
      openActions: [action],
      wheel,
      goals: [goal],
      today: TODAY,
    });
    expect(prompt).toContain('about to run a GROW session with **Naledi**');
    expect(prompt).toContain('2 days ago');
    expect(prompt).toContain('Book the Saturday parkrun');
    expect(prompt).toContain('Health 3/10');
    expect(prompt).toContain('What would you like to take out of this session?');
    // Her own summary mentions the full name; the prompt must not.
    expect(prompt).not.toContain('Mokoena');
  });

  it('names the biggest gap to target', () => {
    const prompt = prepPrompt({ coachee: naledi, framework: 'GROW', wheel, today: TODAY });
    expect(prompt).toContain('Health (3 → 8)');
  });

  it('handles a first session without pretending there is history', () => {
    const prompt = prepPrompt({ coachee: thabo, framework: 'GREAT', today: TODAY });
    expect(prompt).toContain('this is a first session');
    expect(prompt).toContain('none outstanding');
    expect(prompt).toContain('no wheel snapshot on file');
  });
});

describe('redaction', () => {
  it('replaces a full name with a first name and leaves single names alone', () => {
    expect(promptName(naledi)).toBe('Naledi');
    expect(promptName({ ...naledi, name: 'Naledi' })).toBe('Naledi');
  });

  it('matches the longest name first so no surname survives the pass', () => {
    const scrubbed = scrubNotes('Naledi Mokoena and Naledi met.', [
      { ...naledi, name: 'Naledi' },
      naledi,
    ]);
    expect(scrubbed).toBe('Naledi and Naledi met.');
  });

  it('strips emails and phone numbers, keeping the coaching content', () => {
    const scrubbed = scrubNotes('Call +27 82 555 1234 or mail her@x.co. She lost 8kg.', []);
    expect(scrubbed).toContain('[contact removed]');
    expect(scrubbed).toContain('She lost 8kg.');
    expect(scrubbed).not.toContain('555');
  });

  it('leaves short digit runs alone — a weight is not a phone number', () => {
    expect(scrubNotes('Slept 7 hours, walked 4200 steps.', [])).toBe(
      'Slept 7 hours, walked 4200 steps.',
    );
  });

  it('adds an initial only when two coachees share a first name', () => {
    const map = promptNames([naledi, thabo]);
    expect(map.get(naledi.id)).toBe('Naledi');

    const twin = { ...thabo, id: 'c-twin', name: 'Naledi Sithole' };
    const disambiguated = promptNames([naledi, twin]);
    expect(disambiguated.get(naledi.id)).toBe('Naledi M.');
    expect(disambiguated.get(twin.id)).toBe('Naledi S.');
  });

  it('falls back to the bare first name when there is no initial to add', () => {
    const a = { ...naledi, id: 'a', name: 'Naledi' };
    const b = { ...naledi, id: 'b', name: 'Naledi' };
    const map = promptNames([a, b]);
    expect(map.get('a')).toBe('Naledi');
    expect(map.get('b')).toBe('Naledi');
  });
});
