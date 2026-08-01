/**
 * Data minimisation before a prompt leaves the device (§13, POPIA).
 *
 * Be clear about what this is: **minimisation, not anonymisation.** Wellness
 * notes describing a named person's marriage and health are personal
 * information whatever we do to the salutation, and the lawful basis for sending
 * them to a processor is her client's consent — not a regex. What this module
 * does is remove the identifiers that serve no purpose in the prompt: a surname
 * the model does not need in order to grade a GROW cycle, and a phone number
 * that was only ever in the notes because that is where she had a pen.
 *
 * The rule this encodes: the AI is told everything it needs to do the coaching
 * work and nothing it needs to identify a stranger.
 */

import { firstName, type Coachee } from '@cmw/core';

/** Where an identifier was, so the model knows something was removed. */
const CONTACT_PLACEHOLDER = '[contact removed]';

const EMAIL = /[\w.+-]+@[\w-]+\.[\w.-]+/g;

/**
 * Seven or more digits, allowing the spaces, dashes, brackets and `+` that South
 * African numbers are written with. Seven is the floor because six-digit runs are
 * more often a weight in grams or a rand figure than a phone number, and
 * scrubbing "I lost 8kg since 060821" would corrupt the coaching content the
 * prompt exists to carry.
 */
const PHONE = /(?:\+?\d[\d\s()-]{5,}\d)/g;

/**
 * Replaces each coachee's full name with their first name, and strips contact
 * details.
 *
 * Longest name first: "Naledi Mokoena" has to be matched before "Naledi", or the
 * first pass leaves a bare surname behind.
 */
export function scrubNotes(text: string, coachees: readonly Coachee[]): string {
  let out = text;

  const names = coachees
    .map((c) => c.name.trim())
    .filter((name) => name.length > 0)
    .sort((a, b) => b.length - a.length);

  for (const name of names) {
    const short = firstName(name);
    if (short === name) continue;
    out = out.split(name).join(short);
  }

  return out.replace(EMAIL, CONTACT_PLACEHOLDER).replace(PHONE, CONTACT_PLACEHOLDER);
}

/**
 * What the prompt calls a coachee.
 *
 * `firstName` is the same helper the client-facing Progress Links use, so the
 * privacy default is one function rather than a convention each surface
 * remembers separately.
 */
export function promptName(coachee: Coachee): string {
  return firstName(coachee.name);
}

/**
 * Disambiguates when two coachees share a first name.
 *
 * "Thabo" and "Thabo" in one digest is worse than useless — she cannot tell whose
 * review slipped. A trailing initial is the smallest thing that fixes it, and it
 * is still not a surname.
 */
export function promptNames(coachees: readonly Coachee[]): Map<string, string> {
  const counts = new Map<string, number>();
  for (const c of coachees) {
    const short = promptName(c);
    counts.set(short, (counts.get(short) ?? 0) + 1);
  }

  const out = new Map<string, string>();
  for (const c of coachees) {
    const short = promptName(c);
    if ((counts.get(short) ?? 0) === 1) {
      out.set(c.id, short);
      continue;
    }
    const rest = c.name.trim().slice(short.length).trim();
    const initial = rest.replace(/[^A-Za-z]/g, '').charAt(0).toUpperCase();
    out.set(c.id, initial ? `${short} ${initial}.` : short);
  }
  return out;
}
