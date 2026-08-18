# QPS_MTBF_WCS — DMAIC Update Change Log

**Baseline (BSLN):** `QPS_MTBF_WCS.pptx`, 41 slides, as uploaded.
**Updated:** `QPS_MTBF_WCS_DMAIC.pptx`, 42 slides.

This log justifies every slide touched. Anything not listed below is untouched BSLN content — same text, same images, same position.

## Theme finding that shaped this update

The file's own embedded PowerPoint theme is named **"SCK•CEN 2020"**, and its accent1/accent2 are corporate purple (`#562873` / `#984A9C`) — visible on the title slide's dot graphic and already used correctly on Slides 2–14. Slides 15–41, however, drifted to accent4 blue (`#034694`) for every title banner. This update does not "add" purple as a new choice — it restores the deck's own defined brand color where new/rebuilt content was created, per your instruction to hold the corporate purple line. Per your direction, the 31 already-reviewed baseline slides (1, 3–32 in the new numbering) keep their existing blue banners untouched — only new/rebuilt material carries purple.

## 1. New slide: "DMAIC Roadmap" (new Slide 2)

Inserted immediately after the title slide, using the deck's existing purple "Text Slide" layout (no new layout created). Maps all 42 slides to Define / Measure / Analyze / Improve / Control, states each phase's slide range and focus, and closes with an explicit note that this is a MASTER set — any phase can be lifted into its own sub-deck. **Justification:** you asked for a DMAIC update "as per available knowledge" plus explicit MASTER/modularity support; a single index slide delivers both without touching the 41 existing slides' content or numbering logic (RTM cross-references inside those slides refer to RTM IDs, not slide numbers, so nothing broke).

*Side effect: inserting this slide shifted every following slide's position by +1. The narrative section you called "Slides 32–41" is the same content, now physically at Slides 33–42 — flagged here so it's not a silent renumbering.*

## 2. DMAIC phase tags on baseline Slides 3–32 (orig. 2–31)

A small bold purple label (DEFINE / MEASURE / ANALYZE / IMPROVE) added to each slide's top-right margin — new content, so it uses the corporate purple. No existing text, image, position, or banner color was changed on these 30 slides. **Justification:** lets the roadmap's phase claims be checked slide-by-slide without reordering a 41-slide deck that already has internal flow (and RTM/figure references) tuned to its current order — this was your explicitly chosen "light touch" option.

Phase mapping logic: DEFINE = scope/requirements/targets slides; MEASURE = OEM data, capability envelopes, acceptance criteria, appendices A–C; ANALYZE = the Poisson/exponential mathematics, the 94–95% ceiling, the Wrong/Better/Chosen architecture trade-off, RCM/Weibull; IMPROVE = the two "Chosen" architecture-decision slides (28–29).

## 3. Slides 33–42 (orig. 32–41): rebuilt as the narrative MTBF compendium

This was the requested core of the update. The original 10 slides were a working data-dump (rough derivations, "guess"/"to check" notes, near-duplicate charts, yellow/red note-to-self callouts) rather than a reader-facing narrative. Every chart, table and derivation already in these slides was **kept as embedded supporting evidence** — nothing was deleted except one exact-duplicate chart image (orig. Slide 41 duplicated orig. Slide 40's two charts pixel-for-pixel; one copy was reused, the other removed to make room for the closing governance-loop diagram). Banners recolored blue→purple (new-content rule); titles rewritten; a narrative panel and a "Key Takeaway" callout added to every slide.

| New # | Title | Orig. # | What changed | Why |
|---|---|---|---|---|
| 33 | Why MTBF Matters | 32 | Retitled; lead text rewritten as 2-sentence narrative hook; yellow note-box restyled to purple "Key Takeaway" with same underlying fact | Opens the arc by naming MTBF as the shared 0.35-events/yr budget every later slide draws on |
| 34 | The Hidden Assumption | 33 | Retitled; chart resized/repositioned to make room for new narrative text + takeaway | States the constant-hazard-rate assumption underlying every Poisson/MTBF number in Slides 18–32 |
| 35 | When MTBF Lies — the Wear-Out Boundary | 34 | Retitled; kept the "Assumptions" list image as-is; narrative + takeaway added below it | Connects directly to the existing RCM/Weibull slide (32) to explain *when* MTBF stops predicting real risk |
| 36 | Case File: HP Compressors | 35 (Kaeser) | Retitled; evidence image resized to right half; narrative + takeaway added | First of three component "case files" proving the wear-out argument with the deck's own numbers |
| 37 | Case File: PVPS | 36 | Retitled; evidence resized; narrative + takeaway added | Second case file — shows the problem compounding across a 9-unit fleet |
| 38 | Case File: Turbines — Nowhere to Hide | 37 | Retitled; evidence + existing red note resized/restyled; narrative + takeaway added | Third case file — the fleet with no spare position, where the argument matters most |
| 39 | The Turn: From Predicting Failure to Preventing It | 38 | Retitled; evidence group (chart + arrow + inset + note) resized; narrative + takeaway added | Explicit pivot slide: states why the deck moves from MTBF prediction to replacement control |
| 40 | Predictable Service Replacement | 39 | Retitled; evidence resized; narrative + takeaway added | Defines the control response — Weibull-η-based scheduled replacement |
| 41 | Reset to New | 40 | Retitled; kept both charts in original side-by-side layout; narrative + takeaway added above/below | Explains the renewal principle that keeps the whole deck's Poisson math valid |
| 42 | Reliability Governance — Closing the Loop | 41 | Retitled; removed the exact-duplicate second chart; added a 4-step Measure→Track→Replace→Reset governance loop diagram in the freed space; narrative + takeaway added | Closing slide — ties back to Slide 5's logging mandate and Slide 10's RAMI dossier, closing the loop the roadmap slide promised |

## Known pre-existing issue, not touched

**New Slide 6 (orig. Slide 5), "Compressor Flow Capability (Reference Data)":** the title text overflows the right edge of the slide in both the baseline file and this update — confirmed present in the original upload, unrelated to this pass. Left as-is since it falls outside the agreed scope (baseline Slides 3–32 got tags only, no content edits). Flagging it here in case you want it fixed in a follow-up pass.

## What was deliberately left alone

- Slides 1 and 3–32 (new numbering): text, images, layout, and blue banners unchanged except for the small purple phase tag.
- All RTM numbers, figures, and technical values throughout: none were altered, recalculated, or reinterpreted.
- Slide master / layouts: no new layout was created; the Roadmap slide reuses the existing purple "Text Slide" layout already used by Slides 3–15.

---

# Addendum — Phase 2 update

**Baseline for this pass:** `QPS_MTBF_WCS_DMAIC.pptx`, 42 slides (Phase 1 output above).
**Updated:** `QPS_MTBF_WCS_DMAIC_v2.pptx`, 46 slides.

Phase 1 gave the retained baseline slides (old Slides 3–32) a phase tag only, per your explicit "light touch" choice at the time. This pass goes back into those slides on your instruction: condense the text-heavy ones into a bullet panel + a supporting chart or diagram, move the full baseline wording to speaker notes as narrator script, split the Roadmap into three parts with worked sample calculations, and add the missing single-unit energy-cost analysis. Four slides were inserted (2 extra Roadmap parts, the new Unit Economics slide, and a split of old Slide 16), which shifted every later slide's number by a further +4 — every cross-reference inside the deck (including the ones Phase 1 wrote into the closing slides) was re-pointed to the new numbers.

## 1. Roadmap split into three (new Slides 2–4)

The single Phase 1 Roadmap slide was too dense for one slide. Split into DMAIC Roadmap (1/3) Define & Measure, (2/3) Analyze, (3/3) Improve & Control. Each part keeps the phase's slide range and one-paragraph description, and adds: stat tiles for the phase's key numbers, at least one worked "SAMPLE CALC" box (N−1 check on part 1; the Poisson and Weibull worked examples that produce the deck's ~95% and wear-out figures on part 2; the replacement-interval calc on part 3), and a 4-step governance-loop mini-diagram on part 3. Banner color follows the phase (purple/blue/purple) per the existing PHASE_COLOR convention.

## 2. New Slide 10: Unit Economics — Single HP Compressor

You asked for the cost of a single HP compressor (or PVPS unit): isothermal compression power at 50% efficiency, 300 K, water-cooled, VFD-driven. Built from the deck's own numbers — 14 bar(a) discharge (Slide 6), 112.5 g/s per unit at FSD 575/72 Hz (Slide 8) — plus flagged assumptions (1.1 bar suction, not stated in the RTMs; 50% isothermal efficiency; helium R = 2077 J/(kg·K)). Result: 356.6 kW actual shaft power at 50% η, against the deck's own 350 kW nameplate — a 2% match, used as a sanity check on both numbers rather than a coincidence. Includes a 3-panel chart (isothermal/actual/nameplate power; annual energy cost at three illustrative tariff bands) and a full assumptions/caveats writeup in speaker notes, since none of this is baseline content.

## 3. Condensed + charted the retained "text-heavy" baseline slides

Applied to Slides 7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 18: original bullets condensed to a left/right panel, full baseline bullet text preserved verbatim in speaker notes ("narrator" script), and a supporting chart or diagram added where the slide previously had none (frequency-zone bar, flow-capability bar, N−1 bar, 3-only-envelope bar, MTBF-by-class bar, Appendix A/B/C charts — 9 charts total in `make_charts.py`, cross-referencing each other by slide number in their captions, e.g. "target 307 g/s, see Slide 6"). Diagram slides (12, 14, 15, 19) got new step-chip, integration-box, and hub-and-spoke diagrams in place of dense paragraph text. All charts use the corporate palette (accent1/2/3/4) with direct value labels on every bar/point, per the deck's own established practice of flagging assumptions and printing numbers rather than relying on color alone.

## 4. Split old Slide 16 into Slides 20–21

Old Slide 16 crammed two RTM items — "3. Failure Classification" (a table) and "4. Reliability Targets by Failure Class" (bullets + numbers) — onto one crowded slide, plus an unrelated leftover textbox duplicated from the Operational Philosophy slide (dead baseline content, removed). Split into Slide 20 (Failure Classification, table only, lightly re-styled with header/row shading) and Slide 21 (Reliability Targets, reusing the Slide 13 MTBF-by-class chart with a "same chart, different lens" caption).

## 5. Light-touch tidy: Slides 5 and 6

Objectives & Scope and Configuration Baseline were already short (5–6 bullets each) but flat. Converted to head/body bullet pairs and added stat tiles (307 g/s target, 320–350 g/s envelope on Slide 5; 1.4 MW / 14 bar / 10–15 K ΔT on Slide 6) so the numbers that recur throughout the deck are visible from the first content slides, not just buried in prose. The baseline's own open question ("pressure-constant vs. pressure-swing — not yet decided") is kept as a flagged note, not resolved.

## 6. Deck-wide phase-color tag correction

Phase 1's tag helper always drew the phase label in flat purple regardless of phase. Fixed deck-wide: ANALYZE tags are now blue (matching the section's own banner convention you asked to keep), CONTROL tags are magenta; DEFINE/MEASURE/IMPROVE were already correct. 17 tag runs recolored; a duplicate leftover tag on the old clone underlying Slide 10 was also removed.

## 7. Bug fixes found in QA (not present in your original file — introduced and fixed within this pass)

Several title/subtitle overlap issues (same class of bug flagged in Phase 1's known-issues note) turned up on newly-touched slides and were fixed by resizing/shortening: Slide 6's title, Slide 10's title, Slide 11's subtitle, Slide 16's title. The CIS/MCS integration diagram (Slide 14) had a third box running off the right edge of the slide — resized. The Utilities hub-and-spoke diagram (Slide 15) had arrow lines drawn through the hub label and box text — arrows now stop short of both. The Operational Philosophy diagram (Slide 19) had leftover baseline bullet text overlapping the new condensed bullets, and chevron labels wrapping mid-word — old content removed, chevrons widened and re-sized.

## Known pre-existing issue, still not touched

Same as Phase 1's note: a stray tiny text fragment ("...window" if interpreted literally.") is visible at the bottom of Slide 31 (baseline "6 Origin of 95%" working slide) — present in the original upload, inside the deliberately-untouched Analyze section, flagged here rather than fixed.

---

# Addendum — Phase 3 update

**Baseline for this pass:** `QPS_MTBF_WCS_DMAIC_v2.pptx`, 46 slides (Phase 2 output above).
**Updated:** `QPS_MTBF_WCS_DMAIC_v3.pptx`, 38 slides.

You flagged old Slides 22–36 as still feeling stale: the phase tag and light restyling from Phases 1–2 didn't change the fact that this block was 15 slides built almost entirely from embedded screenshots (not editable text/tables), with substantial internal duplication. This pass replaces those 15 slides outright with 7 new, fully-editable "Appendix D–I" slides — continuing the Appendix A/B/C naming already established at old Slides 16–18 — and every later slide shifts down by 8 (46 → 38 total).

## 1. Why 15 slides became 7

Reading the embedded screenshots directly (all ~20 images extracted and transcribed before anything was deleted, so no data was invented or guessed) turned up the same content repeated across multiple slides:

- The Poisson P₀ = e^(−λt) methodology chart appeared, with progressively more annotation layered on, **5 times**.
- RTM-05's exact normative text ("...λ_SAE ≤ 0.26 events per calendar year... ≈ one SAE every 46.7 calendar months") appeared **3–4 times**.
- The Weibull "fresh vs. 5-years-old" failure-probability results table appeared **twice**.
- The "reading ≥99% as a literal requirement implies MTBF ≈ 387 years" derivation appeared **twice**.

Every number from every one of those repeats was preserved — nothing was dropped — but each fact now appears exactly once, in the slide where it's actually used, with the other slides that need it cross-referencing back instead of re-deriving or re-pasting it.

## 2. New Slides 22–28 — Appendix D through I

| New # | Title | Replaces (old #s) | Content |
|---|---|---|---|
| 22 | Appendix D (1/2) — Poisson Reliability Model | 5 near-duplicate chart slides | The model, what the chart shows, the formula, and one clean chart (90-day / 1-year / 5-year P₀ curves) |
| 23 | Appendix D (2/2) — Worked Examples | 3 worked-example slides | Three takeaway boxes: the realistic CC+PVPS case, the contractual Class-A case, and the "≥99% literal reading ⇒ 387 years" misreading |
| 24 | Appendix E — Maintenance Activity Matrix | 1 screenshot table | Same 10-activity × 5-state permission matrix, rebuilt as a native table with colored ✓/⚠/✕ status icons and a legend |
| 25 | Appendix F — Deriving the SAE Frequency Limit | 6 screenshot-heavy slides (the "100 occurrences" scratch work, "Wrong"/"Better" derivations, RTM-05 text ×3–4, Annex X) | The 4-step logical chain from the 90-day continuity requirement to RTM-05's 0.26 events/yr cap, plus the normative RTM-05 text and the Annex X worked check, stated once each |
| 26 | Appendix G — Component Reliability Reference | 1 screenshot table (WMF image) | The CERN/literature MTBF-MTTR reference table (8 components), rebuilt as a native table, with a "where these numbers feed in" cross-reference |
| 27 | Appendix H — Turbine OEM & Contractor Data | 2 screenshot slides | Linde Kryotechnik TED-series field data table, plus the Contractor A vs. RTM-032 availability comparison, reframed as a reading-clarification rather than a contradiction |
| 28 | Appendix I — RCM/Weibull Applied: Cold-Compressor Train | 2 slides (series-MTBF derivation + Weibull results table, the table was itself duplicated) | The cold-compressor-train MTBF derivation (105,000 h ÷ 3 ≈ 35,000 h ≈ 4.0 y) and the Weibull "fresh vs. 5-years-old" table + chart, consolidated into one slide |

All charts, tables, and derivation text on these 7 slides are native PowerPoint objects (text boxes, tables, matplotlib-generated charts consistent with the rest of the deck's chart convention) — nothing is a screenshot. Banners stay ANALYZE blue, matching the section either side of it.

## 3. Deck-wide cross-reference renumbering

Consolidating 15 slides into 7 shifts every slide from old-position-37 onward down by 8. Every "Slide N" citation pointing at the old Analyze block or at a slide that moved was re-pointed:

- Roadmap (2/3) and (3/3): ANALYZE/IMPROVE/CONTROL slide ranges, and both worked "SAMPLE CALC" citations.
- "The Hidden Assumption," "Reset to New": their "(Slides 22–36)" citations → "(Slides 22–28)".
- "When MTBF Lies — the Wear-Out Boundary": previously cited old Slide 36 (a general-formula slide that no longer exists standalone, since that formula now lives on Appendix I) — reworded to cite Appendix I (new Slide 28) directly instead.
- "Reliability Governance — Closing the Loop": "Slide 37" → "Slide 29" (its new position; the Slide 7 and Slide 13 references on the same slide were unaffected, both being before the shift point).
- Two untouched slides outside the renumbered block (Reliability Targets & RAMI, Reliability Targets by Failure Class) still cited the old "Slides 22–36" range and needed the same fix even though their own slide numbers didn't move.

A full deck-wide regex sweep for stale "Slide(s) N" patterns confirmed no remaining references to the deleted range.

## 4. Content-accuracy fix found during the rebuild

Appendix G's original "where these numbers feed in" note claimed oil screw *and* cold compressor MTBF both fed the two component Case Files at old Slides 36/38 — but the second of those positions is the Turbines case file, not a cold-compressor one. Corrected to: oil screw compressor MTBF → the HP Compressors Case File; cold compressor MTBF → the cold-compressor-train calculation on Appendix I (which the same slide already stated correctly).

## 5. Bug fixes found in QA (not present in your original file — introduced and fixed within this pass)

- python-pptx assigns new slide XML parts to the lowest free number; deleting the 15 old slides before adding the 7 new ones would have collided with kept slides' physical part numbers. Fixed by reordering the build script to add the 7 new slides first, then delete, then move into position.
- `wipe_body()` (used to clear each Appendix slide's inherited placeholder text) removed every paragraph from the text frame, leaving a `<p:txBody>` with zero children — invalid OOXML that PowerPoint would reject as a repair-on-open. Fixed to leave one empty paragraph, per `python-pptx`'s own `clear()` behavior. Caught by the validator, not by visual QA — a reminder that render-only QA doesn't catch structural corruption.
- Appendix G: the closing "where these numbers feed in" takeaway box overlapped the footer/logo — table, footnote, and takeaway resized and repositioned to clear it.
- Appendix H: the title "Appendix H — Turbine OEM Data & Contractor Benchmark" wrapped to two lines (longer than the other Appendix titles), and — separately — the top-left bullet was drawn at full slide width, running underneath the right-column panel text. Shortened the title to fit one line at the same size as the other Appendix slides, and narrowed the bullet box to the left column's actual width, giving it enough height to wrap within its own space instead of a neighboring one.
- Appendix I: the "Increase" table column header wrapped awkwardly ("Increas / e"); widened that column.
- Appendix E: a footer-proximity issue found in earlier QA (legend row) — kept from an intermediate pass, reconfirmed clear.

## Known pre-existing issue, not touched

Old Slide 42 ("Case File: Turbines," now Slide 34) assumes 105,000 h MTBF for turbines in its worked calculation. Appendix G's reference table and Appendix H's OEM data both give turbines a materially different figure (150,000 h planning value; 299,500–833,364 h from Linde field data) — 105,000 h is actually the cold-compressor figure elsewhere in this deck. This inconsistency was already present in `QPS_MTBF_WCS_DMAIC_v2.pptx`, inside content this pass's scope didn't touch (old Slides 37–46, the IMPROVE/CONTROL narrative — only their numbering shifted). Flagging it here rather than silently changing narrative content outside the requested scope; worth a follow-up pass if you'd like it reconciled.

## What was deliberately left alone

- Slides 1–21: text, images, layout, and banner colors unchanged (only the two stale "Slides 22–36" cross-references described above were corrected).
- Old Slides 37–46 (new Slides 29–38): content unchanged; only slide-number cross-references were updated for the shift.
- All RTM numbers, figures, and technical values: none were altered, recalculated, or reinterpreted — every figure on the new Appendix D–I slides was transcribed from the original screenshots, not recomputed or estimated.

---

# Addendum — Phase 4 update

**Baseline for this pass:** your own hand-edited review copy, `Cryoplant MTBF and System Design_ReviewGBO.pptx` (uploaded, not `final3.pptx`) — 38 slides, containing your manual textbox moves/resizes, rewritten labels, a physical reorder of Slides 19–21, and a pre-existing hidden Slide 28.
**Updated:** `QPS_MTBF_WCS_DMAIC_v4.pptx`, 38 slides (same slide count — this pass is a style/legibility/consistency pass, not a restructure).
**Build script:** `build_deck4.py`.

## 1. Why your upload, not `final3.pptx`, is the base of this pass

Diffing your upload against `final3.pptx` shape-by-shape (matched by name, not position, to avoid false positives from PowerPoint's auto-added "Slide Number Placeholder" shapes) showed it isn't a re-save — it's a deliberately edited working copy: moved and resized text boxes and DMAIC tags (several auto-shrunk by PowerPoint when you resized their containers), rewritten content in several places, and a physical reorder of Slides 19–21 (Failure Classification → Reliability Targets by Failure Class → Operational Philosophy, a different order from `final3.pptx`). This pass builds on top of your edits, not around them.

## 2. Cross-reference fixes for the 19–21 reorder (7 edits)

Your reorder of Slides 19–21 broke 7 in-text "Slide N" citations elsewhere in the deck (Slides 12, 19, 20, and 24 each contained one or more stale references). A full deck-wide scan for `Slides?\s*\d[\d,\s\-–—]*` patterns, cross-checked against a title-to-position map built from the reordered deck, found and corrected all 7. No other content on those slides was touched.

## 3. Typography: two-font system per your instruction

Title shapes and all text on Slides 1–3 keep **Segoe UI** (the deck's original theme font); every other text run on Slides 4–38 was switched to **Aptos**, per your request. Result: 417 runs → Aptos, 77 runs (titles + Slides 1–3) → Segoe UI.

**One caveat worth flagging directly:** Aptos has no metric-compatible LibreOffice substitute in the sandbox this deck was QA-rendered in, so the visual QA renders approximate — not guarantee — real PowerPoint layout for Aptos text. The auto-fit sizing below was deliberately calibrated with a wide safety margin (each shape targets at most ~74% of its estimated available height) specifically to absorb this uncertainty. If you spot a line wrapping unexpectedly when you open the real file in PowerPoint, it should be an isolated case fixable with a half-point nudge on that one shape, not a systemic problem — but it's worth a quick skim on your end since this environment can't confirm real-Aptos layout directly.

## 4. Content-aware font-size auto-fit — "14–16pt, more fill" without overflow

Built a per-shape, content-aware auto-fit system rather than a flat size bump: for every in-scope text box, it estimates the rendered height of the paragraphs at a candidate size and picks the largest size in a 11.5–16pt band that clears the box's available height (falling back to a lower band, then an absolute 9.5pt floor, for the handful of very dense pre-existing shapes that don't fit even at the low end). 211 body runs were resized this way; 44 already-small caption/footnote-scale shapes (under 10pt) were deliberately left alone rather than bumped up, since bumping fine print to "heavy" body-text size would have changed its role on the slide, not just its size.

This required iterating the calibration constants (character-width factor, line spacing, paragraph gap) against real LibreOffice-rendered output several times — the first two calibrations underestimated required height on dense shapes (a near-miss on Slide 10 in an intermediate pass, caught by close inspection of a razor-thin pass/fail margin) and missed manual `<a:br/>` line breaks inside a single paragraph on Slide 15's relabeled diagram (undercounting three of its lines). Both are fixed in the final constants recorded in `style.yaml`.

## 5. DMAIC tag redesign — bigger, color-coded by phase

Per your request to make the phase tags "bigger and more distinguishable... based on the DMAIC letter," all 37 tags were rebuilt as filled rounded-pill badges (white bold text, letter-spaced) instead of small flat-colored text. DEFINE/MEASURE/ANALYZE keep the theme's own purple/magenta/blue accents; IMPROVE (amber, `B5622A`) and CONTROL (teal, `1D7A5F`) are new non-theme colors, since the theme only supplies about four clearly-distinct usable accents and DMAIC needs five. Full color table in `style.yaml`.

## 6. Titles and subtitles repositioned

Per your request, titles and subtitles moved left and slightly upward from a fully-cornered position (not flush into the corner) — 48 shapes repositioned across the deck. Title width is now capped clear of the enlarged DMAIC tag's left edge, and title font auto-shrinks (floor 20pt) to stay on one line where possible, growing to two lines with the subtitle pushed down as a controlled fallback rather than letting a long title visually collide with the tag. (Slide 6's title — the longest in the deck — was the one that actually exercised this fallback path during testing; it renders clean.)

## 7. Full 38-slide visual QA sweep — one real defect found and fixed

Every slide was rendered via LibreOffice and inspected at 100dpi after each round of changes, not just the ones the code changed. One real, user-visible defect turned up and was fixed:

- **Slide 35 ("The Turn: From Predicting Failure to Preventing It"):** your small annotation/callout text box (a miniature of Slide 34's turbine numbers, with a red-arrow pointer you'd added) was rendering with its last two lines invisible. Root cause, confirmed by deliberately over-growing the box far past what should have been necessary and observing zero visual change: the box's declared height wasn't the limiting factor at all — a pasted screenshot sitting just below it, later in the shape stacking order, was silently drawing over the missing lines. Fixed two ways together: grew the box height up to (but not past) the picture's top edge, and — since even that wasn't enough room for all four lines — brought the caption box to the front of the z-order so any remaining overflow draws legibly on top of the picture instead of disappearing behind it. No text content was changed. Twelve small caption/annotation boxes total needed a height correction of this kind across the deck (most fit cleanly after the height fix alone; Slide 35 was the one that also needed the z-order fix).

## 8. Un-hidden slide (pre-existing, not introduced by this pass)

Slide 28 (Appendix I) carried a `show="0"` attribute already present in your uploaded file — not something this pass introduced. Since Appendix I is cross-referenced by name/number from four other slides (20, 25, 26, 31), it was un-hidden so those references resolve to a visible slide rather than a slide the audience would never see in a slideshow or PDF export. **Flagging this explicitly** in case it was hidden on purpose (e.g. reference material you didn't intend to present) — if so, the fix should instead be rewriting those four cross-references, and it's a quick follow-up either way.

## Pre-existing content issues found, deliberately not touched

Three items were noticed during the QA sweep that are content-layer issues in your own edits, not styling — left alone per the same policy as prior phases (flag, don't silently rewrite content outside the requested scope):

- **Slide 12** ("Acceptance & Test System"), step 3 body text: a stray "¨{RTM-0237–0252 pass}" artifact — looks like a leftover edit-marker.
- **Slide 15** ("Utilities & Interfaces"): a duplicated sentence and a garbled word ("INTERCONNECGà") in the process-headers relabeling.
- **Slide 20** ("Reliability Targets by Failure Class"): inconsistent bullet indentation between two adjacent paragraphs.

Separately — **not an issue**, but worth explaining since it stood out in QA: the salmon highlight (RGB `FF9999`) on phrases in Slides 6, 31, and 32 is applied consistently across all three, matching Slide 6's explicit "Open baseline question... not yet decided" framing. Read as your own "flagged / open item" marking convention and deliberately preserved as-is.

## What was deliberately left alone

- All RTM numbers, figures, and technical content: unchanged.
- Slide order and slide count: unchanged (your 19–21 reorder was kept as the authoritative order; only its downstream cross-references were fixed).
- The three pre-existing content issues listed above.
- The salmon-highlight "open item" markings.

## Deliverables from this pass

- `QPS_MTBF_WCS_DMAIC_v4.pptx` — the updated deck.
- `build_deck4.py` — the build script (re-runnable against a fresh copy of your review file).
- `content.yaml` — every slide's text/table content, decoupled from styling.
- `style.yaml` — the design tokens and rules this pass enforced, with rationale.
- `presenter_narrative_notes.md` — per-slide talking points and engineering handover notes, organized by DMAIC phase.
- `README.md` — dependencies, how to re-run the build, and suggested next-pass improvements.
- This addendum.

---

# Phase 5 addendum — energy-mix graphic, Excel SSOT restructuring, BT deck make-over

This round covers five requests in one pass: (1) an energy-consumption breakdown graphic on the MTBF deck, (2) integrating the RTM-BT workbook into your own hand-edited OFFER_Evaluation workbook, (3) splitting that into a FULL (everything) and LITE (reviewer-shareable) pair with navigation and SCK-purple/blue/turquoise tab colors, (4) a style make-over of the BT_Method_Evaluation deck to match the MTBF deck's visual language, and (5) this documentation update. A clarifying-questions attempt was declined mid-task; four open items were resolved with stated default assumptions instead of blocking (see below).

## 1. Energy-mix donut chart — `QPS_MTBF_WCS_DMAIC_v5.pptx`

Added to Slide 6 (Configuration Baseline) as an **amendment**, not a new slide — the deck has ~30 internal "Slide N" cross-references, and Slide 6 already had unused vertical space in its right column plus the "1.4 MW total installed" HP-compressor figure already stated, making it the natural, lowest-risk home rather than inserting a new slide 7 and renumbering everything after it.

Figures are sourced from the newly-supplied canonical contract mirror (`QPS_Contract_mirror_DOCX.pdf`), RTM-395 Table 19 ("Compressor Room / CCB electrical supply and load constraints") and Table 20 ("Cold Box Room / AUB electrical supply & load constraints"):

| Group | Load | Share |
|---|---|---|
| HP Compressors (4 × 356 kW) | 1,424 kW | 80% |
| PVPS pumping skid | 150 kW | 8% |
| Rest of plant (3× Cold Compressor 42 kW, ORS heater 7.5 kW, Gas Analyzer 1.5 kW, UPS 3 kW, Control systems 3 kW, Other/feeder 65 kW) | 206 kW | 12% |
| **Total** | **1,780 kW** | 100% |

The 350 kW back-up diesel (RTM-401) is excluded — it's LOOP-contingency load, not normal operating load, and mixing it in would overstate the "rest of plant" slice. The on-slide citation says so explicitly ("excl. back-up diesel") so the number is defensible without a footnote hunt.

Chart colors blend turquoise (`1FA7A0`) and light purple/pink (`E0A9D6`) into the existing DEFINE purple (`562873`) — the two new hues you asked to bring in ("also turquoise and light purple or pink hues — still fits"), introduced here rather than by re-touching the already-QA'd v4 element colors elsewhere in the deck.

Files: `make_energy_pie.py` (chart generator), `build_deck5.py` (slide amendment). Re-validated with `validate.py --original QPS_MTBF_WCS.pptx` (all passed) and a full visual QA render.

## 2. Excel workbook integration — `QPS_OFFER_Evaluation_FULL_v5.xlsx`

**Base file:** your own hand-edited `QPS_OFFER_Evaluation.xlsx` (the copy with your START_HERE navigation and tab-order changes, and the WEIGHTS_METHOD repositioning) — kept as the authoritative starting point; this pass only adds sheets and recolors tabs, it never overwrites anything you'd already edited.

**What "integrate the RTM-BT" turned out to mean:** `QPS_RTM_BT_Standalone.xlsx` has 13 sheets, but 10 of them are same-named counterparts of sheets your workbook already has. Only 3 sheets are genuinely unique — `RTM_RANKING`, `DOMAIN_SUMMARY`, `RTM_REVIEW_QUEUE` — so the "merge" is a 3-sheet copy, not a 13-sheet reconciliation. These were copied in with full fidelity (values, formulas, per-cell styles, merged ranges, conditional formatting, column widths) using a custom cross-workbook copy helper (`xlsx_copy_helpers.py`, since openpyxl's own `copy_worksheet()` only works within a single workbook), positioned right after OFFER_RANKING.

**Navigation wired in**, not just dropped in: START_HERE's row-3 nav bar gets a 10th "RTM Rank" link, its numbered walkthrough gets a step 9, and NAVIGATION_MAP gets 3 new rows describing each sheet's purpose/action/owner — matching the pattern of every existing row rather than leaving the new sheets undocumented.

**Tab colors:** every tab recolored with an explicit SCK RGB palette — purple (`562873`) for core evaluation content, blue (`034694`) for canonical ranking/reference data, turquoise (`1FA7A0`) for the RTM-only sheets that have no OFFER-side data, light purple/pink (`D9A6D9`/`E0A9D6`) for QA/audit/governance sheets — replacing the workbook's earlier ad-hoc theme-tint coloring, per your "guide via tab colour" request. `COMPLIANCE_LEGEND`'s red stays red (semantic, not decorative). START_HERE and NAVIGATION_MAP stay uncolored as always-white anchor tabs.

**One content gap found and filled, not just flagged:** `START_HERE!A19` was a bold "BT win %" glossary heading with no body text underneath it — every sibling entry (Weighted S above it, Negotiation flag below it) had an explanation, this one didn't. Since it sits on the page every reviewer opens first, filled it in directly (wording matches the engineering handover's own §3.2 definition) rather than leaving a silent gap in a document you're about to share externally.

**A finding, disclosed rather than silently treated as complete:** `QPS_RTM_BT_Standalone.xlsx`'s ranking values are static/flattened snapshots, not live formulas — 130 formulas across 34,838 cells (0.4% density), versus 17% in the canonical spec files supplied in `files_Claude_RTM.zip`, and using a different 4-column (L/R/P/F) scoring scheme rather than the canonical 7-dimension model. This wasn't rebuilt — reconstructing it correctly would mean re-deriving the ranking from the canonical `QPS_OFFER_Cluster_v3_6.xlsx`/`RTM_Importance_Ranking_standalone.xlsx` spec files, which is a bigger, higher-risk job than this pass's scope. Numbers are integrated as-is and usable for review, but they should be treated as a snapshot, not as something that recomputes if the canonical weights change.

Validated: recalculated headlessly via LibreOffice (the xlsx equivalent of the pptx skill's render QA — forces every formula to actually recompute rather than trusting cached values) and scanned for literal Excel error strings — **zero formula errors**, matching the engineering handover's own §6 acceptance bar.

## 3. Reviewer-shareable LITE workbook — `QPS_OFFER_Evaluation_LITE_v5.xlsx`

Per "I would rather have a slimmed down... one big with BT everything and then only the 'really need and need to know' tabs" — built from the FULL workbook rather than as a second independent copy, so the two never drift apart.

**Kept (11 sheets):** START_HERE, DASHBOARD, COMPLIANCE_LEGEND, EVALUATION_WORKSPACE, NEGOTIATION_AGENDA, OFFER_RANKING, RTM_CROSSWALK, RTM_RANKING, QUALITY_CHECKS, LISTS (hidden — dropdown data source, not reviewer-facing but can't be deleted without breaking every STATUS/Depth/Negotiation dropdown), OFFER_CANONICAL.

**Dropped (10 sheets):** OFFER_CANONICAL was *planned* to drop too, until a full cross-sheet formula-dependency scan (not just a hyperlink scan) caught that `QUALITY_CHECKS!C9` genuinely reads `=MIN(OFFER_CANONICAL!M6:M55)` — dropping it would have produced a live `#REF!` in a document meant to go to external reviewers. Added back before finalizing. The other 10 (DOMAIN_SUMMARY, RTM_REVIEW_QUEUE, STANDARDS, DELIVERABLES, AUDIT_NOTES, DMAIC_AUDIT, EVALUATION_INPUT, NAVIGATION_MAP, CODING_HANDOVER, WEIGHTS_METHOD) are internal/audit/method-reproduction artifacts per NAVIGATION_MAP's own role column, not reviewer-facing content — the keep/drop split follows your own curated 9-item START_HERE nav bar and NAVIGATION_MAP's role descriptions rather than a fresh guess.

**Dead links neutralized, not left dangling:** 26 `HYPERLINK("#SheetName!...")` formulas pointed at sheets this trim removed. Each was detected by regex and replaced with plain grey italic text (label kept, link removed) rather than left as a formula that would throw when clicked.

Validated the same way as the FULL workbook: zero dangling cross-sheet references, zero formula errors after headless recalculation.

## 4. BT_Method_Evaluation deck make-over — `BT_Method_Evaluation_v5.pptx`

Starting point: your uploaded `BT_Method_Evaluation_v3_6.pptx` (13 slides), with one real pre-existing overlap fixed first (Slide 9's callout box was drawn over its own footer bar). Same content throughout — this pass is visual only.

- **Font:** unified onto Aptos everywhere (202 runs, including table cells) — the deck was already Aptos-majority (104 Aptos / 56 Calibri / 81 theme-inherited), matching the MTBF deck's body-font convention.
- **Text size:** content-aware bump toward 14–16pt, reusing the same per-shape auto-fit logic as `build_deck4.py` but re-calibrated to this deck's own tighter paragraph spacing (~1.08 line spacing vs. the MTBF deck's 1.45 — using the MTBF deck's numbers here would have under-fit almost everything and left it unbumped). 12 shapes bumped; several narrow, tightly-paired shapes were deliberately excluded rather than risk breaking their layout — the Layer A/B/C progress cards on Slide 2 (which carry a deliberate 3-tier internal size hierarchy a flat resize would flatten), the tier-chip count labels on Slide 7 and the weight-dimension rows on Slide 4 (both bound to fixed-width color chips), and the "link type distribution" label/value row pairs on Slide 13 (caught by render QA: the longest label, "Direct — primary evidence:", ran into its adjacent number once bumped — a horizontal overflow the row-height estimator doesn't model, so the whole row-pair pattern was excluded rather than patched one row at a time).
- **Color:** header bars, footer bars, and "Board position/read" callout backgrounds blended from the original flat navy/light-blue-grey pair toward deep purple (`441F63`) and light lavender (`F3EC F8`/`EFE5F5`) — the purple/blue blend you asked for. The tier and STATUS-legend colors (T0 Gate red, T1 green, T2 blue, T3 gray on Slide 7; the 7-color STATUS legend on Slide 12) were explicitly left untouched — those encode meaning, not brand, and recoloring them would change what the deck communicates, not just how it looks.
- **A second real overlap, found by this pass's own QA:** Slide 9's chart picture and its sensitivity-analysis callout box had a ~211k EMU static overlap that predates this round (the earlier single-slide fix only solved the *footer* collision by moving the box up — toward the chart, not away from it) — invisible at the original small font, but it became a visible collision once body text anywhere near it was touched. Fixed by shrinking the chart (same aspect ratio, still fully legible) to free real vertical room, then re-sizing the callout box to what's actually left between the shorter chart and the footer bar — confirmed by directly computing the box's required height against its own paragraph spacing, not just by eyeballing a re-render.

Re-validated with `validate.py --original BT_Method_Evaluation_v3_6.pptx` (all passed) and a full 13-slide visual QA sweep after every geometry/font change, not just the slides the code touched.

## Assumptions adopted after a declined clarifying-questions prompt

Before starting this round's build work, four open questions were put to you via a clarifying-questions prompt; that prompt was declined. Rather than re-ask or stall, these defaults were adopted and are called out here so they're easy to revisit:

1. **RTM-BT integration scope:** fold in the 3 unique sheets as-is (no attempt to reconcile the 4-dimension RTM-BT scoring scheme against the canonical 7-dimension model) — see the formula-integrity finding above.
2. **BT deck DMAIC-tag scope:** typography/palette/spacing only this round — no DEFINE/MEASURE/etc. phase badges added to this deck (it isn't itself organized by DMAIC phase the way the MTBF deck is).
3. **Handover deck** (`QPS_OFFER_EVAL_DMAIC_Handover_Deck.pptx`): left untouched this round — not in scope for this pass.
4. **"Update... skill to match":** read as updating this project's own documentation (this changelog, the READMEs), not building a separate installable Skill package.

## Deliverables from this pass

- `QPS_MTBF_WCS_DMAIC_v5.pptx` — MTBF deck with the energy-mix graphic added.
- `QPS_OFFER_Evaluation_FULL_v5.xlsx` — full SSOT workbook (21 sheets), RTM-BT integrated, SCK tab colors, extended navigation.
- `QPS_OFFER_Evaluation_LITE_v5.xlsx` — reviewer-shareable subset (11 sheets) derived from the FULL workbook.
- `BT_Method_Evaluation_v5.pptx` — restyled methodology deck, same content.
- `make_energy_pie.py`, `build_deck5.py` — energy chart + slide amendment scripts.
- `xlsx_copy_helpers.py`, `build_workbook_full_v5.py`, `build_workbook_slim_v5.py` — Excel integration + slim-down scripts.
- `build_bt_deck_v5.py` — BT deck restyle script.
- This addendum.
