# PCA + DMAIC pass on the 7-dimension BT scores — real numbers, no hidden layer

## 0. First, the direct answer: is there a hidden/password-protected "advanced" layer?

Checked directly, not assumed: `QPS_OFFER_Evaluation_FULL_v19.xlsx` has 28
sheets, all `sheet_state = visible`, all `protection.sheet = None` (no
per-sheet password), workbook-level `security = None` (no structure/window
protection), and the zip contains no `vbaProject.bin` (no macros) and no
extra hidden parts beyond the 28 worksheets, their tables, charts and
comments. **There is no hidden or password-protected advanced-analysis
sheet in this workbook.** Whatever deeper analysis you're picturing isn't
sitting there waiting to be unlocked — it has to be computed fresh, which
is what the rest of this document does, using the workbook's own raw
7-dimension scores as input.

## 1. Why Average and Sum Weighted S diverge — computed, not guessed

You asked specifically about "Section 4" featuring the vast bulk of
requirements. Checked directly against `RTM_RANKING!Section`: **Section 4
alone accounts for 593 of the 722 RTMs (82%)** — this is the technical
requirements section, and it is genuinely almost the whole RTM by volume.

| Section | RTM count | Sum Weighted S | Average Weighted S |
|---|---:|---:|---:|
| **4** | **593** | **18,152.0** | **30.61** |
| 8 | 45 | 1,306.7 | 29.04 |
| 7 | 21 | 347.0 | 16.52 |
| 5 | 20 | 638.0 | 31.90 |
| 9 | 19 | 546.7 | 28.77 |
| 10 | 17 | 537.7 | 31.63 |
| 6 | 7 | 139.7 | 19.95 |

Section 4 dominates the **Sum** column by an order of magnitude — exactly
as you'd expect, since Sum is literally count × average, and Section 4 has
14× the next-largest section's item count. But its **Average** (30.61) is
completely unremarkable — Section 5, with only 20 items, actually runs
slightly higher per-item (31.90).

The same pattern holds one level down, at Domain (not Section):

| Domain | Count | Sum Weighted S | Average Weighted S | Rank by Sum | Rank by Average |
|---|---:|---:|---:|---:|---:|
| **Subsystems** | **202** | **6,455.7** | 31.96 | **#1** | #7 |
| Acceptance Testing | 66 | 2,439.7 | 36.96 | #2 | #3 |
| Control & Interlock | 86 | 2,142.0 | 24.91 | #3 | #15 |
| Commissioning | 4 | 177.3 | **44.33** | #16 | **#1** |
| After-Sales | 3 | 126.0 | 42.00 | #17 | #2 |
| Training | 8 | 294.0 | 36.75 | #12 | #4 |

**Subsystems is #1 on Sum purely because it has 3× the next-largest
domain's item count** (202 vs. 66) — not because its individual items are
unusually high-stakes. Its average (31.96) puts it 7th, well behind
Commissioning (44.33) and After-Sales (42.00), which each have only 3–4
items but every one of them scores high. This is exactly what Sum and
Average are each designed to show, and they're supposed to diverge this
way: **Sum answers "where is the volume/total exposure," Average answers
"which items are individually highest-stakes, independent of how many
there are."** A domain scoring high on one and mid-pack on the other isn't
a data problem — it's the two lenses doing their separate jobs. This is
the same logic already built into the Navigator's "Read together, for a
presenter" callout under the Domain volume charts, now with the specific
numbers behind it.

## 2. PCA on the 7 BT dimensions (L / R / P / F / Q / LC / C) — real, computed

Ran a standard PCA (z-score standardized, since the 7 dimensions have
different scales — LC and C especially, with means near 0.3 and 0.08
respectively vs. F's mean of 1.61) across all 722 RTMs' raw dimension
scores.

**Explained variance per component:**

| PC | Variance explained | Cumulative |
|---|---:|---:|
| PC1 | 30.6% | 30.6% |
| PC2 | 16.5% | 47.0% |
| PC3 | 13.8% | 60.9% |
| PC4 | 12.4% | 73.2% |
| PC5 | 11.3% | 84.5% |
| PC6 | 8.9% | 93.4% |
| PC7 | 6.6% | 100.0% |

**Finding: the requirement space is genuinely 7-dimensional, not
reducible to 1–2 factors.** No single component dominates — it takes 5 of
the 7 components to reach 84.5% of the variance, and the last two still
carry a combined 15.5%. This is itself a meaningful result: it validates
the project's decision to keep all 7 weighted dimensions in the ranking
formula rather than collapsing to a simpler score. If two or three of the
seven dimensions were just noisy proxies for the same underlying thing,
PCA would show it (one or two components eating 70-80%+ of the variance).
It doesn't.

**Loadings — how each raw dimension contributes to the first 3
components:**

| Dimension | PC1 | PC2 | PC3 |
|---|---:|---:|---:|
| L (Safety/Legal) | +0.523 | −0.109 | −0.205 |
| R (Reliability) | −0.038 | **+0.761** | +0.079 |
| P (Performance) | −0.391 | −0.254 | +0.387 |
| F (Functional) | −0.465 | +0.149 | −0.105 |
| Q (Quality/Verifiability) | +0.426 | −0.265 | −0.047 |
| LC (Lifecycle) | +0.358 | +0.500 | +0.122 |
| C (Cost) | +0.215 | −0.048 | **+0.880** |

**Reading the axes:**
- **PC1 (30.6%) — "compliance/quality emphasis" vs. "engineering
  performance emphasis."** Positive = high Safety/Legal, Quality,
  Lifecycle; negative = high Performance, Functional. This is the closest
  thing to a dominant axis, and it's a real substantive split, not
  redundancy.
- **PC2 (16.5%) — "reliability + lifecycle" axis**, loading almost
  entirely on R (0.761) and LC (0.500), largely independent of everything
  else.
- **PC3 (13.8%) — near-pure Cost axis.** C loads at 0.880 with everything
  else small — Cost behaves almost like its own independent dimension,
  barely entangled with the other six. That's a useful confirmation for
  the weighting method: Cost genuinely needs its own weight, it can't be
  inferred from the other six.

## 3. Where the "bulk" sits vs. the "remaining" items — the granular drill-down you asked for

Using each item's distance from the population center in PC1–PC2 space as
a measure of "how typical vs. how distinctive this item's dimension
profile is":

- **548 items (76%) sit in the central, typical zone** — their L/R/P/F/Q/LC/C
  profile looks like a blend close to the overall average shape. This is
  the "bulk / major count" you asked to expose separately.
- **174 items (24%) sit in the outer, distinctive zone** — profiles that
  lean unusually hard into one or two dimensions rather than a typical
  blend. These are the "remaining items" worth studying on their own,
  since they're the ones a population-average view would wash out.

**Domain-level position on the two main axes** (mean PC1/PC2 per domain,
n = item count):

| Domain | n | PC1 (compliance ← → performance) | PC2 (reliability/lifecycle) |
|---|---:|---:|---:|
| Acceptance & Warranty | 17 | +3.24 | +1.51 |
| After-Sales | 3 | +1.93 | +3.62 |
| Codes & Standards | 19 | +1.70 | −0.25 |
| Quality Assurance & Control | 45 | +2.24 | −0.83 |
| Technical Documentation | 28 | +2.06 | +0.61 |
| Safety & Protection | 20 | +1.31 | −0.24 |
| — | | | |
| **Buildings & Utilities** | **53** | **−1.27** | +0.30 |
| **Process & Functional** | **49** | **−1.27** | −0.65 |
| **Subsystems** | **202** | **−1.04** | +0.06 |
| **Cryogenic Interfaces** | 17 | **−1.02** | −0.24 |
| **Control & Interlock** | **86** | **−0.74** | +0.40 |

**This is the real structural finding behind your Section-4 question.**
The four largest bulk domains (Subsystems, Control & Interlock, Buildings
& Utilities, Process & Functional — 390 of 722 RTMs, 54% of the entire
RTM) all sit on the **negative** side of PC1 — the "engineering
performance" pole, not the "compliance/quality" pole. Meanwhile T0 Gate
items, as a group, average **PC1 = +1.58** — solidly on the compliance
pole, the opposite direction from where the volume actually sits. That's
not a coincidence: gate items are gate items *because* they carry
Safety/Legal, Quality and Lifecycle weight, which is exactly what loads
positively on PC1 and (via Q and LC) pushes Average Weighted S up — while
the bulk technical domains' strength is in P and F, which load negatively
on PC1 and don't carry the same per-item average premium. Weighted S
itself correlates weakly with PC1 (r = 0.03) but moderately with PC2 (r =
0.33, the reliability/lifecycle axis) — so it isn't simply "high on the
compliance pole = high score"; the reliability/lifecycle axis matters more
to the actual ranking than the compliance/performance split does.

## 4. DMAIC framing, with a BT-analysis priority focus

**Define.** The open question was: why doesn't the biggest bucket of
requirements (Section 4 / the large technical domains) show up as the
top-ranked bucket on every lens, and is there a hidden layer that would
explain it. Answered in §0–1: there's no hidden layer, and the divergence
is the expected mathematical behavior of Sum vs. Average once volume is
this lopsided (82% of all RTMs in one section).

**Measure.** §2 quantifies the dimension structure itself (PCA, 7
components, no dominant single factor, Cost nearly orthogonal to the other
six). §3 quantifies where individual items sit relative to the population
center (76% bulk / 24% distinctive) and confirms, with real correlation
coefficients, that Weighted S tracks the reliability/lifecycle axis (PC2,
r=0.33) more than the compliance/performance axis (PC1, r=0.03).

**Analyze.** The practical read: the project's four largest technical
domains are volume-dominant but average-unremarkable because their
strength is concentrated in Performance/Functional, which the scoring
method (correctly, per its own design) doesn't reward as heavily per-item
as Safety/Legal/Quality/Lifecycle. This isn't a scoring bug — it's the
7-dimension weighting doing what it was built to do. The 24% "distinctive"
items (§3) are where a reviewer's attention finds outliers a pure
count-based scan would miss; the 76% "bulk" items are where the reviewer's
*volume* of work sits, even though few individual bulk items are
individually alarming.

**Improve — priority-focus proposal.** Two concrete, low-effort additions
this analysis suggests, neither built yet (flagging for a scoping decision
rather than building speculatively, per this session's established
pattern):
1. A **PC1/PC2 scatter view** in the Navigator (or a static chart in the
   deck) plotting all 722 RTMs, colour-coded by domain, so the
   "distinctive 24%" are visually separable from the bulk cluster instead
   of only being identifiable via a percentile threshold in a script.
2. A **domain quadrant view**: Average Weighted S (x-axis) vs. RTM count
   (y-axis, log-scale given the 202-vs-3 spread) — this turns the
   Sum-vs-Average divergence in §1 into one glance instead of two separate
   charts a reader has to mentally cross-reference.

**Control.** If either of the above gets built, it should follow the same
"generated from live data, never hand-typed" rule as everything else in
this project — the PCA numbers above came from a one-off script
(`/tmp` working files, not yet saved as a named script), so if this
becomes a recurring view, it needs a proper `compute_pca.py` saved under a
discoverable name, same lesson already logged in the handover doc's gaps
section for other analyses.

## 5. Proposal: making the BT method more pervasive via a wide-but-shallow study, deepened by link/trigger

You asked for a way to "merge the maths and stats" so the BT method feels
more pervasive across the project — reaching more of the content without
requiring every single item to get the full 7-dimension deep-dive
treatment. This section is a **proposal**, not something built — it needs
a scoping decision before anything gets constructed, same as the other
structural asks earlier this session.

**The core idea:** most of the project's depth (the 7-dimension BT
scoring, PCA, cluster analysis) is currently applied to one population —
RTM requirements. A wide-but-shallow pass would apply the *same*
scoring/weighting language, even in simplified form, across every other
population in the project that doesn't currently get it — OFFER response
text, STANDARDS cross-references, DELIVERABLES items, NEGOTIATION_AGENDA
items — so the same 7-letter vocabulary (L/R/P/F/Q/LC/C) becomes the
common unit of measure everywhere in the project, not just in RTM_RANKING.
That's the "wide" part: broad coverage, lightweight per-item (maybe just a
1-7 flag for which dimension(s) an item primarily touches, not a full
weighted score).

**Depth by link, not by default.** Rather than deep-scoring everything
(expensive, and this session's own disclosure principle says don't fake
precision that isn't there), the proposal is to make depth *reachable*
rather than *default*: any lightly-tagged item that shares a dimension
profile, cluster, or domain with an already-deep-scored RTM gets a
"similar items" link — clicking through takes you from the shallow view
into the full 7-dimension analysis of its nearest deep-scored neighbors.
Concretely, this could reuse the PCA space from §2–3 directly: project a
lightly-tagged item's flags into the same PC1/PC2/PC3 space (even
approximately) and surface its nearest deep-scored RTM neighbors as "items
like this one already have full analysis — see: RTM-xxx, RTM-yyy." That
gives every corner of the project a foothold into the deep analysis
without requiring the deep analysis to be run everywhere first.

**What this would take, if picked up:** (1) a decision on which
additional populations get the lightweight tagging first — OFFER items
are the obvious first candidate since OFFER_RANKING already carries a
static BT rank with no dimension breakdown; (2) a similarity metric
(nearest-neighbor in PC space is the natural choice, already computed in
§2); (3) a UI decision — Navigator cross-links vs. a new dedicated
"similar items" panel. None of this is built. Flagging it here as a
concrete, scoped proposal rather than either building it speculatively or
leaving it as an abstract ask.

## 6. Data provenance

All numbers in this document came from live queries against
`QPS_OFFER_Evaluation_FULL_v19.xlsx` (`RTM_RANKING` for section/domain/7-
dimension raw scores, `DOMAIN_SUMMARY` for the cross-check on Sum/Average
by domain), computed this round via `numpy`/`scikit-learn` PCA — nothing
here is estimated or carried over from an earlier session. The PCA
component scores, dimension matrix, and per-RTM metadata used to produce
every table above are saved at `/tmp/pca_scores.npy`, `/tmp/pca_X.json`,
`/tmp/pca_meta.json` for this session only — not yet a permanent,
re-runnable script (see §4 Control note).
