# Store preparation — prompt P9

Written ahead of the apps on purpose. §8.3 names one dependency that no amount of
good engineering shortens:

> **A new personal Google Play account must run a closed test with 12–20 testers
> for 14 continuous days before production access.**

That clock is the critical path to launch. It costs $25 and can start the day the
account exists — long before there is an app worth testing. Everything else in
this document exists so that when the builds are ready, nothing is waiting on a
form.

**Do these two things now, in this order:**

1. **Open the Play Console account** ($25, once). The 14-day clock cannot start
   before it exists, and identity verification alone can take days.
2. **Start the tester list.** 12 people who will actually opt in. Family, her
   circles, two or three coachees who already know about the app. Write the names
   down; "I'll find people later" is how this slips a fortnight.

Apple's account ($99/yr) is less urgent — no waiting period — but it also covers
macOS notarization in P8, so opening it with the other is tidier.

---

## What the app actually collects

Every answer below derives from §3.1 and the code as built, not from what sounds
safest. If a future change makes one of these untrue, the form answer changes
with it.

| Question | Answer | Why |
|---|---|---|
| Does it collect personal information? | Yes — names, contact details and notes the coach types about her clients | `coachee.name`, `coachee.contact`, `coachee.notes`, session summaries |
| Does the app collect data about the *user*? | Her practice data only. No profile, no demographics, no advertising ID | There is no account in Build 1 |
| Is data shared with third parties? | Only if she switches the Copilot on, and only then to Anthropic for processing | §9; off by default, and the app is complete without it |
| Is data sold? | No | And never will be — there is no business model that wants it |
| Is data used for advertising or tracking? | No. No analytics SDK, no attribution, no ad identifier | Deliberate; the single HTML file makes zero network requests |
| Is data encrypted in transit? | Yes — HTTPS for every network call the app makes | Build 1 makes none at all unless the Copilot is used |
| Can a user request deletion? | Yes, in-app | M7: remove a coachee, or clear everything |
| Is there account creation? | No in Build 1. Magic-link email in the hosted web app (P3) | |
| Health data? | **No.** Wellness coaching notes, not medical records | §13 — this line matters, see below |

### The health-claims line

State it plainly in both listings and never blur it:

> CoachMillaWellness is a practice-management tool for a professional coach. It
> is not a medical device, it does not diagnose, and it does not provide medical
> advice.

This is not marketing caution. Health-adjacent apps attract a slower, stricter
review, and every claim that edges toward treatment invites it. The Copilot's own
system prompt carries the same instruction — it is told not to diagnose and to
suggest a referral if notes describe something clinical — so the product and the
listing say the same thing.

---

## Apple App Store

### Guideline 4.2 — Minimum Functionality

The real risk. Apps that read as a wrapped website get rejected, and this one
*is* a web UI in a native shell. §8.2's answer is that it does not merely look
native, it uses native capabilities that a website cannot:

- **Offline-first.** SQLite on device; the whole app works in aeroplane mode.
- **Push notifications.** The Nudge Engine — review dates, pre-session prep at
  T-2h, streak milestones, Pulse received — with per-category toggles and quiet
  hours.
- **Native share sheet.** Share Kit renders wheel PNGs and recap cards to
  WhatsApp-perfect sizes and hands them to the OS share sheet.
- **Haptics** on wheel interactions.
- **Universal Links**, so every `coachmillawellness.com` link opens in-app.

**Ship all of these in the first TestFlight build.** They are not polish to add
after approval; they are the argument for approval.

### Appeal letter, drafted in advance

Keep this ready rather than writing it under time pressure after a rejection:

> CoachMillaWellness is not a wrapper around a website. It stores a coach's
> entire practice locally in SQLite and is fully functional with no network
> connection. It schedules and delivers local notifications for client review
> dates, renders share cards through the native share sheet, and uses haptics for
> the wheel-scoring interaction. The web version exists for the coach's clients,
> who receive read-only progress links; the app is the practitioner's tool and
> has capabilities the web version does not and cannot have.

### Required assets

- Privacy policy URL (must be live before submission — it goes up with P3)
- Privacy nutrition label — answers from the table above
- Screenshots at 6.7" and 5.5"
- Icon set
- Support URL

## Google Play

### The closed test

- 12–20 testers, **14 continuous days**. A tester who opts out mid-way breaks
  continuity — recruit 15+ for a 12-person floor.
- Testers must join via the opt-in link and keep the app installed.
- Start it on **day 1 of P4**, not when the app feels finished. A rough build
  under test beats a polished build waiting to start the clock.

### Required assets

- Privacy policy URL
- Data Safety form — answers from the table above
- Feature graphic 1024×500
- Phone screenshots
- Short description (80 chars) and full description

---

## Listing copy

Written as she would say it, and kept honest — no "transform your life", no
outcome claims, nothing that invites a health review.

### Short description (80 characters)

> The coaching practice tool that grades the coach, not just the client.

### Full description

> CoachMillaWellness is a practice tool for professional health and life coaches.
>
> **Run your sessions on your own methodology.** GROW and GREAT frameworks with
> your own question banks, scored element by element — so the steps you tend to
> skip become visible instead of staying a hunch. Your adherence charts month by
> month.
>
> **A Wheel of Life that moves.** Ten domains, scored by dragging or by keyboard,
> with a timeline you can scrub between sessions to see the shape of a year.
> Export it as an image and send it to your client.
>
> **See whether what you post matches what you stand for.** Message pillars
> against your published work, with the pillars you have been neglecting named in
> words.
>
> **Your data is yours.** Everything works offline. Export the whole practice as
> one file whenever you like, and take it with you if you ever stop using this.
>
> **AI, only if you want it.** Bring your own API key and the Copilot will grade a
> session from your notes against your own frameworks, check a script against your
> message pillars, and write you a Monday brief — every suggestion editable before
> anything is saved. Leave the key out and everything above still works.
>
> CoachMillaWellness is a practice-management tool for a professional coach. It is
> not a medical device, it does not diagnose, and it does not provide medical
> advice.

### Keywords

coaching, life coach, wellness coach, GROW model, wheel of life, coaching
practice, client tracker, session notes, coaching business, health coach

---

## Screenshot script

Five screens, in this order. Shot on the sample practice so no real client
appears, in Dawn unless the store's own background makes Morning read better.

1. **Command Deck** — the focus line and today's sessions. First impression is
   "this answers a question", not "this is a database".
2. **The Living Wheel** mid-morph, with the timeline scrubber visible. The one
   screenshot that sells the product.
3. **Session scorecard** — the framework stepper with an *often skipped* flag
   visible and the closing script open. This is the differentiator no competitor
   shows.
4. **Coherence map** — pillars against published work, with a starved pillar
   named.
5. **Insights** — the Coach Growth Curve with the thinnest element called out.

Caption each one with a plain sentence, not a feature name.

`apps/single/e2e/` already drives every one of these screens under
`reducedMotion: 'reduce'`; the capture script should reuse those navigation
helpers rather than re-deriving selectors that will drift.

---

## Submission checklist

Ordered by what blocks what.

- [ ] Play Console account open ($25) — **do first, the clock depends on it**
- [ ] 15+ testers named and contacted
- [ ] Apple Developer Program enrolled ($99/yr) — also covers P8 notarization
- [ ] Privacy policy and terms live on the domain (P3)
- [ ] Closed test running, day 1 of P4
- [ ] Native capabilities in the first TestFlight build (§8.2 — the 4.2 defence)
- [ ] Data Safety form submitted, answers matching the table above
- [ ] Privacy nutrition label submitted, same answers
- [ ] Screenshots captured for 6.7", 5.5", and Play phone sizes
- [ ] Feature graphic 1024×500
- [ ] Health-claims line present in both listings
- [ ] 14 continuous days of closed testing complete
- [ ] Budget one to two weeks for a rejection cycle before any launch date is
      promised to anyone

---

## Costs to reach launch

From §10, at roughly R19/$ — verify the rate at purchase.

| Item | Cost | When |
|---|---|---|
| Google Play Console | $25 once ≈ R475 | **Now** — gates the 14-day test |
| Apple Developer Program | $99/yr ≈ R1,880 | P4 (also covers desktop notarization) |
| Domain | ~R190/yr (.com) | P3 |
| Vercel + Supabase | R0 on free tiers | P3+ |
| Claude API | ~R100–300/mo at her usage | Only if she switches the Copilot on |

**Cash to reach store launch: ≈ R2,500–3,500.** Phases 1 and 2 cost nothing —
they are a file.
