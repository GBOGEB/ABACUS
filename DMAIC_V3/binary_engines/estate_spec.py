"""Single source of truth for the binary-estate engines: types, lanes, DAG, capabilities (generic, in code)
and roots, epics, routing, private markers, pilots (site-specific, from configuration).

Every other script imports from here; nothing is redefined elsewhere.
Code and data are separate: this folder holds code and the neutral example files only. Every output goes under
ESTATE_HOME (environment; default ~/.binary_estate), which must be outside the repository.
Configuration: ESTATE_CONFIG (environment) if set, else estate_config.yaml in ESTATE_HOME (private, never public),
else estate_config.example.yaml (neutral, ships with the code).
Generic engine and K-<TYPE>-NN definitions are NOT owned here: the engine catalogue and the private registry named in
the configuration (bound_external) own them; this file binds files to them and records what they do not cover yet.
"""

from __future__ import annotations

import os
from pathlib import Path as _P

import yaml as _yaml

SCHEMA = "gbogeb.master_input.binary_estate/0.3"

CODE_DIR = (
    _P(__file__).resolve().parent
)  # engines and neutral example files; never written to
ESTATE = _P(
    os.path.expanduser(os.environ.get("ESTATE_HOME") or "~/.binary_estate")
).resolve()  # data home
_REPO = CODE_DIR.parents[1]
if ESTATE == _REPO or _REPO in ESTATE.parents:
    raise RuntimeError(
        f"ESTATE_HOME ({ESTATE}) is inside the repository ({_REPO}); outputs name private files, "
        "so point ESTATE_HOME at a folder outside the repository"
    )


def _load_config() -> tuple[dict, _P]:
    for cand in (
        os.environ.get("ESTATE_CONFIG"),
        ESTATE / "estate_config.yaml",
        CODE_DIR / "estate_config.example.yaml",
    ):
        if cand and _P(cand).exists():
            return _yaml.safe_load(_P(cand).read_text("utf-8")) or {}, _P(cand)
    raise FileNotFoundError(
        "no estate configuration: set ESTATE_CONFIG or add estate_config.yaml"
    )


CONFIG, CONFIG_PATH = _load_config()
CONFIG_IS_EXAMPLE = CONFIG_PATH.name.endswith(".example.yaml")


def legend_registry() -> _P | None:
    """Owner-accepted legend rules (style -> meaning): ESTATE_LEGEND_REGISTRY if set, else LEGEND_REGISTRY.yaml in
    ESTATE_HOME. None = no accepted rules, so an edge without an in-drawing legend stays DEFER. The template
    LEGEND_REGISTRY.example.yaml next to this file is never read as rules."""
    p = os.environ.get("ESTATE_LEGEND_REGISTRY")
    cand = _P(p) if p else ESTATE / "LEGEND_REGISTRY.yaml"
    return cand if cand.exists() else None


def _root_path(p: str) -> _P:
    return _P(os.path.expanduser(p.replace("{estate_parent}", str(ESTATE.parent))))


# Roots scanned with the SAME engines; depth diminishes per extra folder (full > standard > light).
ROOTS = {
    rid: (_root_path(r["path"]), r.get("depth", "standard"))
    for rid, r in (CONFIG.get("roots") or {}).items()
}
ROOTS["SMOKE"] = (
    ESTATE / "fixtures" / "smoke_root",
    "full",
)  # smoke fixture (built by the tests); never aggregated into engines
REAL_ROOTS = [r for r in ROOTS if r != "SMOKE"]
DEPTH = {  # what each depth level runs
    "full": {"hash_max_bytes": None, "probe": True, "move_plan": True},
    "standard": {"hash_max_bytes": 200_000_000, "probe": True, "move_plan": True},
    "light": {"hash_max_bytes": 200_000_000, "probe": False, "move_plan": True},
}


def inv_dir(root_id: str) -> _P:
    return (
        ESTATE / "inventory"
        if root_id == "MI"
        else ESTATE / "roots" / root_id / "inventory"
    )


# ---------------------------------------------------------------- types (A..K)
# letter, code, extensions, catalogue type (None = not yet in ENGINE_CATALOG -> extension proposal)
TYPES = [
    ("A", "DOCX", (".docx", ".doc", ".dotx"), "DOCX"),
    ("B", "XLSX", (".xlsx", ".xlsm", ".xls", ".csv"), "XLSX"),
    ("C", "PPTX", (".pptx", ".pptm", ".ppt", ".potx"), "PPTX"),
    ("D", "PDF", (".pdf", ".xps"), "PDF"),
    ("E", "HTML", (".html", ".htm"), "HTML"),
    ("F", "TXT", (".txt", ".log"), None),
    (
        "G",
        "MD",
        (".md",),
        None,
    ),  # letter G was unused in the request; MD is the largest human-facing group
    ("H", "VSDX", (".vsdx", ".vsd", ".drawio", ".mmd"), None),
    ("I", "PNG", (".png", ".jpg", ".jpeg", ".jfif", ".gif"), None),
    ("J", "SVG", (".svg",), "SVG"),
    ("K", "ZIP", (".zip", ".gz", ".tar", ".7z", ".bundle"), None),
]
EXT_TO_TYPE = {e: code for _, code, exts, _ in TYPES for e in exts}
TYPE_LETTER = {code: letter for letter, code, _, _ in TYPES}

# ---------------------------------------------------------------- epics (from configuration)
# Scored on filename tokens; highest score wins, ties go to the earlier epic. repo = the repo the epic converges on.
EPICS = [
    (
        e["id"],
        e.get("repo"),
        {str(k).upper(): int(v) for k, v in (e.get("keywords") or {}).items()},
    )
    for e in CONFIG.get("epics") or []
]
EPIC_SHORT = {e["id"]: e.get("short", e["id"]) for e in CONFIG.get("epics") or []}
PRIVATE_EPICS = {e["id"] for e in CONFIG.get("epics") or [] if e.get("private")}
_oe = CONFIG.get("other_epic") or {"id": "E0_OTHER"}
OTHER_EPIC = (_oe["id"], None)
EPIC_SHORT[_oe["id"]] = _oe.get("short", _oe["id"])
# Personal/admin documents: never routed to a repo; target is the git-excluded _personal/ folder.
PERSONAL_TOKENS = {str(t).upper() for t in CONFIG.get("personal_tokens") or []}
BOUND = CONFIG.get("bound_external") or {}
PRIVATE_LADDER = CONFIG.get("private_ladder") or {}

# ---------------------------------------------------------------- capabilities (per TYPE.gg_Engine)
# status: now = an installed engine can do it on this PC; planned = defined, not built; na = not applicable.
CAPABILITIES = [
    "READ",
    "WRITE",
    "PATCH",
    "SCAN",
    "GREP",
    "LINT",
    "PARSE",
    "SLICE",
    "SEMANTIC_SECTIONS",
    "OUTLINE_LEVELS",
    "BULLET_LEVELS",
    "NUMBER_LEVELS",
    "FONTS",
    "COLOURS",
    "SIZE",
    "TEXT_BOXES",
    "SHAPES_GRAPH",
    "DEBUG",
    "QA_K",
]

# ---------------------------------------------------------------- lanes (one per major core function)
LANES = [
    (
        "L1_INTAKE",
        "Discover, identify (bytes vs extension), hash, dedupe, lock/open detection",
    ),
    (
        "L2_READ_PARSE",
        "Open read-only, parse package parts, slice into pages/slides/sheets/sections",
    ),
    (
        "L3_EXTRACT",
        "Outline/levels, bullets/numbering, fonts/colours/sizes, text boxes, shapes->graph",
    ),
    (
        "L4_SEMANTIC",
        "Sectional/semantic breakdown, golden-thread links to RTM/lanes/repos, staleness",
    ),
    (
        "L5_WRITE_PATCH",
        "Build, patch, repair copies (never overwrite pinned originals)",
    ),
    ("L6_QA_RELEASE", "K-ladder checks, receipts, release to OG5 repo or archive"),
]

# ---------------------------------------------------------------- engine DAG (E0..E9; S0..S9 is the hub DevOps census)
DAG = [
    ("E0_DISCOVER", [], "L1_INTAKE"),
    ("E1_IDENTIFY", ["E0_DISCOVER"], "L1_INTAKE"),
    ("E2_CLASSIFY", ["E1_IDENTIFY"], "L1_INTAKE"),
    ("E3_PARSE", ["E2_CLASSIFY"], "L2_READ_PARSE"),
    ("E4_EXTRACT", ["E3_PARSE"], "L3_EXTRACT"),
    ("E5_SEMANTIC", ["E4_EXTRACT"], "L4_SEMANTIC"),
    ("E6_DECIDE", ["E5_SEMANTIC", "E2_CLASSIFY"], "L4_SEMANTIC"),
    ("E7_WRITE_PATCH", ["E6_DECIDE"], "L5_WRITE_PATCH"),
    ("E8_QA", ["E7_WRITE_PATCH", "E4_EXTRACT"], "L6_QA_RELEASE"),
    ("E9_RECEIPT_RELEASE", ["E8_QA"], "L6_QA_RELEASE"),
]

# decision outcomes at E6
DECISIONS = [
    "KEEP_CANONICAL",
    "REWORK",
    "SUPERSEDED",
    "STALE_ARCHIVE",
    "DUPLICATE",
    "ACTIVATE_ZIP",
    "PARK",
]

OG5 = list(CONFIG.get("og5") or [])
