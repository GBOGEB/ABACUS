# QPS OFFER Evaluation — Artefact & Task Index

Generated this round in response to GBO's request for "a full conversation
TASK and SUBTASK list and files, artefacts, folders and local paths" and
"core index of artefacts." This is a snapshot, not a live document — the
authoritative machine-readable version is `ARTIFACT_REGISTRY.json`
(regenerate any time with `python3 generate_artifact_registry.py`, no
arguments, auto-scans the working directory).

## 1. Core deliverables — canonical (current) versions

These 5 are the files that matter; everything else in the working directory
is either a superseded version, a QA/scratch file, or a build script.

| Family | Canonical file | What it is |
|---|---|---|
| Master workbook | `QPS_OFFER_Evaluation_FULL_v23.xlsx` | The SSOT — 722 RTMs, 50 OFFER items, BT/weighted-S scoring, taxonomy, clusters, review queue, all audit sheets. Everything else derives from this file. |
| Reviewer workbook | `QPS_OFFER_Evaluation_LITE_v23.xlsx` | 23-sheet reviewer-shareable subset of FULL, kept in lockstep. |
| HTML Navigator | `QPS_RTM_BT_Navigator_v20.html` | Single-file browsable companion. **Stale relative to FULL_v23** — has not been re-exported since AD_07/08 were added; that's task #60. |
| BT methodology deck | `BT_Method_Evaluation_v11.pptx` | 24 slides — scoring method, PCA, robustness, Deliverables Dossier. |
| MTBF/DMAIC deck | `QPS_MTBF_WCS_DMAIC_v7.pptx` | Separate deck — reliability/MTBF story, DMAIC framing. **Exists, untouched this session** (not lost — this round's work has been on the workbook/BT-deck/Navigator triangle per your prioritisation). An earlier pre-DMAIC version (`QPS_MTBF_WCS.pptx`) also still exists on disk but is superseded. |

Supporting index/handover documents also present and current:
`SESSION_SSOT.yaml` (narrative build history + canonical pointers, hand-
maintained), `NEXT_ITERATION_BACKLOG.md` (26 sections, running log of
findings/fixes/open items), `ARTIFACT_REGISTRY.json` (machine-generated,
175 files / 76 families), `ENGINEERING_HANDOVER_SESSION.md`,
`KNOWLEDGE_TAXONOMY_MAPPING.md`, `PIPELINE_DIAGRAM.md`,
`SKILLS_INVENTORY.md`, `DELIVERABLES_INDEX.html`,
`MASTER_DEVELOPER_DASHBOARD.html`.

## 2. Development status (answers to the governance questions)

- **Git**: local-only, by your explicit earlier choice ("Local git only for
  now"). No GitHub remote configured in this session, no credentials given
  to or requested by this session. You pull/push to GitHub yourself. This
  is recorded in `SESSION_SSOT.yaml`'s `meta.git_repository` block.
- **CI/CD**: none — there is no pipeline. Every build is a manually-run
  Python script in this session, QA'd via LibreOffice-PDF render +
  Playwright before delivery.
- **Hosting**: none of this is hosted anywhere public. Files are delivered
  to you directly each round; the Navigator is a self-contained HTML file
  you open locally (or the desktop Cowork artifact copy, kept in sync via
  `update_artifact`).
- **Maturity**: workbook is on its 6th major round this session (v18→v23),
  Navigator on its 5th (v16→v20), BT deck on its 4th (v6/v9/v10/v11). Each
  round has been additive/append-only where possible (deck slide codes,
  Navigator sections) specifically to avoid renumbering breaks.

## 3. Folders and local paths

**This session's working directory** (cloud sandbox, not your machine):
`/home/claude/work/` — every file above lives here.

**Your machine** (reached via the device bridge this round):
`C:\Users\gbonthuy\OneDrive - Studiecentrum voor Kernenergie\Master_Input\`
— your general shared working folder (confirmed it's broad-purpose: `.git`,
`.github`, `.vscode`, unrelated projects live there too, not just AD docs).
5 files were staged from it into this session so far:
`AD_07 - QPS Cybersecurity Policy Framework.docx`, `AD_07_1_QPS_FULL.pdf`,
`AD_08_Abnormal_Scenarios_Full.docx`, `AD_08_Share_v2.pdf`,
`Figure_9_1_8_HEAT_LOAD_DATA_EQUATIONS.svg`. A broader scan found ~30+ more
real vector figures (P&ID diagrams, heat-load/enthalpy figures) and larger
zips (`PID_SVG_A3_LAYERED_OUTPUT.zip` 83MB, `AD_08_iteration_package_v3.zip`
10.6MB) sitting in the same folder — **not yet opened or processed**; that
full-folder scan/index was explicitly deferred pending your confirmation
(you prioritised items 1/2/3 over the broad scan when asked).

## 4. Task list — this session

Completed this round (chronological, most recent first):
58. PCA-clustered Pareto analysis for the P1 cutoff
57. DELIVERABLES_DOSSIER updated with AD_07/AD_08, RTM cross-ref re-scanned
56. AD_07/AD_08 documents + SVG figure staged from Master_Input
55. Subsystems domain drill-down (202 RTMs, 45 real sub-groups) built
54. Phase coverage visual (L0-L6 active / PAC-Warranty-FAC out of scope)
53. Files delivered, backlog updated, AD source-folder question asked
52. Nav data regenerated, Navigator re-spliced, LITE rebuilt, Playwright QA
51. AD relevance/importance slide added to BT deck
50. AD Deliverables Dossier hierarchy/tree view built
49. Real STATUS/Compliance legend colours, Taxonomy tab led with it
48. DOMAIN_SUMMARY chart data-range bug fixed

Open, in progress or queued:
- **#59 (in progress)**: Deck updates — Base/Equal/Cost=70% weight-scenario
  slide(s) with message banner; granular OFFER/RTM/Deliverable/Code&Standard
  /Lifecycle slide using the new AD_07/08 data; EVAL-S09 toggle-metric idea
  (needs honest framing — true interactive toggling isn't native to static
  PPTX, likely resolved as either multiple static slides or moved to the
  Navigator where toggle patterns already exist).
- **#60 (pending)**: Re-export Navigator against FULL_v23, rebuild/verify
  LITE_v23 is wired in, Playwright QA, commit, deliver.
- **Deferred pending your confirmation**: broad Master_Input folder
  scan/index by size/date + git-repo discovery (your prioritisation put
  this after items 1/2/3, not instead of them); "bicycle chart" for
  OFFER↔RTM links (terminology needs a quick clarification before
  building); indexing/rewriting all `.txt` files in Master_Input.

Older backlog items (#21-47 range) predate this round's AD/PCA/taxonomy
work and mix completed, superseded, and genuinely-still-open entries (e.g.
#30 "Build HTML navigator companion" reads as pending in the raw task list
but is long done — the Navigator is on v20). That list has drifted from
reality over many rounds and is due a cleanup pass rather than trusted
as-is; `NEXT_ITERATION_BACKLOG.md`'s 26 dated sections are the more
reliable record of what actually happened when.

## 5. This round's two remaining honest-assessment items

**"Broad/contextual" relation type (44 rows)**: all 44 trace to exactly
ONE OFFER item — OFFER-13 ("Main Equipment Technical Specifications") —
fanning out across 7 RTM Categories (General Requirements=12, WSH
Requirements=10, Helium Inventory Management=6, Compressors=5, External
Helium Withdrawal/Recovery=5, WSH Configuration=3, Liquid Nitrogen
Storage=3). Legitimate many-to-one pattern, not a classification bug — but
worth knowing the whole bucket is one source document, not a diverse
category.

**PCA-clustered Pareto (task #58)**: clustering the 722 RTMs in 7-dimension
PC-space (KMeans, k=5 by silhouette) finds real, coherent groups — but
they're requirement-TYPE clusters (Reliability-dominant, Cost-dominant,
Quality-dominant, etc.), not importance-tier clusters. The highest-scoring
cluster spans rank 10 to 561, only 36% overlapping a flat top-105 slice —
so this does not produce a cleaner P1 cutoff than what was already found:
either an 80%-of-importance line (rank ~490) or keeping the administrative
top-36 honestly relabelled as a workload cutoff. It IS a useful new lens
(route reviewers by requirement type) — logged as candidate content for
task #59, not yet built into any deliverable.
