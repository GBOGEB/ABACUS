# QPS Cryoplant MTBF & System Design — Presenter Narrative & Engineering Handover

**Deck:** `QPS_MTBF_WCS_DMAIC_v4.pptx` (38 slides) · **Phase:** 4 (GBO style pass) · **Author of this note:** Claude, from the DMAIC-restructured deck and GBO's own review edits

This document does two jobs at once, per your request:

1. **Presenter notes** — what to *say* on each slide, and how one slide's number hands off to the next (so the talk track survives you skipping around live).
2. **Engineering handover** — for someone who has to *build, improve, or extend* this system later: what decision each slide locks in, what's still open, and where the DMAIC cycle picks back up if new data arrives.

Read this alongside `content.yaml` (raw text, no styling) and `style.yaml` (the design rules this pass enforced). Speaker notes were not duplicated into the .pptx notes pane — this document *is* the notes, kept as one navigable file rather than 38 fragments you'd have to click through in Presenter View.

---

## How the deck is organized

The DMAIC roadmap slides (2, 3, 4) are the deck's own table of contents — use them as your live outline. The five DMAIC phases are **not** presented as five contiguous blocks; they interleave by subject instead (e.g. DEFINE content on Slide 13 sits between two MEASURE-tagged runs). That's a deliberate reader-friendly ordering, not a build error — flag it at the top of your talk so the audience doesn't expect strict phase blocks.

| Phase | Slides | What it settles |
|---|---|---|
| DEFINE | 5–7, 13–15, 19–21 | Scope, RTM obligations, operating-state hierarchy, failure-class definitions |
| MEASURE | 8–12, 16–18 | OEM flow data, N−1 sizing, acceptance testing, unit economics |
| ANALYZE | 22–28 | The Poisson/Weibull math core — where every probability in the deck comes from |
| IMPROVE | 29–34 | Why MTBF matters, where it stops being trustworthy, component-level proof |
| CONTROL | 35–38 | The maintenance policy that follows from IMPROVE's findings |

---

## Slide 1 — Title

**Say:** State the three-part scope up front — MTBF policy, flow assumptions, acceptance/CIS-MCS integration — so the audience knows this is a compliance-and-engineering compendium, not a pitch deck.
**Handover:** No decision content here; it's the index card for the whole document.

## Slide 2 — DMAIC Roadmap (1/3): Define & Measure

**Say:** Walk the room through what DEFINE and MEASURE each answer, then land on the sample calc — 3×112.5 g/s at 72 Hz clears the 307 g/s target with 30 g/s to spare. That number is the thread that runs through Slides 5–11.
**Handover:** This is the map, not the territory — if scope changes later (new flow target, new fleet size), this slide's stat tiles are the first four numbers to revisit.

## Slide 3 — DMAIC Roadmap (2/3): Analyze

**Say:** Set up the two sample calcs (Poisson → ~95% campaign success; Weibull → 235× age-related risk increase) as previews of Slides 22–28's full derivations. This is the slide to slow down on if the audience is skeptical of "MTBF" as a concept.
**Handover:** The 94–95% ceiling and the β>1 aging warning are the two facts every later ANALYZE/IMPROVE slide assumes the audience already has. Don't skip this one live.

## Slide 4 — DMAIC Roadmap (3/3): Improve & Control

**Say:** Frame IMPROVE/CONTROL as the payoff — "everything up to now was diagnosis; this is the treatment." Preview the four-step governance loop (measure exposure → track age vs. η → replace before wear-out → reset & feed back) since it's literally the deck's closing slide too (38), so the audience recognizes it when it comes back around.
**Handover:** This four-step loop is the actual deliverable of the whole compendium — if you only get to present one slide's worth of "so what," make it this one plus Slide 38.

## Slide 5 — Objectives & Scope

**Say:** Anchor the whole deck on 307 g/s @ 24 QM as the operative target (not 320–350 g/s, which is the design envelope, not the requirement).
**Handover:** "SCOPE IN ONE LINE" is intentionally the shortest, most quotable sentence in the deck — use it as your one-sentence recovery if you get derailed by a tangent question.

## Slide 6 — Configuration Baseline (Option A – 4× HSD Combi)

**Say:** State the fleet's physical envelope (1.4 MW, 14 bar, 10–15K cooling ΔT) as inputs, not outputs — they feed Slide 10's cost model and Slide 15's utilities diagram.
**Handover — open item:** The highlighted line ("pressure-constant vs. pressure-swing control — not yet decided") is a genuinely open decision, not a review artifact — flag it explicitly if a stakeholder asks "is this final?" It is the one architectural fork left unresolved in this compendium.

## Slide 7 — Frequency and Upset Policy

**Say:** Three tiers — nominal ≤65 Hz, transient upset ≤72 Hz for ≤8h, cumulative >72 Hz capped — this policy is what makes Slide 9's N−1 margin *usable*, not just theoretical.
**Handover:** Any future compressor selection needs to be checked against this frequency ceiling before it's checked against flow — a unit that clears flow at 80 Hz doesn't help if it can't legally run there.

## Slide 8 — Compressor Flow Capability

**Say:** FSD 575 gives the largest per-unit margin of the three candidates — this is the slide where that becomes visible, and Slide 9 is where it becomes decisive.
**Handover:** OEM reference figures — if a vendor revises a datasheet, this is the one slide to update, and Slides 9/11/17 (all of which depend on these numbers) need re-checking after.

## Slide 9 — Total Flow and N−1 Snapshots

**Say:** This is the sizing decision, stated plainly: FSD 575 clears the N−1 case outright; FSD 475 falls ~19 g/s short. Say it exactly that bluntly — it's the deck's central engineering conclusion.
**Handover:** If a future revision considers FSD 475 anyway (cost pressure, availability), Slide 18's liquid-buffer coverage-time analysis is the mitigation path to bring back into the conversation.

## Slide 10 — Unit Economics — Single HP Compressor

**Say:** Flag this slide explicitly as new work, not baseline — "isothermal compression as the thermodynamic best case," and the headline finding: the 50%-isothermal model reproduces the deck's own 350 kW nameplate to within 2%.
**Handover:** The suction-pressure assumption (1.1 bar) is flagged in-slide as an assumption, not a measurement — if real commissioning data becomes available, this is the number to replace first.

## Slide 11 — 3-Only Envelope (Service / MTTR)

**Say:** Reframe Slide 9's question for the "one unit is down for service" case specifically — FSD 575 still clears 307 g/s at 72 Hz; FSD 475 doesn't, and gets marginal even at reduced frequency.
**Handover:** This is the slide that answers "what happens during scheduled maintenance," which is a different question from N−1-due-to-failure (Slide 9) even though the math looks similar — don't conflate them when presenting.

## Slide 12 — Acceptance & Test System

**Say:** Four gated checks, each must pass before the next is credited — walk them in order (72 Hz stress → 3-only envelope → CIS/MCS exchange → recovery).
**Handover — pre-existing note:** Step 3's body text contains a stray "¨{RTM-0237–0252 pass}" artifact — a leftover edit-marker, not meaningful content. Worth a quick cleanup pass before this deck goes to a wider audience, but it was left untouched here since it's your own content edit, not a styling issue.

## Slide 13 — Reliability Targets and RAMI

**Say:** MTBF targets scale with failure consequence — Class A/B/C, formally defined two slides later on 19 (this is a forward reference, said naturally: "we'll define exactly what Class A/B/C mean shortly").
**Handover:** The 40,000–80,000h overhaul planning assumption for rotary screw compressors is a planning figure, not a guarantee — Appendix G (Slide 26) has the sourced MTBF/MTTR data if anyone wants the primary numbers.

## Slide 14 — CIS Autonomy & MCS Exchange

**Say:** This is a contractual-obligation slide (RTM 0237–0252, Addendum II verbatim) — read the "Applicant shall" language precisely if presenting to a compliance audience.
**Handover:** The three-way diagram (QPLANT compressors ↔ CIS ↔ MCS) is what makes Slide 13's dossier and the whole CONTROL-section governance loop possible in practice — no live data link, no governance loop. Say this connection out loud; it's easy for an audience to miss why a data-integration slide matters to a reliability story.

## Slide 15 — Utilities & Interfaces

**Say:** Four utility interfaces (electrical, cooling water, process headers, future QDB/WPS tie-ins) constrain everything in Slides 8–18 — this is the "how the compressor fleet actually plugs into the rest of the facility" slide.
**Handover — pre-existing note:** There's a duplicated sentence and a garbled word ("INTERCONNECGà") in the process-headers box, left over from your own relabeling pass. Worth fixing before a formal issue of this deck; not touched here since it's content, not style.

## Slide 16 — Appendix A: Canonical Scenarios

**Say:** Five canonical WCS HP-flow scenarios cross-checked against Addendum II — 24 QM Operation (307 g/s) is the real target used throughout; the others (30 QM, etc.) are reference points, not operating targets.
**Handover:** If Addendum II is revised, this is the first slide to re-cross-check — everything upstream in the MEASURE section assumes these scenario numbers are current.

## Slide 17 — Appendix B: N−1 Hz Requirement

**Say:** Same N−1 question as Slides 9/11, now in frequency terms — FSD 575 needs only ~65–66 Hz, comfortably inside the 72 Hz ceiling from Slide 7.
**Handover:** This is the slide that proves the N−1 case isn't just flow-feasible but frequency-legal under the Slide 7 policy — useful if a reviewer asks "sure it flows enough, but is it allowed to run that hard."

## Slide 18 — Appendix C: Liquid Buffer Coverage

**Say:** The 5 m³ buffer converts a flow shortfall into a bounded repair window — ~12h coverage at ¾ nominal flow (the FSD 475 N−1 case). This is the fallback story if a lower-margin compressor type is ever chosen.
**Handover:** Coverage-time-vs-flow-shortfall is the general relationship here; if the buffer size or the shortfall scenario changes, this is a straightforward re-derivation, not a rebuild.

## Slide 19 — Failure Classification

**Say:** This defines Class A/B/C precisely — the classification promised back on Slide 13. State it as the formal definition moment.
**Handover:** Everything downstream that says "Class A target," including Appendix F's SAE-frequency derivation (Slide 25), inherits its definition from this slide. If the classification scheme changes, this is ground zero for the ripple.

## Slide 20 — Reliability Targets by Failure Class

**Say:** Restates the MTBF targets per failure class, now that the classes themselves are defined. This is the "so what does Class A actually require in years" slide.
**Handover — pre-existing note:** Minor inconsistent bullet indentation between two adjacent paragraphs — cosmetic only, left untouched as a content-layer issue rather than a style-pass fix.

## Slide 21 — Operational Philosophy: Cold ≠ Off

**Say:** Walk the five-state chevron (2K-OP → 2K-SB → 4.5K-SB → TS-SB → WS) left to right — "every step right of nominal is a deliberate, monitored trade-down, not a failure, until Warm Stop." This is a genuinely useful mental model to state explicitly; the audience will still be thinking in "on/off" terms otherwise.
**Handover:** This five-state hierarchy is the backbone Appendix E's maintenance matrix (Slide 24) is built on — introduce it clearly here and Slide 24 becomes a simple lookup table instead of a new concept.

## Slide 22 — Appendix D (1/2): Poisson Reliability Model

**Say:** This is the math core — P(N=0) = e^(−λt), with t in years and λ = 1/MTBF. Three windows plotted (90-day, 1-year, 5-year) so the audience can see how the same MTBF reads very differently at different horizons.
**Handover:** Every campaign-success percentage anywhere else in the deck (Slides 23, 25, 29–34, 36–38) traces back to this one formula. If you only explain one equation live, this is it.

## Slide 23 — Appendix D (2/2): Worked Examples

**Say:** Three readings of the same curve: the realistic case (~4y MTBF, 94% campaign success), the contractual case (5y MTBF per Class A, 95% — this is what RTM-05 is built on), and the common misreading (treating "≥99% success" as a lifetime figure, which implies an impossible 387-year MTBF).
**Handover:** The "common misreading" box is worth memorizing verbatim — it's the single most useful sentence in the deck for defusing a reviewer who's misread the reliability requirement.

## Slide 24 — Appendix E: Maintenance Activity Matrix

**Say:** A lookup table — for each of the five operating states from Slide 21, what maintenance is permitted, conditional, or forbidden. Useful as a live reference if an operational question comes up mid-meeting.
**Handover:** This table is the operational consequence of the Slide 21 state hierarchy — if that hierarchy is ever revised, this matrix needs a matching pass.

## Slide 25 — Appendix F: Deriving the SAE Frequency Limit

**Say:** Walk the four-step derivation — continuity requirement → Poisson model → invert for the rate cap → duty-factor conversion — ending at RTM-05's ≤0.26 events/year limit (~one SAE every 46.7 months).
**Handover:** This is a from-first-principles derivation, not an assertion — if RTM-05's numeric value is ever challenged, this slide is the full proof, and Annex X (bottom box) shows the compliance-assessment method that goes with it.

## Slide 26 — Appendix G: Component Reliability Reference

**Say:** The sourced MTBF/MTTR table (CERN feedback + published literature) that everything else's component-level numbers are pulled from — say "this is where the compressor and turbine figures used elsewhere actually come from" to ground the more abstract slides.
**Handover:** The "WHERE THESE NUMBERS FEED IN" box is a literal dependency map — oil-screw MTBF → Slide 32, cold-compressor MTBF → Appendix I (28), turbine MTBF → cross-checked on Appendix H (27). Useful as your own cross-reference cheat sheet when fielding questions out of order.

## Slide 27 — Appendix H: Turbine OEM & Contractor Data

**Say:** Cross-checks the 150,000h turbine planning figure against real Linde Kryotechnik field data (2009–2019), then reconciles Contractor A's ≥96% availability claim against this deck's own RTM-032 reading — land on the "READING THIS RIGHT" box: it's not a contradiction, it's two different ways of stating the same constraint.
**Handover:** If a new turbine OEM's data ever needs to be checked against this deck's assumptions, this slide is the template for how to do that reconciliation.

## Slide 28 — Appendix I: RCM/Weibull Applied — Cold-Compressor Train

**Say:** This is the slide the deck's own text calls out by name from four other slides (20, 25, 26, 31) — the worked Weibull example proving that age matters, not just average MTBF. Oil screw compressors show a 237× increase in 90-day failure probability at 5 years old vs. good-as-new.
**Handover — technical note:** This slide was marked hidden in your uploaded file (pre-existing, not something this pass introduced) but is cross-referenced by name from four other slides — it has been un-hidden so those references resolve to a visible slide. Confirm this is what you want before final issue; if it was hidden on purpose, the four references to it need rewriting instead.

## Slide 29 — Why MTBF Matters

**Say:** This is the IMPROVE-section opener — ties every prior number back to a single shared quantity: MTBF. The BCR013 derivation (accelerator-side, opposite the takeaway) shows the 0.35 events/year budget isn't arbitrary; it's the accelerator's own 250h MTBF requirement translated into cryoplant terms.
**Handover:** "MTBF is a shared 0.35-events/year budget, not a component property" is the framing every subsequent IMPROVE/CONTROL slide assumes. State it explicitly here so the case-file slides (32–34) land as consequences of it, not as new claims.

## Slide 30 — The Hidden Assumption

**Say:** Name the assumption plainly: constant hazard rate means "a 5-year-MTBF component is exactly as likely to fail in month one as month fifty." Call it what the slide calls it — "a convenient mathematical fiction, not a description of real machinery."
**Handover:** This is the pivot slide of the whole deck — everything in ANALYZE (22–28) assumed constant hazard; everything from here to Slide 34 is about what happens once that assumption breaks down.

## Slide 31 — When MTBF Lies — the Wear-Out Boundary

**Say:** Introduce Weibull's β parameter as the "is this assumption even valid" check — β>1 means rising hazard, i.e. real aging. Point back to Appendix I's worked numbers (200–240× higher near-term failure risk at 5 years vs. good-as-new) as the concrete proof, not just theory.
**Handover:** MTBF governs the plant's *average* reliability budget; β governs whether any *one specific unit* is quietly approaching a cliff. Keep these two ideas visually and verbally separate — conflating them is the single most common misunderstanding this deck exists to prevent.

## Slide 32 — Case File: HP Compressors

**Say:** Concrete numbers: a bare 3-of-3 no-redundancy train clears 90 days with 98.2% probability under the Poisson model — but only while the compressors stay inside their flat-hazard useful-life window. The 3+1 redundancy case isn't just insurance against random failure — it buys the *time* to pull a unit for scheduled service before it enters its own wear-out region.
**Handover:** This is the practical argument for N+1 sparing beyond pure statistical margin — worth having ready if a cost-cutting conversation ever proposes dropping the spare compressor.

## Slide 33 — Case File: PVPS

**Say:** At 9-of-9 no-spare, 5-year probability of at least one trip is 67.6% — not because any single pump is unreliable, but because unreliability compounds across fleet size. N+1/N+2 sparing claws back the 90-day and 1-year numbers dramatically, but the 5-year figure stays stubborn (13–33%).
**Handover:** The takeaway is precise and worth quoting directly: "for a 9-unit fleet, the honest 5-year reliability number is a scheduling problem, not just a redundancy problem." This is the strongest argument in the deck for treating PVPS maintenance scheduling as a first-class planning activity, not an afterthought.

## Slide 34 — Case File: Turbines — Nowhere to Hide

**Say:** Turbines are the hardest case: no credible spare position exists because cooling topology fixes each turbine's location in the cold-box train. With 7-of-7 required, 5-year no-trip probability is already down to 94.6%; adding an 8th barely moves it.
**Handover:** State the conclusion exactly as written — "a fleet this exposed cannot be managed by waiting for an MTBF-driven alarm; it has to be managed by knowing, ahead of time, which unit is closest to end of life." This is the slide that most directly motivates the CONTROL section that follows.

## Slide 35 — The Turn: From Predicting Failure to Preventing It

**Say:** This is the explicit pivot from IMPROVE to CONTROL — MTBF was the right tool for budget-setting and acceptance testing (say this to validate everything in Slides 5–28, not undercut it), but the wrong tool for one specific aging unit. The right-hand panel is your own worked-example callout (the same turbine numbers from Slide 34, annotated) — use it as a live worked-example if the audience wants to see the arithmetic, not just the conclusion.
**Handover — technical note:** This slide's right-hand annotation is a small pre-existing callout box that needed both a height increase and a z-order fix in this pass — it was rendering with its bottom two lines hidden behind a pasted screenshot beside it. Both are now visible; no content was changed, only the box's height and stacking order.

## Slide 36 — Predictable Service Replacement

**Say:** The control response to rising hazard rate is not a better MTBF estimate — it's a scheduled intervention set *before* the wear-out region is reached, sized from each component's Weibull characteristic life (η), not its long-run MTBF.
**Handover:** The "in practice" bullet is the actionable policy: set overhaul intervals at a fraction of η (tighter for Class B/C consequence items), track operating hours and Hz-band exposure per unit (already mandated back on Slide 7), and treat "still running at 340,000 hours" as a maintenance trigger, not a success story to celebrate.

## Slide 37 — Reset to New

**Say:** A full overhaul or unit exchange resets the Weibull clock to t=0, restoring the flat, low hazard rate every probability figure in this compendium depends on. Both charts here are the same P0-vs-MTBF/trips-per-year relationship from Slides 22/30, shown again as the closing reference pair.
**Handover:** "Reset to new is what keeps the rest of this deck's mathematics honest — skip it, and every MTBF-based probability quoted earlier quietly becomes optimistic." That line is worth using verbatim if anyone asks "why does the maintenance schedule matter to a reliability number."

## Slide 38 — Reliability Governance — Closing the Loop

**Say:** Close on the same four-step loop previewed on Slide 4 — measure exposure (Slide 7's Hz-band logging) → track age vs. η → replace before wear-out → reset & feed back into next year's RAMI dossier (Slide 13). Say explicitly that this loop is the actual deliverable of the whole compendium, not a summary slide.
**Handover:** This is where the DMAIC cycle re-enters: CONTROL's output (logged renewal events) becomes next year's DEFINE/MEASURE input (an updated RAMI dossier, Slide 13). If this deck is ever revised on a cadence, this is the slide that explains *why* it should be revised on a cadence, not just that it can be.

---

## Cross-cutting notes for whoever inherits this build

- **Font/size system:** every content run's size was chosen algorithmically (see `style.yaml` → `body_text_autofit`) to hit 14–16pt where the box allows it, with a floor no lower than 9.5pt on the very densest pre-existing shapes. If you edit text in PowerPoint afterward and a box overflows, re-run `build_deck4.py` on your edited file rather than hand-adjusting font sizes — the auto-fit logic will re-derive a safe size for you.
- **DMAIC tag colors are load-bearing**, not decorative — DEFINE/MEASURE/ANALYZE use the theme's own accent colors; IMPROVE (amber) and CONTROL (teal) are new non-theme colors chosen to complete a 5-way distinguishable set. If the deck's theme ever changes, these five hex values need to be re-checked for contrast and distinctness as a set, not one at a time.
- **The pink/salmon highlight (FF9999)** on Slides 6, 31, and 32 is your own "flagged / open item" marking convention — it was left untouched. If you want it removed before a wider release, that's a one-line find on those three runs, not a redesign.
- **Three pre-existing content issues were found and deliberately not fixed** (Slide 12's stray artifact, Slide 15's duplicated sentence + typo, Slide 20's bullet indentation) — see `style.yaml` → `pre_existing_content_notes_not_touched` for the exact locations. These are yours to fix since they're content, not style.
