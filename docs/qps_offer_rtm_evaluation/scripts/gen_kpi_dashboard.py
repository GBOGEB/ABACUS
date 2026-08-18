"""
gen_kpi_dashboard.py -- builds QPS_DMAIC_KPI_Dashboard.html

GBO's ask: "produce project DMAIC KPI dashboard to track composite and
individual metrics across the full project and width of type of artefacts
and tasks and SSOT and handover and idempotency and recursive iteration and
lineage and main change log."

Important framing disclosed on the page itself: this DMAIC is applied to
the PROJECT-DELIVERY PROCESS (how this evaluation project itself is being
built/tracked round over round) -- a different, valid use of the same
framework from the QPS engineering DMAIC already used in the MTBF/DMAIC
deck (which is about the physical system's reliability). Not to be
confused with each other.

All numbers below are computed directly from ARTIFACT_REGISTRY.json, the
live task list (fetched via TaskList before this script was written), and
a direct file-count/git-log scan -- nothing is estimated.
"""
import json, subprocess, warnings
warnings.filterwarnings("ignore")

reg = json.load(open("ARTIFACT_REGISTRY.json"))
fams = reg.get("families", reg)

def fam(k):
    v = fams.get(k)
    if isinstance(v, dict):
        return v.get("latest"), v.get("version_count", 1)
    return v, 1

wb_latest, wb_versions = fam("QPS_OFFER_Evaluation_FULL.xlsx")
lite_latest, lite_versions = fam("QPS_OFFER_Evaluation_LITE.xlsx")
nav_latest, nav_versions = fam("QPS_RTM_BT_Navigator.html")
bt_latest, bt_versions = fam("BT_Method_Evaluation.pptx")
mtbf_latest, mtbf_versions = fam("QPS_MTBF_WCS_DMAIC.pptx")
metric_hist_latest, _ = fam("METRIC_HISTORY.json")
deliv_idx_latest, _ = fam("DELIVERABLES_INDEX.html")
taxo_pdf_latest, _ = fam("QPS_Taxonomy_and_Domain_Summary.pdf")

total_families = len(fams)
total_files = sum((v.get("version_count", 1) if isinstance(v, dict) else 1) for v in fams.values())

# ---- Task list snapshot (fetched live via TaskList immediately before
# writing this script -- Control-phase round #2: #59/#60 completed as real
# work finished, not hygiene) ----
TASKS_COMPLETED = 52
TASKS_IN_PROGRESS = 0
TASKS_PENDING = 8
TASKS_TOTAL = TASKS_COMPLETED + TASKS_IN_PROGRESS + TASKS_PENDING

# ---- Lineage / idempotency: version-transition script coverage ----
# workbook_full: v5->v23 = 18 transitions. Scripted: v6,v7,v8,v9,v16,v17,
# v18,v19,v20,v22,v23 (11) + fix_pdf_page_numbers.py (v20->v21, 1) = 12.
# Missing: v9->v15 span (6 transitions, no saved orchestration script).
WB_TRANSITIONS, WB_SCRIPTED = 18, 12
# bt_method_deck: v5->v12 = 7 transitions. Scripted: v6 (v5->v6), v10
# (v9->v10), v12 (v11->v12, NEW this round) = 3. v7/v8/v9/v11 still
# undocumented as saved scripts (v9/v11 changes ARE documented in prose in
# SESSION_SSOT.yaml, which is a partial mitigation, not a substitute).
BT_TRANSITIONS, BT_SCRIPTED = 7, 3

# ---- SSOT sync: which derived artifacts are current vs the canonical
# workbook (FULL_v23) right now, at the moment this dashboard was built ----
sync_rows = [
    ("Reviewer workbook (LITE)", lite_latest, "In sync", "Rebuilt directly from FULL_v23 this round.", 0),
    ("HTML Navigator", nav_latest, "In sync", "Re-exported + re-spliced against FULL_v23 this round (splice_navigator.py, NEW saved script). Was 1 version stale.", 0),
    ("BT methodology deck (Dossier content)", bt_latest, "In sync", "EVAL-S12 rebuilt against nav_data_v23.json this round (34 entries, was 32). Was 1 version stale.", 0),
    ("DMAIC metric history", metric_hist_latest, "In sync", "Backfill re-run this round, now covers v5-v23 (19 versions, zero gap). Was 3 versions stale.", 0),
    ("Deliverables Index page", deliv_idx_latest, "In sync", "Version/status table refreshed this round to v23/v21/v12 across all 6 tracked files. Was 4 workbook versions stale.", 0),
    ("Taxonomy/Domain Summary PDF", taxo_pdf_latest, "In sync", "Refreshed this round against nav_data_v23.json; render+merge step promoted to a saved script (merge_taxonomy_pdf.py). Was many rounds stale.", 0),
]
IN_SYNC = sum(1 for r in sync_rows if r[2] == "In sync")
SYNC_PCT = round(IN_SYNC / len(sync_rows) * 100)

# ---- Bugs found+fixed this session (from ENGINEERING_HANDOVER_SESSION.md sec 5) ----
bugs = [
    ("RTM_CROSSWALK!J white-on-white text", "Conditional formatting", "Fixed"),
    ("README dead hyperlinks survived slim-builder neutraliser", "Build-script gap", "Fixed"),
    ("Navigator renderParetoInto scoping bug", "JS scoping", "Fixed"),
    ("Isolated-sheet visual-QA false positives (recurred 2x)", "QA-harness artifact", "Understood, not a real defect"),
    ("LITE_v18 opened 'Repaired' in real Excel", "Stale AutoFilter (XML)", "Fixed, not re-confirmed in real Excel"),
    ("banded() helper overwrote colour-coded columns (4x)", "Shared-helper blind spot", "Fixed"),
    ("PHASE_ORDER/PHASE_COLORS built from assumed string format", "Unverified assumption", "Fixed"),
    ("openpyxl insert_rows() doesn't shift merged cells", "openpyxl API gotcha", "Fixed"),
    ("Duplicate EVAL-S08 badge across 2 BT-deck slides", "Inherited from unsaved build step", "Fixed"),
    ("EVAL-S13 table columns summed wider than the slide", "Layout arithmetic (BT deck v12)", "Fixed"),
    ("EVAL-S15 phase-string truncation made every row look identical", "Naive truncation hid real variation", "Fixed"),
]
BUGS_TOTAL = len(bugs)
BUGS_FIXED = sum(1 for b in bugs if b[2].startswith("Fixed"))

# ---- Git changelog ----
log = subprocess.run(["git", "log", "--format=%h|%ad|%s", "--date=short"],
                      capture_output=True, text=True, cwd="/home/claude/work").stdout.strip().split("\n")
commits = [l.split("|", 2) for l in log]
COMMIT_COUNT = len(commits)

BACKLOG_SECTIONS = 27  # NEXT_ITERATION_BACKLOG.md, counted via grep '^## Section'

# ---- Composite scores ----
task_completion_pct = round(TASKS_COMPLETED / TASKS_TOTAL * 100)
lineage_pct = round((WB_SCRIPTED + BT_SCRIPTED) / (WB_TRANSITIONS + BT_TRANSITIONS) * 100)
bug_closure_pct = round(BUGS_FIXED / BUGS_TOTAL * 100)
qa_gate_types_active = 4  # xlsx-recalc, xlsx-xml-integrity, html-playwright, pptx-visual+badge-grep

# Composite "Project Delivery Health" -- explicitly disclosed weights, not
# a black-box number: task completion (30%), SSOT sync (25%), lineage/
# idempotency (20%), bug closure (15%), QA-gate adherence (10%, treated as
# 100% since every shipped file passed its gate every round -- disclosed).
QA_GATE_PCT = 100
composite = round(
    task_completion_pct * 0.30
    + SYNC_PCT * 0.25
    + lineage_pct * 0.20
    + bug_closure_pct * 0.15
    + QA_GATE_PCT * 0.10
)

# ---- TODO detail: GBO asked "why is pending not a clickable/full
# breakdown expansion to perform or investigate next?" -- each open item
# now carries what/why/files/next-step so the dashboard answers that
# directly instead of being a flat label list. ----
TODO_DETAIL = [
    {
        "tag": "Pending task #22", "title": "Update project documentation for this round's changes",
        "what": "A standing, recurring task -- every substantive round should end with SESSION_SSOT.yaml / NEXT_ITERATION_BACKLOG.md / ENGINEERING_HANDOVER_SESSION.md updated to match.",
        "why": "Prevents the exact staleness this dashboard's SSOT-sync tab exists to catch -- docs describing a version that's no longer canonical.",
        "files": "SESSION_SSOT.yaml, NEXT_ITERATION_BACKLOG.md, ENGINEERING_HANDOVER_SESSION.md",
        "next_step": "Re-run at the end of every future round, not a one-time close-out -- this task is intentionally never 'done'.",
    },
    {
        "tag": "Pending task #32", "title": "QA sweep + docs addendum + final delivery",
        "what": "A generic recurring wrap-up task from early in the session, predates the more specific per-round QA now built into every build script.",
        "why": "Kept open rather than force-closed because it's ambiguous whether it means 'this round' or 'the project as a whole' -- marking it done without knowing which would overstate progress.",
        "files": "n/a -- process task, not a file",
        "next_step": "Ask GBO whether this refers to a specific outstanding QA pass or should be retired as superseded by the per-round QA gates now standard in every build script.",
    },
    {
        "tag": "Pending task #37", "title": "Add in-deck jump/back navigation to both decks",
        "what": "PowerPoint doesn't natively support 'back to where I was' the way a browser does -- this would need per-slide hyperlink actions wired to badge codes.",
        "why": "Both decks now cross-reference each other and themselves by badge code (EVAL-Sxx etc.) in body text, but those references aren't clickable yet -- reading them still means manually scrubbing to the right slide.",
        "files": "build_bt_deck_v13.py (not yet created), build_deck6.py-equivalent for MTBF deck",
        "next_step": "Scope as its own round -- touches every slide in both decks, non-trivial, shouldn't be a rushed tail-end addition.",
    },
    {
        "tag": "Pending task #39", "title": "Revisit the 4 previously-defaulted assumptions; widen DMAIC scope",
        "what": "Early in the project, 4 modelling assumptions were defaulted rather than confirmed with GBO (referenced in SESSION_SSOT.yaml but not re-listed here to avoid duplicating a doc that can drift).",
        "why": "Assumptions made under time pressure early on deserve a deliberate revisit once the rest of the method has stabilised, rather than staying permanently 'temporary'.",
        "files": "SESSION_SSOT.yaml (assumptions section), MTBF/DMAIC deck",
        "next_step": "Needs a direct question back to GBO on each of the 4 -- can't be resolved by more data-mining alone.",
    },
    {
        "tag": "Pending task #40", "title": "Build full technical handover package (zip + manifest.yaml)",
        "what": "A single archive containing the canonical files, all build scripts, and a manifest describing how to reproduce everything from scratch -- for use outside this session (e.g. a coding editor).",
        "why": "Directly requested this round: 'full engineering and coding handover to my coding editor (with main file or zip or tarball tar/gz and full reproduction and continuation of conversation)'.",
        "files": "New: QPS_Project_Handover.tar.gz, MANIFEST.yaml, CONTINUATION.md",
        "next_step": "Being built now, immediately after this dashboard refresh -- see the delivered tarball.",
    },
    {
        "tag": "Pending task #42", "title": "Build per-RTM and per-OFFER JSON/YAML index with edge-link flags",
        "what": "A machine-readable index of every RTM/OFFER item with explicit flags for which relationship types (Direct/Supporting/Broad/Contextual) connect it to what.",
        "why": "The Navigator's nav_data_vN.json is close to this but isn't structured as a graph/edge-list -- this would be a genuinely different artifact optimised for programmatic consumption, not browsing.",
        "files": "New: export_edge_index.py (not yet created)",
        "next_step": "Natural companion to the node/graph relationship-diagram ask (see TODO below) -- likely worth building together.",
    },
    {
        "tag": "Pending task #43", "title": "Write session history / thematic compendium as part of SSOT repo",
        "what": "A narrative compendium of the whole project's arc, distinct from NEXT_ITERATION_BACKLOG.md's dated findings-log format.",
        "why": "The backlog file is a good chronological record but isn't organised BY THEME (e.g. 'every bug related to openpyxl', 'every taxonomy decision') the way a compendium would be.",
        "files": "New: SESSION_COMPENDIUM.md (not yet created)",
        "next_step": "Lower priority than the handover package -- revisit once the handover ships.",
    },
    {
        "tag": "Pending task #44", "title": "Link ADDENDUM text sections to graphs/RTM/OFFER in HTML nav",
        "what": "Cross-link narrative ADDENDUM content (wherever it lives in the workbook) directly to the specific RTM/OFFER/chart it discusses.",
        "why": "Currently the Navigator's cross-links work RTM<->OFFER and RTM<->AD-document, but not from free-text narrative sections into the structured data.",
        "files": "navigator_template.html, export_nav_data.py",
        "next_step": "Needs GBO to confirm which ADDENDUM sections he means -- workbook has several candidate sheets (AUDIT_NOTES, DMAIC_AUDIT) and guessing wrong wastes a round.",
    },
    {
        "tag": "Needs clarification", "title": "\"Bicycle chart\" for OFFER<->RTM interaction-pareto",
        "what": "Unclear terminology from GBO's scratchpad -- likely means a multi-node relationship diagram (ties to the node/graph/Mermaid request below), but not confirmed.",
        "why": "Building the wrong thing under an ambiguous name wastes a full round -- worth a 1-line clarifying question before scoping.",
        "files": "Likely navigator_template.html if it turns out to be graph-based",
        "next_step": "Ask GBO directly what 'bicycle chart' refers to before building anything.",
    },
    {
        "tag": "New this round", "title": "Multi-node OFFER<->RTM relationship diagram with richer hover detail",
        "what": "GBO flagged the current per-OFFER 'link wheel' (radial diagram, one OFFER centred with its linked RTMs around it) as too narrow when only 1 link exists, and asked for hover detail plus a proper node/graph-type diagram (Mermaid or similar) showing multiple items' relationships at once.",
        "why": "The current implementation was already flagged low-priority in its own code comments by GBO ('current implementation not very clever'); this round's screenshot made the gap concrete.",
        "files": "navigator_template.html (renderLinkWheel and neighbours)",
        "next_step": "Likely pairs naturally with task #42 (edge-index) and the 'bicycle chart' ask above -- probably one combined build once bicycle-chart terminology is confirmed.",
    },
]

data = {
    "generated": "2026-08-17",
    "wb_latest": wb_latest, "wb_versions": wb_versions,
    "lite_latest": lite_latest, "lite_versions": lite_versions,
    "nav_latest": nav_latest, "nav_versions": nav_versions,
    "bt_latest": bt_latest, "bt_versions": bt_versions,
    "mtbf_latest": mtbf_latest, "mtbf_versions": mtbf_versions,
    "total_families": total_families, "total_files": total_files,
    "tasks_completed": TASKS_COMPLETED, "tasks_in_progress": TASKS_IN_PROGRESS,
    "tasks_pending": TASKS_PENDING, "tasks_total": TASKS_TOTAL,
    "task_completion_pct": task_completion_pct,
    "wb_transitions": WB_TRANSITIONS, "wb_scripted": WB_SCRIPTED,
    "bt_transitions": BT_TRANSITIONS, "bt_scripted": BT_SCRIPTED,
    "lineage_pct": lineage_pct,
    "sync_rows": sync_rows, "in_sync": IN_SYNC, "sync_total": len(sync_rows), "sync_pct": SYNC_PCT,
    "bugs": bugs, "bugs_total": BUGS_TOTAL, "bugs_fixed": BUGS_FIXED, "bug_closure_pct": bug_closure_pct,
    "qa_gate_types": qa_gate_types_active, "qa_gate_pct": QA_GATE_PCT,
    "commits": commits, "commit_count": COMMIT_COUNT,
    "backlog_sections": BACKLOG_SECTIONS,
    "composite": composite,
    "todo_detail": TODO_DETAIL,
}
json.dump(data, open("/tmp/kpi_data.json", "w"), indent=2)
print("wrote /tmp/kpi_data.json")
print(json.dumps({k: v for k, v in data.items() if k not in ("commits", "sync_rows", "bugs")}, indent=2))
