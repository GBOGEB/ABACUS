"""
build_handover_package.py -- GBO: "I still need a full engineering and
coding handover to my coding editor (with main file or zip or tarball
tar/gz and full reproduction and continuation of conversation)".

Curates a coding-editor-ready package, NOT a raw dump of the working
directory: the working dir has 175+ files including ~20 superseded
workbook versions, scratch/QA files (final*.pptx, step*.pptx, qa_*.xlsx),
and a 175MB local git history -- none of that helps someone opening this
in an editor, it just bloats the download. What actually matters for
reproduction is: (1) every CURRENT canonical file, (2) every build script
(the actual reproducible pipeline), (3) every doc that explains intent,
decisions, and status, (4) a manifest tying it together, (5) a
continuation guide for picking this up cold.

Usage: python3 build_handover_package.py
Output: QPS_Project_Handover_<date>.tar.gz in the working directory.
"""
import os, shutil, tarfile, json, warnings
warnings.filterwarnings("ignore")

WORKDIR = "/home/claude/work"
STAGE = "/tmp/handover_stage"
DATE = "2026-08-17"
ARCHIVE_NAME = f"QPS_Project_Handover_{DATE}.tar.gz"

if os.path.exists(STAGE):
    shutil.rmtree(STAGE)
os.makedirs(STAGE)

# ============================================================ 1. current/ -- canonical deliverables
CURRENT_FILES = [
    "QPS_OFFER_Evaluation_FULL_v23.xlsx",
    "QPS_OFFER_Evaluation_LITE_v23.xlsx",
    "QPS_RTM_BT_Navigator_v21.html",
    "BT_Method_Evaluation_v12.pptx",
    "QPS_MTBF_WCS_DMAIC_v7.pptx",
    "QPS_Taxonomy_and_Domain_Summary.pdf",
    "DELIVERABLES_INDEX.html",
    "MASTER_DEVELOPER_DASHBOARD.html",
    "QPS_DMAIC_KPI_Dashboard.html",
    "METRIC_HISTORY.json",
    "ARTIFACT_REGISTRY.json",
]
os.makedirs(f"{STAGE}/current", exist_ok=True)
missing = []
for f in CURRENT_FILES:
    src = f"{WORKDIR}/{f}"
    if os.path.exists(src):
        shutil.copy2(src, f"{STAGE}/current/{f}")
    else:
        missing.append(f)
print(f"current/: {len(CURRENT_FILES) - len(missing)}/{len(CURRENT_FILES)} copied", f"(missing: {missing})" if missing else "")

# ============================================================ 2. scripts/ -- every build/utility script
os.makedirs(f"{STAGE}/scripts", exist_ok=True)
py_files = sorted(f for f in os.listdir(WORKDIR) if f.endswith(".py"))
for f in py_files:
    shutil.copy2(f"{WORKDIR}/{f}", f"{STAGE}/scripts/{f}")
# non-.py dependency: splice_navigator.py's default template arg
TEMPLATE_DEPS = ["navigator_template.html"]
for f in TEMPLATE_DEPS:
    src = f"{WORKDIR}/{f}"
    if os.path.exists(src):
        shutil.copy2(src, f"{STAGE}/scripts/{f}")
        py_files.append(f)
print(f"scripts/: {len(py_files)} files copied (Python scripts + {len(TEMPLATE_DEPS)} template dependency)")

# ============================================================ 3. docs/ -- narrative, decisions, status
DOC_FILES = [
    "SESSION_SSOT.yaml",
    "NEXT_ITERATION_BACKLOG.md",
    "ENGINEERING_HANDOVER_SESSION.md",
    "SESSION_ARTEFACT_AND_TASK_INDEX.md",
    "KNOWLEDGE_TAXONOMY_MAPPING.md",
    "PIPELINE_DIAGRAM.md",
    "SKILLS_INVENTORY.md",
    "DMAIC_BT_TECHNICAL_REPORT.md",
    "PCA_DMAIC_BT_ANALYSIS.md",
    "DMAIC_update_changelog.md",
    "presenter_narrative_notes.md",
    "content.yaml",
    "style.yaml",
    "README_v5.md",
]
os.makedirs(f"{STAGE}/docs", exist_ok=True)
missing_docs = []
for f in DOC_FILES:
    src = f"{WORKDIR}/{f}"
    if os.path.exists(src):
        shutil.copy2(src, f"{STAGE}/docs/{f}")
    else:
        missing_docs.append(f)
print(f"docs/: {len(DOC_FILES) - len(missing_docs)}/{len(DOC_FILES)} copied", f"(missing: {missing_docs})" if missing_docs else "")

# ============================================================ 4. git_history.txt -- full commit log w/ stats
import subprocess
log = subprocess.run(["git", "log", "--stat", "--date=iso"], capture_output=True, text=True, cwd=WORKDIR).stdout
open(f"{STAGE}/git_history.txt", "w").write(log)
print(f"git_history.txt: {len(log)} bytes ({log.count(chr(10)+'commit ')+1 if log else 0} commits, full stat log -- NOT the .git directory itself, which is 175MB of binary blobs from files no longer canonical and not useful in an editor. Ask if you want the actual .git history transferred separately.)")

# ============================================================ 5. MANIFEST.yaml
manifest = f"""# QPS OFFER Evaluation -- Handover Package Manifest
# Generated {DATE} for GBO's coding-editor handover request.
# This is a CURATED package, not a raw directory dump -- see CONTINUATION.md
# for why, and for what was deliberately left out.

package:
  name: QPS_Project_Handover_{DATE}
  project: "QPS OFFER Evaluation -- SCK CEN MYRRHA/QPS procurement evaluation"
  generated_by: build_handover_package.py

current/:
  description: "Every canonical deliverable, current as of this package's generation."
  files:
    - {{name: QPS_OFFER_Evaluation_FULL_v23.xlsx, role: "SSOT workbook -- 32 sheets, 722 RTMs x 50 OFFER items, 7-dim weighted BT scoring"}}
    - {{name: QPS_OFFER_Evaluation_LITE_v23.xlsx, role: "23-sheet reviewer trim of FULL, no internal audit/method sheets"}}
    - {{name: QPS_RTM_BT_Navigator_v21.html, role: "Self-contained read-only HTML browser, data spliced from FULL at build time"}}
    - {{name: BT_Method_Evaluation_v12.pptx, role: "27-slide BT scoring methodology deck"}}
    - {{name: QPS_MTBF_WCS_DMAIC_v7.pptx, role: "38-slide MTBF/reliability DMAIC deck -- separate lineage, separate subject"}}
    - {{name: QPS_Taxonomy_and_Domain_Summary.pdf, role: "5-page mixed-orientation print reference"}}
    - {{name: DELIVERABLES_INDEX.html, role: "One-page index of all outward-facing deliverables with audience/status"}}
    - {{name: MASTER_DEVELOPER_DASHBOARD.html, role: "5-tab developer landing page (content/status focused)"}}
    - {{name: QPS_DMAIC_KPI_Dashboard.html, role: "6-tab delivery-process metrics dashboard (this package's own kind of artefact)"}}
    - {{name: METRIC_HISTORY.json, role: "Version-over-version stats, v5 through v23, zero gap"}}
    - {{name: ARTIFACT_REGISTRY.json, role: "Auto-generated file inventory -- 175 files / 76 families as of this package"}}

scripts/:
  description: >
    Every Python build/utility script from the working directory ({len(py_files)}
    files). These are the actual reproducible pipeline -- SESSION_SSOT.yaml's
    builder_chain entries under docs/ tell you which script produced which
    canonical version and in what order. Known gaps (some intermediate
    versions have no saved script) are disclosed there too, not hidden.
  entry_points:
    - {{script: build_workbook_v23.py, produces: "QPS_OFFER_Evaluation_FULL_v23.xlsx from v22"}}
    - {{script: build_workbook_slim_v23.py, produces: "QPS_OFFER_Evaluation_LITE_v23.xlsx from FULL_v23"}}
    - {{script: export_nav_data.py, produces: "/tmp/nav_data_vN.json from any FULL_vN.xlsx (takes IN/OUT as argv)"}}
    - {{script: splice_navigator.py, produces: "QPS_RTM_BT_Navigator_vN.html from nav_data + navigator_template.html"}}
    - {{script: build_bt_deck_v12.py, produces: "BT_Method_Evaluation_v12.pptx from v11"}}
    - {{script: build_pdf_export.py, produces: "/tmp/print_taxonomy.html + /tmp/print_domain_summary.html from nav_data (takes path as argv)"}}
    - {{script: merge_taxonomy_pdf.py, produces: "QPS_Taxonomy_and_Domain_Summary.pdf from the two print_*.html files"}}
    - {{script: compute_metrics_snapshot.py, produces: "METRIC_HISTORY.json (--backfill scans every FULL_v*.xlsx on disk)"}}
    - {{script: generate_artifact_registry.py, produces: "ARTIFACT_REGISTRY.json (no args, auto-scans the working dir)"}}
    - {{script: gen_kpi_dashboard.py, produces: "/tmp/kpi_data.json (real numbers from registry/task-list/git log)"}}
    - {{script: build_kpi_dashboard_html.py, produces: "QPS_DMAIC_KPI_Dashboard.html from kpi_data.json"}}
    - {{script: pca_pareto_cluster.py, produces: "/tmp/pca_cluster_results.json -- standalone analysis, reads FULL_v23 directly"}}

docs/:
  description: "Everything explaining WHY, not just what -- read these before touching scripts/."
  read_order:
    - {{file: ENGINEERING_HANDOVER_SESSION.md, why: "START HERE. Full project intent, chronological progress, known bugs, honest gap-check."}}
    - {{file: SESSION_ARTEFACT_AND_TASK_INDEX.md, why: "Compact snapshot of every canonical file, folder, local path, and task."}}
    - {{file: SESSION_SSOT.yaml, why: "Machine-parseable canonical-version pointers + full builder_chain lineage + decisions_log."}}
    - {{file: NEXT_ITERATION_BACKLOG.md, why: "27 dated sections -- every finding, fix, and open question, in the order they happened."}}
    - {{file: KNOWLEDGE_TAXONOMY_MAPPING.md, why: "Maps GBO's own SKILL_user_ADD taxonomy onto real project artefacts."}}
    - {{file: PIPELINE_DIAGRAM.md, why: "ASCII pipeline diagram of the whole build chain."}}
    - {{file: DMAIC_BT_TECHNICAL_REPORT.md, why: "PCA + Sum-vs-Average divergence technical writeup."}}
    - {{file: PCA_DMAIC_BT_ANALYSIS.md, why: "Underlying PCA/DMAIC analysis this report is built from."}}
    - {{file: SKILLS_INVENTORY.md, why: "What Anthropic/user skills were available and used this session."}}
    - {{file: content.yaml, why: "Structured content extraction from the BT deck -- style/content separation experiment."}}
    - {{file: style.yaml, why: "Style schema paired with content.yaml."}}

git_history.txt:
  description: >
    Full `git log --stat` output (26 commits) -- NOT the .git directory
    itself. The actual .git history is ~175MB (accumulated binary blobs
    from ~20 superseded workbook/deck/Navigator versions plus scratch/QA
    files that were committed along the way) and isn't useful pasted into
    an editor -- this text log gives the full narrative and file-level
    diffs-by-name without the weight. If the real .git history is wanted
    (e.g. to `git log -p` a specific past version), ask and it can be
    packaged separately.

deliberately_excluded:
  - "~20 superseded workbook versions (FULL_v5 through v22, LITE_v5 through v22) -- current versions are in current/, full lineage documented in docs/SESSION_SSOT.yaml"
  - "~18 superseded Navigator versions (v2-v20) -- same reasoning"
  - "~6 superseded BT deck versions (v5-v11) -- same reasoning"
  - "Scratch/QA files (final*.pptx, step*.pptx, qa_*.xlsx, uploaded_*.pptx, test_grow.pptx, lite_start_here_qa.xlsx) -- these were intermediate working files, never deliverables"
  - "The raw .git directory (175MB) -- see git_history.txt note above"
"""
open(f"{STAGE}/MANIFEST.yaml", "w").write(manifest)
print(f"MANIFEST.yaml: {len(manifest)} bytes")

# ============================================================ 6. CONTINUATION.md
continuation = f"""# Continuation guide -- QPS OFFER Evaluation project

If you're picking this up cold, in a coding editor, with no memory of the
Claude session that built it: read this file first, then
`docs/ENGINEERING_HANDOVER_SESSION.md`, then decide what you actually need
to touch.

## What this project is

A contract-compliance evaluation system for a nuclear/physics infrastructure
procurement (SCK CEN, MYRRHA/QPS Quench Protection System). Two Applicants'
OFFER responses are scored against 722 RTM (Requirements Traceability
Matrix) contract requirements, using a 7-dimension weighted Bradley-Terry-
style ranking method: Safety/Legal (0.20), Reliability (0.22), Performance
(0.20), Functional (0.16), Quality/Verifiability (0.12), Lifecycle (0.07),
Cost (0.03) -- frozen contract weights, disclosed everywhere they're used.

Everything derives from ONE Excel workbook (`current/QPS_OFFER_Evaluation_FULL_v23.xlsx`).
Nothing else is hand-edited independently -- the reviewer workbook, the HTML
Navigator, and (partially) the presentation decks are all regenerated FROM
it by the scripts in `scripts/`.

## The one rule that matters most

**No duplicated SSOT, disclose rather than fabricate.** Every rule-derived
or inferred value on any sheet is tagged with its confidence/method right
there, not presented as equivalent to hand-reviewed data. If you extend
this project, keep that convention -- it's why the workbook can be trusted
at 722 rows instead of spot-checked.

## How to reproduce anything

```bash
pip install python-pptx openpyxl matplotlib pyyaml playwright numpy scikit-learn pypdf --break-system-packages

# Full rebuild chain (only run steps you actually need -- most work is
# additive on top of the current canonical files in current/)
python3 scripts/build_workbook_v23.py            # needs FULL_v22.xlsx as input (not included -- see docs/SESSION_SSOT.yaml builder_chain for the full version history if you need an older input)
python3 scripts/build_workbook_slim_v23.py        # FULL_v23 -> LITE_v23
python3 scripts/export_nav_data.py current/QPS_OFFER_Evaluation_FULL_v23.xlsx /tmp/nav_data_v23.json
python3 scripts/splice_navigator.py /tmp/nav_data_v23.json QPS_RTM_BT_Navigator_v21.html scripts/navigator_template.html
python3 scripts/build_pdf_export.py /tmp/nav_data_v23.json
python3 scripts/merge_taxonomy_pdf.py QPS_Taxonomy_and_Domain_Summary.pdf
python3 scripts/compute_metrics_snapshot.py --backfill
python3 scripts/generate_artifact_registry.py
```

Note: most `build_workbook_vNN.py` scripts take the PREVIOUS version as
input (`vNN-1 -> vNN`), not the original baseline -- this package only
includes the CURRENT (v23) workbook, not every intermediate version, so a
from-scratch rebuild of the full v5->v23 history isn't possible from this
package alone. If you need that, ask for the full working directory
(534MB) or the raw `.git` history instead.

## What's actually outstanding right now

Pulled directly from this session's own tracking, not re-guessed:

- **8 pending tasks** (see `docs/NEXT_ITERATION_BACKLOG.md` and
  `docs/SESSION_ARTEFACT_AND_TASK_INDEX.md` for full detail): recurring
  documentation upkeep, in-deck slide navigation, revisiting 4 early
  modelling assumptions with GBO, a per-RTM/OFFER JSON edge-index, a
  thematic session compendium, ADDENDUM-to-graph linking in the Navigator,
  and two open questions GBO has never directly answered (Aptos vs Carlito
  font preference; whether an old "repaired file" Excel warning still
  applies).
- **A requested but not-yet-built feature**: a multi-node OFFER<->RTM
  relationship diagram (Mermaid-style or similar) with richer hover detail
  -- the current Navigator only has a single-OFFER "link wheel," flagged
  as low-priority in its own code comments.
- **Terminology to clarify with GBO before building**: a "bicycle chart"
  for OFFER<->RTM interaction-Pareto -- likely related to the item above,
  not confirmed.

## If you're an AI agent continuing this in a fresh session

Read, in order: this file, `docs/ENGINEERING_HANDOVER_SESSION.md` (full
narrative + gap-check), `docs/SESSION_SSOT.yaml` (structured facts, parse
don't re-derive), `docs/NEXT_ITERATION_BACKLOG.md` (dated findings log).
Do not re-investigate things already answered in those three files -- e.g.
whether T0/Gate items dominate OFFER_RANKING's top rank (yes, by design,
see SESSION_SSOT.yaml decisions_log), or whether the MTBF deck is stale
(untouched but not broken, RTM citations spot-checked valid). Follow the
same QA convention before shipping anything: LibreOffice-PDF render +
direct page inspection for pptx/pdf, Playwright headless sweep (zero
console/page errors, zero horizontal overflow) for html, reload-and-verify
for xlsx after any structural edit (openpyxl has real gotchas -- see the
insert_rows()/merged-cells bug in ENGINEERING_HANDOVER_SESSION.md section 5
before doing any row insertion near a merged cell).
"""
open(f"{STAGE}/CONTINUATION.md", "w").write(continuation)
print(f"CONTINUATION.md: {len(continuation)} bytes")

# ============================================================ 7. tar it up
OUT_PATH = f"{WORKDIR}/{ARCHIVE_NAME}"
with tarfile.open(OUT_PATH, "w:gz") as tar:
    tar.add(STAGE, arcname="QPS_Project_Handover")

size_mb = os.path.getsize(OUT_PATH) / (1024 * 1024)
print(f"\nwrote {OUT_PATH} ({size_mb:.1f} MB)")
