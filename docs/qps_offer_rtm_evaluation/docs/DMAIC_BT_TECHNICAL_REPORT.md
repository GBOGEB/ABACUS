# BT Method — PCA & DMAIC Technical Analysis Report

**Project:** QPS OFFER Evaluation — RTM/OFFER Benefit–Trade-off (BT) Method
**Scope:** Statistical structure of the 7-dimension BT scoring (L/R/P/F/Q/LC/C) across all 722 RTM requirements
**Data source:** `QPS_OFFER_Evaluation_FULL_v19.xlsx` — `RTM_RANKING`, `DOMAIN_SUMMARY` (live query, not estimated)
**Method:** DMAIC (Define–Measure–Analyze–Improve–Control), with a Principal Component Analysis (PCA) computed on standardized z-scores of the 7 raw dimension scores

---

## 0. Executive summary

The question behind this report was why the project's single largest bucket of
requirements — Section 4, the technical requirements, 593 of 722 RTMs (82%) —
does not also read as the top-ranked bucket on every scoring lens, and whether
a hidden or advanced analysis layer exists in the workbook that would explain
the gap. Direct inspection of the workbook (§2.2) rules out a hidden layer.
The real explanation is structural: **Sum** Weighted S rewards volume, **Average**
Weighted S rewards per-item intensity, and Section 4's per-item average
(30.61) is unremarkable next to smaller sections such as Section 5 (31.90,
only 20 items) — the two metrics are supposed to diverge this way once volume
is this lopsided.

A full PCA on the 7 BT dimensions (§3.3–3.4) shows the requirement space is
genuinely 7-dimensional — no 1–2 factor shortcut exists, it takes 5 of 7
components to reach 84.5% of variance — which validates keeping all seven
weighted dimensions rather than collapsing to a simpler score. The most
load-bearing finding (§4.2) is that the four largest technical domains
(Subsystems, Control & Interlock, Buildings & Utilities, Process & Functional
— 390 of 722 RTMs, 54% of the entire RTM) sit on the opposite pole of the
dominant component (PC1, "compliance/quality" vs. "engineering performance")
from where T0 Gate items cluster. Gate items carry Safety/Legal, Quality and
Lifecycle weight almost by definition; the bulk technical domains carry
Performance/Functional weight instead — which is exactly why raw item *count*
and per-item *stakes* pull apart, and it is a property of the scoring design
working as intended, not a data or method flaw.

Section 5 (Improve) lays out four concrete, scoped-but-not-yet-built proposals
for turning this analysis into a recurring, reusable view rather than a
one-off report: a PC1/PC2 scatter, a domain quadrant view, wide-but-shallow BT
tagging of non-RTM populations, and a "depth by link" nearest-neighbor
mechanism so lightly-tagged items can reach the full analysis of their nearest
deep-scored RTM neighbors. None of the four are built yet; they are logged
here as a scoping decision point, per this project's standing "disclose,
don't build speculatively" convention, and carried forward into
`NEXT_ITERATION_BACKLOG.md`.

---

## 1. Define

### 1.1 The question posed

Why doesn't the largest bucket of RTM requirements (Section 4 / the largest
technical domains) also read as the top-ranked bucket on every BT lens — and
is there a hidden or password-protected "advanced" analysis layer in the
workbook that would explain the divergence?

### 1.2 Hidden-layer check — answered directly, not assumed

`QPS_OFFER_Evaluation_FULL_v19.xlsx` was inspected directly (not inferred):
28 sheets, all `sheet_state = visible`, all `protection.sheet = None` (no
per-sheet password), workbook-level `security = None` (no structure/window
protection), and the zip archive contains no `vbaProject.bin` (no macros) and
no extra hidden parts beyond the 28 worksheets, their tables, charts and
comments.

**Finding: there is no hidden or password-protected advanced-analysis sheet
in this workbook.** Whatever deeper structure explains the divergence has to
be computed fresh from the workbook's own raw 7-dimension scores — which is
what §2–§4 of this report do.

---

## 2. Measure

### 2.1 Sum vs. Average Weighted S, by Section

Section 4 (technical requirements) accounts for 593 of 722 RTMs — 82% of the
entire RTM by volume.

| Section | RTM count | Sum Weighted S | Average Weighted S |
|---|---:|---:|---:|
| **4** | **593** | **18,152.0** | **30.61** |
| 8 | 45 | 1,306.7 | 29.04 |
| 7 | 21 | 347.0 | 16.52 |
| 5 | 20 | 638.0 | 31.90 |
| 9 | 19 | 546.7 | 28.77 |
| 10 | 17 | 537.7 | 31.63 |
| 6 | 7 | 139.7 | 19.95 |

Section 4 dominates the Sum column by an order of magnitude, as expected
since Sum = count × average and Section 4 has 14× the next-largest section's
item count. Its Average (30.61) is unremarkable — Section 5, with only 20
items, runs slightly higher per-item (31.90).

### 2.2 Sum vs. Average Weighted S, by Domain

The same pattern holds one level down, at Domain:

| Domain | Count | Sum Weighted S | Average Weighted S | Rank by Sum | Rank by Average |
|---|---:|---:|---:|---:|---:|
| **Subsystems** | **202** | **6,455.7** | 31.96 | **#1** | #7 |
| Acceptance Testing | 66 | 2,439.7 | 36.96 | #2 | #3 |
| Control & Interlock | 86 | 2,142.0 | 24.91 | #3 | #15 |
| Commissioning | 4 | 177.3 | **44.33** | #16 | **#1** |
| After-Sales | 3 | 126.0 | 42.00 | #17 | #2 |
| Training | 8 | 294.0 | 36.75 | #12 | #4 |

Subsystems ranks #1 on Sum purely because it has 3× the next-largest domain's
item count (202 vs. 66), not because its individual items are unusually
high-stakes; its average (31.96) puts it 7th, well behind Commissioning
(44.33) and After-Sales (42.00), which each have only 3–4 items but every one
scores high. **Sum answers "where is the volume/total exposure," Average
answers "which items are individually highest-stakes, independent of how
many there are."** A domain scoring high on one lens and mid-pack on the
other is not a data problem — it is the two lenses doing their separate jobs,
consistent with the Navigator's existing "read together, for a presenter"
callout under the Domain volume charts.

### 2.3 PCA on the 7 BT dimensions — explained variance

A standard PCA (z-score standardized, since the 7 dimensions have different
scales — LC and C especially, with means near 0.3 and 0.08 respectively vs.
F's mean of 1.61) was run across all 722 RTMs' raw dimension scores
(L / R / P / F / Q / LC / C).

| PC | Variance explained | Cumulative |
|---|---:|---:|
| PC1 | 30.6% | 30.6% |
| PC2 | 16.5% | 47.0% |
| PC3 | 13.8% | 60.9% |
| PC4 | 12.4% | 73.2% |
| PC5 | 11.3% | 84.5% |
| PC6 | 8.9% | 93.4% |
| PC7 | 6.6% | 100.0% |

**Finding: the requirement space is genuinely 7-dimensional, not reducible to
1–2 factors.** No single component dominates — it takes 5 of the 7
components to reach 84.5% of the variance, and the last two still carry a
combined 15.5%. This validates the project's decision to keep all 7 weighted
dimensions in the ranking formula rather than collapsing to a simpler score:
if two or three of the seven dimensions were noisy proxies for the same
underlying thing, PCA would show it as one or two components eating
70–80%+ of the variance. It does not.

### 2.4 PCA loadings and axis interpretation

Loadings — how each raw dimension contributes to the first 3 components:

| Dimension | PC1 | PC2 | PC3 |
|---|---:|---:|---:|
| L (Safety/Legal) | +0.523 | −0.109 | −0.205 |
| R (Reliability) | −0.038 | **+0.761** | +0.079 |
| P (Performance) | −0.391 | −0.254 | +0.387 |
| F (Functional) | −0.465 | +0.149 | −0.105 |
| Q (Quality/Verifiability) | +0.426 | −0.265 | −0.047 |
| LC (Lifecycle) | +0.358 | +0.500 | +0.122 |
| C (Cost) | +0.215 | −0.048 | **+0.880** |

Reading the axes:

- **PC1 (30.6%) — "compliance/quality emphasis" vs. "engineering performance
  emphasis."** Positive = high Safety/Legal, Quality, Lifecycle; negative =
  high Performance, Functional. The closest thing to a dominant axis, and a
  real substantive split rather than redundancy between dimensions.
- **PC2 (16.5%) — "reliability + lifecycle" axis**, loading almost entirely
  on R (0.761) and LC (0.500), largely independent of everything else.
- **PC3 (13.8%) — near-pure Cost axis.** C loads at 0.880 with everything
  else small — Cost behaves almost like its own independent dimension,
  barely entangled with the other six, confirming Cost needs its own weight
  and can't be inferred from the other six.

### 2.5 Population split: bulk vs. distinctive items

Using each item's distance from the population center in PC1–PC2 space as a
measure of how typical vs. how distinctive its dimension profile is:

- **548 items (76%)** sit in the central, typical zone — their L/R/P/F/Q/LC/C
  profile looks like a blend close to the overall average shape (the "bulk").
- **174 items (24%)** sit in the outer, distinctive zone — profiles that lean
  unusually hard into one or two dimensions rather than a typical blend (the
  "remaining" items worth studying on their own, since a population-average
  view would wash them out).

### 2.6 Domain-level position on the two main axes

Mean PC1 / PC2 per domain (n = item count):

| Domain | n | PC1 (compliance ← → performance) | PC2 (reliability/lifecycle) |
|---|---:|---:|---:|
| Acceptance & Warranty | 17 | +3.24 | +1.51 |
| After-Sales | 3 | +1.93 | +3.62 |
| Codes & Standards | 19 | +1.70 | −0.25 |
| Quality Assurance & Control | 45 | +2.24 | −0.83 |
| Technical Documentation | 28 | +2.06 | +0.61 |
| Safety & Protection | 20 | +1.31 | −0.24 |
| **Buildings & Utilities** | **53** | **−1.27** | +0.30 |
| **Process & Functional** | **49** | **−1.27** | −0.65 |
| **Subsystems** | **202** | **−1.04** | +0.06 |
| Cryogenic Interfaces | 17 | −1.02 | −0.24 |
| **Control & Interlock** | **86** | **−0.74** | +0.40 |

---

## 3. Analyze

### 3.1 The Section-4 / volume-vs-stakes divergence, explained

The divergence between Sum and Average Weighted S (§2.1–2.2) is the expected
mathematical behavior of the two metrics once volume is this lopsided (82%
of all RTMs sit in one section) — not evidence of a hidden layer, a scoring
bug, or missing data.

### 3.2 Why the four largest technical domains sit opposite T0 Gate items

This is the structural finding behind the Section-4 question. The four
largest bulk domains — **Subsystems, Control & Interlock, Buildings &
Utilities, Process & Functional (390 of 722 RTMs, 54% of the entire RTM)** —
all sit on the **negative** side of PC1, the "engineering performance" pole.
T0 Gate items, as a group, average **PC1 = +1.58** — solidly on the opposite,
compliance pole.

That split is not a coincidence: gate items are gate items *because* they
carry Safety/Legal, Quality and Lifecycle weight, which loads positively on
PC1 and (via Q and LC) pushes Average Weighted S up. The bulk technical
domains' strength is in Performance and Functional, which load negatively on
PC1 and do not carry the same per-item average premium. This is the scoring
method working as designed, not a defect.

### 3.3 Correlation of Weighted S with PC1 vs. PC2

Weighted S itself correlates weakly with PC1 (r = 0.03) but moderately with
PC2 (r = 0.33, the reliability/lifecycle axis). So the ranking is not simply
"high on the compliance pole = high score" — the reliability/lifecycle axis
matters more to the actual ranking than the compliance/performance split
does.

### 3.4 T0 Gate tier is independent of Weighted S — not a score-threshold artifact

A direct question this round: do T0 Gate items simply default to "top
ranked," or is Tier assignment genuinely independent of the Weighted S
score? Checked directly against all 722 RTMs' `tier` and `weightedS` fields:

| Tier | n | Min Weighted S | Max Weighted S | Avg Weighted S |
|---|---:|---:|---:|---:|
| T0 Gate | 43 | 20.00 | 62.67 | 31.60 |
| T1 Primary | 156 | 37.33 | 76.67 | **47.46** |
| T2 Secondary | 244 | 24.00 | 37.33 | 30.24 |
| T3 Contextual | 279 | 0.00 | 24.00 | 19.81 |

**Finding: T0 Gate is not the top-scoring tier, and its Weighted S range
overlaps heavily with T1 and T2.** T1 Primary has both the highest average
(47.46) and the highest single score (76.67) in the entire RTM — well above
T0 Gate's average (31.60) and max (62.67). T0 Gate's own scores span nearly
the full population range, from 20.00 up to 62.67, and its floor sits
squarely inside T2 Secondary's range. 19 of the 43 T0 items sit at exactly
20.00 — the same score a T2 item can carry — while carrying `gate = Yes`.

This confirms Tier and Weighted S are **two independent signals, not one
derived from the other**: `gate = Yes` (T0) marks an item as a mandatory,
non-negotiable compliance/safety criterion regardless of how it happens to
score on the 7-dimension formula, while Weighted S measures the magnitude of
that item's combined L/R/P/F/Q/LC/C intensity. An item can be an absolute
must-pass gate (T0) while scoring modestly (e.g. RTM-001, RTM-003, RTM-004 —
general compliance/documentation gate items at the population floor of
20.00), and conversely a very high-scoring item can sit in T1 rather than T0
if it isn't flagged as an absolute gate. Practically: **T0 should be read as
"must not fail," not "ranks highest"** — a reviewer scanning by Weighted S
alone would systematically under-prioritize several T0 items sitting at or
near the score floor, purely because the gate flag and the score come from
different, independent criteria.

---

## 4. Improve — priority-focus proposals (none built yet)

Four concrete, low-effort additions this analysis suggests. All four are
**proposals**, flagged here for a scoping decision rather than built
speculatively, per this project's standing disclosure convention. See
`NEXT_ITERATION_BACKLOG.md` for sequencing.

### 4.1 Proposal A — PC1/PC2 scatter view

A scatter plot of all 722 RTMs in PC1×PC2 space, colour-coded by domain, in
the Navigator (or as a static chart in the deck), so the "distinctive 24%"
(§2.5) are visually separable from the bulk cluster instead of only being
identifiable via a percentile threshold in a script.

### 4.2 Proposal B — Domain quadrant view

Average Weighted S (x-axis) vs. RTM count (y-axis, log-scale given the
202-vs-3 spread) — turns the Sum-vs-Average divergence in §2.1–2.2 into one
glance instead of two separate charts a reader has to mentally
cross-reference.

### 4.3 Proposal C — Wide-but-shallow BT tagging across other populations

Apply the same 7-letter vocabulary (L/R/P/F/Q/LC/C), even in simplified
form, across every other population in the project that doesn't currently
get it — OFFER response text, STANDARDS cross-references, DELIVERABLES
items, NEGOTIATION_AGENDA items — so the BT language becomes the common unit
of measure everywhere in the project, not just in RTM_RANKING. Lightweight
per-item: e.g. a 1–7 flag for which dimension(s) an item primarily touches,
not a full weighted score.

### 4.4 Proposal D — Depth by link, not by default

Rather than deep-scoring every population (expensive, and would fake a
precision that isn't there), make depth *reachable* rather than *default*:
any lightly-tagged item (from Proposal C) that shares a dimension profile,
cluster, or domain with an already-deep-scored RTM gets a "similar items"
link — clicking through takes the reader from the shallow view into the full
7-dimension analysis of its nearest deep-scored neighbors. Concretely, this
would project a lightly-tagged item's flags into the same PC1/PC2/PC3 space
computed in §2.3–2.4 and surface its nearest deep-scored RTM neighbors as
"items like this one already have full analysis — see: RTM-xxx, RTM-yyy."

What this would take, if picked up: (1) a decision on which additional
populations get lightweight tagging first — OFFER items are the obvious
first candidate, since OFFER_RANKING already carries a static BT rank with
no dimension breakdown; (2) a similarity metric — nearest-neighbor in PC
space is the natural choice, already computed in §2.3–2.4; (3) a UI
decision — Navigator cross-links vs. a new dedicated "similar items" panel.

---

## 5. Control

### 5.1 Reproducibility requirement

If any of the four Improve proposals gets built, it must follow the same
"generated from live data, never hand-typed" rule as everything else in this
project. The PCA numbers in this report came from a one-off working script
(`/tmp` scratch files, not yet saved as a named, discoverable script) — if
any of §4's proposals becomes a recurring view, it needs a proper
`compute_pca.py` saved under a discoverable name in the project root, so the
numbers can be regenerated any time the underlying RTM data changes rather
than silently going stale.

### 5.2 Data provenance

All numbers in this report came from live queries against
`QPS_OFFER_Evaluation_FULL_v19.xlsx` (`RTM_RANKING` for section/domain/7-
dimension raw scores, `DOMAIN_SUMMARY` for the cross-check on Sum/Average by
domain), computed via `numpy`/`scikit-learn` PCA — nothing in this report is
estimated or carried over from an earlier session. The PCA component scores,
dimension matrix, and per-RTM metadata used to produce every table above are
saved at `/tmp/pca_scores.npy`, `/tmp/pca_X.json`, `/tmp/pca_meta.json` for
this session only, pending the `compute_pca.py` promotion noted in §5.1.

---

## 6. Appendix — where this fits in the broader project

This report formalizes and extends `PCA_DMAIC_BT_ANALYSIS.md` (the original
working analysis) into outline-numbered technical-report form, per request.
Nothing in §4's four proposals is built into the Navigator, workbook, or deck
yet — that build-out, plus the other structural asks logged the same round
(individual-RTM parent/child and parallel graphing views, full-verbatim RTM
text, Excel typing-ease and cross-link work, and a full HTML/PDF/Word QA
sweep) are tracked in `NEXT_ITERATION_BACKLOG.md`.
