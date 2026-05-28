from __future__ import annotations

import json
import shutil
from pathlib import Path

from build_handover import build_handover
from generate_dashboard import generate_dashboard
from manifest import build_output_manifest, write_json_if_changed, write_text_if_changed

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ASSETS = ROOT / "assets"
DOCS_ASSETS = DOCS / "assets"
OUTPUTS = ROOT / "outputs"
MANIFESTS = OUTPUTS / "manifests"
DATA = ROOT / "data"

BUILDER_VERSION = "2.0.0"


def _copy_assets() -> None:
    DOCS_ASSETS.mkdir(parents=True, exist_ok=True)
    for name in ["style.css", "triage.js"]:
        src = ASSETS / name
        dst = DOCS_ASSETS / name
        write_text_if_changed(dst, src.read_text(encoding="utf-8"))


def _build_error_log(summary: dict[str, float]) -> None:
    old_wrong = "Previous baseline multiplied by CONTRACTUAL_ALIGNMENT_FACTOR=1000"
    text = f"""# ERROR_LOG

## Critical error fixed (OUTPUT_1_BASELINE rebuild)

### Error description
- Prior engine applied an undocumented multiplication factor of 1000 in leak-rate to mass conversion.
- This inflated results by ~3 orders of magnitude and led to unrealistic single-valve losses.

### Root cause
- `src/calculations/engineering.py` used `CONTRACTUAL_ALIGNMENT_FACTOR = 1000`.
- The factor was presented as contractual alignment instead of a physics-based transformation.

### Corrective action
- Replaced engine with first-principles conversion in `src/calc_leak_rate.py`.
- Removed all alignment factors.
- Added dimensional proof and tests.

### Validation snapshot
- Single valve 1e-8 mbar·L/s @300K,1bar: {summary['single_valve_1e8_300k_1bar_g_year']:.6f} g/year
- Baseline 410-valve scenario: {summary['baseline_total_kg_year']:.3f} kg/year
- RTM-048 cap reference (1 Nm³/day): {summary['rtm048_cap_kg_year']:.2f} kg/year

### Preventive controls
- Unit tests for dimensional consistency and expected ranges.
- Idempotent deterministic build (`python src/build_all.py`).
- Output hashes tracked in `OUTPUT_MANIFEST.json`.

### Legacy note
- Legacy path retained for audit: {old_wrong}
"""
    write_text_if_changed(ROOT / "ERROR_LOG.md", text)


def _build_readme() -> None:
    readme = """# Cryogenic Leak-Rate Dashboard (Fixed Baseline)

This repository rebuilds `OUTPUT_1_BASELINE` with corrected leak-rate physics and a full triage output system.

## Build
```bash
python src/build_all.py
```

## Output structure
- `docs/`: GitHub Pages-ready HTML views + `handover.pdf`
- `source/`: markdown source pack
- `data/`: classified input objects
- `outputs/tables`: generated CSV/JSON evidence tables
- `OUTPUT_MANIFEST.json`: deterministic output registry with hashes

## Audience views
- `docs/executive_summary.html` (manager)
- `docs/dashboard.html` (engineer)
- `docs/calculations.html` (specialist)
- `docs/rtm_traceability.html` (specialist / QA)
- `docs/handover.html` + `docs/handover.pdf` (formal handover)
"""
    write_text_if_changed(ROOT / "README.md", readme)


def _build_changelog() -> None:
    content = """# CHANGELOG

## 2.0.0
- Fixed critical leak-rate conversion error (removed non-physical x1000 factor).
- Added first-principles dimensional proof and worked examples.
- Implemented multi-format triage package (HTML/MD/PDF/JSON).
- Added status badges, collapsible sections, mode switching, print CSS.
- Added deterministic build orchestration and output manifest hashing.
- Added unit and integration tests for math and output completeness.
"""
    write_text_if_changed(ROOT / "CHANGELOG.md", content)


def _collect_classifications() -> dict[str, dict[str, str]]:
    classifications: dict[str, dict[str, str]] = {}
    mapping = {
        "docs/executive_summary.html": {"purpose": "decision summary", "audience": "manager", "density": "low"},
        "docs/dashboard.html": {"purpose": "interactive evidence", "audience": "engineer", "density": "medium"},
        "docs/calculations.html": {"purpose": "formula proof", "audience": "specialist", "density": "high"},
        "docs/rtm_traceability.html": {"purpose": "requirement mapping", "audience": "specialist", "density": "high"},
        "docs/handover.html": {"purpose": "handover dossier", "audience": "manager", "density": "medium"},
        "docs/handover.pdf": {"purpose": "formal export", "audience": "manager", "density": "medium"},
    }
    classifications.update(mapping)
    return classifications


def run() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    MANIFESTS.mkdir(parents=True, exist_ok=True)

    if DOCS.exists():
        shutil.rmtree(DOCS)
    DOCS.mkdir(parents=True, exist_ok=True)

    summary = generate_dashboard()
    _copy_assets()
    build_handover(summary)

    docs_source = DOCS / "source"
    docs_source.mkdir(parents=True, exist_ok=True)
    for md_name in ["handover.md", "assumptions.md", "developer_notes.md", "rtm_traceability.md"]:
        src_md = ROOT / "source" / md_name
        if src_md.exists():
            write_text_if_changed(docs_source / md_name, src_md.read_text(encoding="utf-8"))

    _build_error_log(summary)
    _build_readme()
    _build_changelog()

    source_inputs = [
        "data/leak_classes.json",
        "data/valve_candidates.json",
        "data/scenarios.json",
        "data/source_anchors.json",
        "src/calc_leak_rate.py",
        "src/generate_dashboard.py",
        "src/build_handover.py",
    ]

    tracked = [p for p in ROOT.rglob("*") if p.is_file() and not any(part.startswith(".git") for part in p.parts)]
    tracked = [p for p in tracked if "__pycache__" not in str(p)]

    manifest = build_output_manifest(
        root=ROOT,
        files=tracked,
        source_inputs=source_inputs,
        classifications=_collect_classifications(),
        builder_version=BUILDER_VERSION,
    )

    write_json_if_changed(ROOT / "OUTPUT_MANIFEST.json", manifest)
    write_json_if_changed(MANIFESTS / "latest_manifest.json", manifest)

    # compatibility alias requested by deliverable
    write_text_if_changed(DOCS / "handover_link.txt", "Open handover.html or handover.pdf in docs/.\n")


if __name__ == "__main__":
    run()
    print(json.dumps({"status": "ok", "builder_version": BUILDER_VERSION}, indent=2))
