# Knowledge Taxonomy Mapping — SKILL_user_ADD (00–10) against the QPS project

## What this document is

GBO proposed a general-purpose personal/organizational knowledge taxonomy
(`SKILL_user_ADD`, nodes 00 through 10) as an abstract framework — not
specific to this project. This document does one narrow thing: it maps each
of those eleven nodes onto what actually exists in the QPS OFFER Evaluation
project today, states plainly which nodes are already well covered by real
artifacts versus which are partial or missing, and stops there. It does
**not** attempt to design or build the general-purpose taxonomy itself —
that's a separate, much larger piece of work (a reusable framework meant to
apply across projects, not just this one) that would need its own scoping
conversation before anything gets built. Treat this as the honest starting
point for that later conversation, not a substitute for it.

The taxonomy as stated:

| # | Node | GBO's description |
|---|---|---|
| 00 | Content | — |
| 01 | Content Parsing | — |
| 02 | Memory / Knowledge Oracle (KO) | "the look-up user-facing DASHBOARD for a specific CORE TOPIC" |
| 03 | Knowledge Renditions | "interlinked output from same original and traceable SSOT (master index JSON...)" |
| 03.1–03.5 | Primary NODE Analyses (PNA) | Define / Measure / Analyze / Improve / Control (DMAIC sub-phases) |
| 04 | STATS | "DMAIC metric, iteration, waves (and improvement waves)" |
| 05 | GRAPHS + MATH + TRENDS | — |
| 06 | Interlinking | "+ Cross and interferences" |
| 07 | Status | "progress, completions, developmental phase, maturity" |
| 08 | Document Navigation | "TREE, Dashboard, Dependencies, versioning" |
| 09 | Coding Space Navigation | — |
| 10 | WIP | — |

(GBO's original list numbered both "Memory/KO" and "Knowledge Renditions" as
"02" — read here as 02 and 03 respectively, since Renditions is clearly a
distinct concept from Memory/KO and PNA is explicitly "03".)

## Node-by-node mapping

### 00 — Content — **covered**
The raw material everything else derives from: 722 RTM requirement rows, 50
OFFER item texts, contract section references. Lives in `RTM_CROSSWALK`,
`OFFER_CANONICAL`, and the (internal-only) `EVALUATION_INPUT` sheet. Nothing
missing here — this is the one node where "just have the source data" is
the whole requirement, and it's satisfied.

### 01 — Content Parsing — **covered**
The classification/extraction pipeline that turns raw content into
structured fields: `classify_all_rtms.py` (Requirement Type), `infer_clusters.py`
(C1–C8 cluster assignment), `t0_taxonomy.py` (T0 Gate classification),
`extract_content.py`. Every rule-derived field this pipeline produces is
tagged with its method/confidence directly on the sheet rather than
presented as equivalent to hand-reviewed data — that disclosure discipline
is effectively this node's design principle already in practice.

### 02 — Memory / Knowledge Oracle (KO) — **covered**
GBO's own definition — "the look-up user-facing DASHBOARD for a specific
CORE TOPIC" — maps almost exactly onto `RTM_LOOKUP` / `OFFER Lookup` (type
an ID, see every field for it in one place) and the Filter Dashboard
(`DASHBOARD_2`, pick a Domain/Cluster, get live counts). These are
literally "ask the system about one topic, get everything back," which is
the KO pattern by definition.

### 03 — Knowledge Renditions — **covered, arguably the project's central design principle**
"Interlinked output from same original and traceable SSOT" describes the
FULL → LITE → Navigator → PDF rendition chain exactly: one SSOT workbook,
multiple output renditions, each traceable back through
`SESSION_SSOT.yaml`'s `builder_chain` records and `export_nav_data.py`'s
JSON intermediate (never hand-typed, so no rendition can silently diverge
from the source). The Deliverables Index HTML built this round is itself a
new rendition of this same principle — an index of renditions, generated
from what's actually on disk rather than hand-maintained.

### 03.1–03.5 — Primary NODE Analyses (PNA): Define/Measure/Analyze/Improve/Control — **partial, genuine gap**
DMAIC content exists in the project — `DMAIC_AUDIT` sheet, the
`QPS_MTBF_WCS_DMAIC_v7.pptx` deck — but as a **separate track**, not as a
structured phase tag on individual RTM/OFFER/cluster rows. There is no
column today that says "this RTM is currently in the Analyze phase" or
"this cluster's DMAIC status is Improve." This is the same gap already
flagged in `SESSION_SSOT.yaml` under the still-open cluster-ranking/DMAIC
question — clusters deliberately don't rank today, and there's no per-item
DMAIC phase field to extend. Building this would mean either adding a
phase field to `RTM_RANKING`/`CLUSTERS` or deciding DMAIC phase genuinely
belongs at the cluster level only. Real gap, not yet scoped.

### 04 — STATS (DMAIC metric, iteration, waves) — **partial**
Point-in-time stats are strong: `DOMAIN_SUMMARY`, `QUALITY_CHECKS`, the
Navigator's Focus Score charts. What's missing is the "iteration/wave"
dimension GBO names explicitly — tracking a metric's value *across* build
versions (e.g., review-completion rate at v15 vs. v19, or how many T0 Gate
items were still unlinked at each round). `ARTIFACT_REGISTRY.json` now
tracks file-version history, but not metric-value history — nothing
currently snapshots "the numbers themselves" per version the way it
snapshots "the files themselves." Gap, not yet scoped.

### 05 — GRAPHS + MATH + TRENDS — **covered, most mature node**
This is the most built-out node in the whole taxonomy against this
project: Pareto charts with cumulative-% (additive-measure-aware, per the
`pareto_avgS_dot_suppression` decision), log-scale volume charts, 80:20
zoom, Domain×Cluster heatmaps (now purple-themed, two lenses), Focus Score
rankings by Domain/Category/Cluster, live weight-scenario toggle
(SUMPRODUCT/INDEX-driven, real RANK()). Nothing obviously missing here.

### 06 — Interlinking + Cross and interferences — **mostly covered, one real gap**
The "interlinking" half is well covered: `RTM_CROSSWALK`, the Domain×Cluster
heatmap, `CATEGORY_FOCUS`'s hidden-champion detection, and the new
DASHBOARD_2 crosswalk-coverage panel (293 linked / 429 not-linked, tier
breakdown, T0-Gate-specific unlinked-risk callout) — this last one was
built specifically in response to "what if the rest isn't covered by
OFFERS." The "cross and interferences" half — detecting when two
requirements *conflict* with each other, not just whether they're linked —
does not exist anywhere in the project. That's a materially different
capability (contradiction detection, not link-coverage) and a real gap.

### 07 — Status (progress, completions, phase, maturity) — **covered at item level, partial at project level**
Item-level status is solid: `QUALITY_CHECKS` (OPEN/CHECK/colour-coded),
`RTM_REVIEW_QUEUE`'s Disposition field, `SESSION_SSOT.yaml`'s own
done/pending/missing breakdown. What doesn't exist is a single rolled-up
"how far along is this evaluation, overall" number or view — e.g., no
single view says "68% of RTMs have a disposition decision" the way
DASHBOARD_2 now says "41% linked to an OFFER item." Partial — the pattern
already exists elsewhere in the project (DASHBOARD_2's coverage callout),
it just hasn't been applied to overall review-completion status yet.

### 08 — Document Navigation (TREE, Dashboard, Dependencies, versioning) — **covered**
`START_HERE`, `README`, the Navigator's own tab structure, the
(internal) `NAVIGATION_MAP` sheet, and now the Deliverables Index HTML
built this round (which is directly this node — a navigable index with
audience/purpose/version per artifact). Dependencies are captured in
`SESSION_SSOT.yaml`'s `builder_chain` records; versioning is captured in
`ARTIFACT_REGISTRY.json`'s family/version grouping. This node went from
partial to covered specifically as a result of this session's handover
work.

### 09 — Coding Space Navigation — **covered**
`ENGINEERING_HANDOVER_SESSION.md` §3 ("How to regenerate anything") plus
`ARTIFACT_REGISTRY.json` together answer "where is the script that builds
X, and what does it depend on." The known gap here isn't navigation, it's
completeness of what there is to navigate — see §5 of the handover doc
(BT-method deck v7/v8 and MTBF deck v7 have no saved build script, so
there's nothing to navigate *to* for those specific versions).

### 10 — WIP — **covered**
`SESSION_SSOT.yaml`'s `status.still_pending_this_session` /
`not_done_or_missing` / `open_standing_questions` sections are exactly
this node, kept as one parseable place rather than scattered across chat
history.

## Summary

| Node | Status |
|---|---|
| 00 Content | Covered |
| 01 Content Parsing | Covered |
| 02 Memory / KO | Covered |
| 03 Knowledge Renditions | Covered — central design principle |
| 03.1–03.5 PNA (DMAIC phases) | **Gap** — no per-item phase field |
| 04 STATS | Partial — no metric-value-over-version history |
| 05 GRAPHS+MATH+TRENDS | Covered — most mature node |
| 06 Interlinking | Mostly covered — no conflict/interference detection |
| 07 Status | Covered at item level, partial at project roll-up level |
| 08 Document Navigation | Covered (strengthened this session) |
| 09 Coding Space Navigation | Covered |
| 10 WIP | Covered |

Four real gaps, in priority order if this gets picked up next: (1) whether
DMAIC phase belongs on individual RTM rows or only at cluster level — this
is the same open question already logged against cluster-ranking; (2) a
project-level review-completion rollup, which is a small extension of a
pattern (DASHBOARD_2's coverage callout) that already exists; (3)
version-over-version metric history, which needs a decision on what gets
snapshotted and when; (4) requirement-conflict/interference detection,
which is the newest and least-scoped of the four — it isn't an extension
of anything already built, it would be new capability from scratch.

None of these four were picked in GBO's prioritization for this round — the
two selected items were this document and the Deliverables Index HTML
(delivered alongside this one). Building any of the four gaps above would
need the same kind of explicit scoping decision this session's earlier
sprawling-request triage called for, not a default guess.
