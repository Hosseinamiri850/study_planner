# 02 — Design Interview

_Questions asked of the product owner before any direction is set. Answers recorded verbatim/paraphrased; decisions flow into `03-design-direction.md`._

## Round 1 — identity & mood (asked first, blocking)

**Q1. Product personality — when a student opens this app, what should they feel?**
- (a) Calm focus — quiet, disciplined, "library" mood. Muted colors, generous whitespace, few elements.
- (b) Energy & momentum — progress is exciting. Warm accent, bold numerals, animated feedback.
- (c) Serious tool — precise, dense, professional. Grids, data-first, minimal decoration.
- (d) Friendly study buddy — soft shapes, encouraging copy, approachable.

**Q2. Overall visual mood family (pick closest 2):**
- (a) Swiss/editorial — strong type, rules and grids, black on paper.
- (b) Soft neumorphic-lite — gentle shadows, rounded, tactile.
- (c) Technical/linear — borders, mono details, terminal-ish accents.
- (d) Warm paper — cream/ink, serif touches, analog feel.

**Q3. Density:**
- (a) Airy — few items per screen, big targets.
- (b) Balanced — moderate, adaptive.
- (c) Dense — power-user, more data per screen.

**Q4. Color philosophy:**
- (a) One disciplined accent on near-neutral base (chosen after interview).
- (b) Multi-hue functional color (each course/status gets a hue).
- (c) Monochrome + single state color.

**Q5. Typography appetite:**
- (a) Characterful display face for numbers/headers + clean Persian body (Vazirmatn-like).
- (b) One super-family doing everything (safe, coherent).
- (c) Bold/oversized type as the main visual device.

## Round 2 — structure & motion (asked after Round 1)

**Q6. Navigation style:**
- (a) Keep top bar, strengthen it.
- (b) Side rail (desktop) + top bar (mobile).
- (c) Command-palette-first, minimal chrome.

**Q7. Animation level:**
- (a) Functional only (200ms fades).
- (b) Purposeful accents — timer pulse, progress fills, view transitions.
- (c) Expressive — springs, micro-celebrations on completion.

**Q8. The running study timer is the product's hero moment. How loud should it be?**
- (a) Ambient — small persistent chip.
- (b) Prominent — dedicated docked module with live seconds.
- (c) Cinematic — full focus mode.

**Q9. Layout philosophy (desktop dashboard):**
- (a) Single column, linear story.
- (b) Asymmetric: primary workspace + secondary stats column.
- (c) Grid-of-equal-panels (current state — not recommended).

**Q10. Mobile experience priority:**
- (a) Equal-first — SPA mobile deserves full design effort.
- (b) Desktop-first, mobile functional.
- (c) Mobile-first — most students track from phone.

## Round 3 — expressiveness details (after direction doc draft)

**Q11. Iconography:** (a) outline minimal (lucide default), (b) rounded/filled friendly, (c) custom sparse — icons only where essential.

**Q12. Rounded vs angular:** corner radius vocabulary — (a) sharp 2–4px, (b) mixed: large surfaces 12–16px / controls 8px, (c) minimal radius 0–6px everything.

**Q13. Language of the empty/first-run experience:** (a) instructive checklist, (b) single CTA, (c) illustrative + story.

---

## Answers

### Round 1 — identity & mood

- **Q1 Personality:** Calm focus. Quiet, disciplined, muted colors, generous whitespace, few elements.
- **Q2 Mood family:** Swiss/editorial (single pick). Strong typography, visible grids/rules, black-on-paper discipline.
- **Q3 Density:** _not asked in Round 1 UI; implied calm→airy-balanced. Resolved by Q9 answer (asymmetric two-zone = balanced, not dense)._
- **Q4 Color:** One disciplined accent on a custom neutral ramp.
- **Q5 Typography:** Display + body. Persian body (Vazirmatn-class) + distinctive display face for numerals/stats/timer.

### Round 2 — structure & motion

- **Q6 Navigation:** Stronger top bar (keep top bar, strengthen it).
- **Q7 Animation:** Purposeful accents — progress fill, timer treatment, subtle view transitions.
- **Q8 Timer:** Prominent docked module with live tabular-numeral seconds.
- **Q9 Desktop layout:** Asymmetric two-zone — primary workspace (timer + tasks) + secondary context column (stats, chart, course progress).
- **Q10 Mobile:** Equal-first — verified at 375px every phase.

### Round 3 — expressiveness

- **Q11 Icons:** Lucide outline, 1.75 stroke.
- **Q12 Radius:** Mixed vocabulary — surfaces 12–16px, controls 8px, pills only for status.
- **Q13 First-run:** Single CTA + suggested course.
