#!/usr/bin/env bash
# ===========================================================================
# make.sh — regenerate ALL derived outputs from tracked source.
#
# Derived outputs (output_v6/, data/model/, data/pemo/, publish/,
# reports/*.xlsx) are git-ignored. A reviewer clones the repo, runs this
# script, and reproduces every number quoted in the reports.
#
# Tracked source inputs: src/, segmentation/data/*.json, configs/, data/svg/
#
# Usage:   ./make.sh            # full regeneration
#          ./make.sh --clean    # wipe derived outputs first, then regenerate
#
# Requirements: python3 (stdlib) + cairosvg + openpyxl
# ===========================================================================
set -euo pipefail

cd "$(dirname "$0")"
export PYTHONPATH=src

run() {
  echo ""
  echo ">>> $*"
  "$@"
}

if [[ "${1:-}" == "--clean" ]]; then
  echo ">>> --clean: removing derived outputs"
  rm -rf output_v6 data/model data/pemo publish
  rm -f reports/COMPONENT_CATALOG.xlsx
fi

# Sanity check: source SVGs must be present (W001 ingest precondition).
svg_count=$(find data/svg -maxdepth 1 -name '*.svg' 2>/dev/null | wc -l | tr -d ' ')
if [[ "$svg_count" -lt 2 ]]; then
  echo "ERROR: expected >= 2 source SVGs in data/svg/, found $svg_count." >&2
  echo "       Cannot regenerate. Restore data/svg/QCELL.svg and RFCELL.svg." >&2
  exit 1
fi
echo ">>> found $svg_count source SVG(s) in data/svg/"

# ---------------------------------------------------------------------------
# 1. W001/W002 — colour-line model (must run FIRST; later phases read it)
# ---------------------------------------------------------------------------
run python3 src/abacus_svg_pid/cli.py

# ---------------------------------------------------------------------------
# 2. W003/W004 — layer hierarchy + geometry/arrow tracing + PEMO
# ---------------------------------------------------------------------------
run python3 -m abacus_svg_pid.build_w003_w004

# ---------------------------------------------------------------------------
# 3. Component catalog (XLSX + HTML) — reads segmentation + data/model
# ---------------------------------------------------------------------------
run python3 -m abacus_svg_pid.build_catalog

# ---------------------------------------------------------------------------
# 3b. W005 — Tag & instrument register reconciliation (reads the catalog above)
#     Cross-references the as-drawn catalog against the design nomenclature XLSX.
# ---------------------------------------------------------------------------
run python3 -m abacus_svg_pid.build_w005

# ---------------------------------------------------------------------------
# 3c. W006 — Design <-> As-Drawn tag cross-map (reads the W005 registers above)
#     Builds a confidence-scored bidirectional map between the design register
#     (circuit-sequential) and the as-drawn catalog (SVG-instance) tags.
# ---------------------------------------------------------------------------
run python3 -m abacus_svg_pid.build_w006_crossmap

# ---------------------------------------------------------------------------
# 4. Layered atlas v6 (per-source 13-layer SVG/PDF + HTML)
# ---------------------------------------------------------------------------
run python3 -m abacus_svg_pid.build_atlas_v6

# ---------------------------------------------------------------------------
# 5. Colour-line collage (W002 publish deliverable)
# ---------------------------------------------------------------------------
run python3 src/abacus_svg_pid/render_collage.py

# ---------------------------------------------------------------------------
# 6. Interactive cross-map viewer (W008 -- FULL interactive viewer)
#    Depends on the W006 crossmap (step 3c), the W006 statistics report and
#    the QCELL/RFCELL atlas SVGs (step 4). Emits a single self-contained
#    offline HTML with tag->SVG highlighting, triage, export and compare views.
# ---------------------------------------------------------------------------
run python3 -m abacus_svg_pid.build_viewer

echo ""
echo "=========================================================================="
echo " Regeneration complete. Derived outputs written to:"
echo "   data/model/   data/pemo/   data/excel/   output_v6/   publish/   reports/*.xlsx"
echo " Run the tests to validate (standalone runners, no pytest required):"
echo "   PYTHONPATH=src python3 tests/test_integration_pipeline.py"
echo "=========================================================================="
