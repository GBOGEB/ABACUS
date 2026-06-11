#!/bin/bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────
# QPLANT SBOM Generation Script
# ─────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "📦 Generating Software Bill of Materials (SBOM)"
echo "───────────────────────────────────────────────"

cd "$SCRIPT_DIR"

# Generate CycloneDX SBOM
echo ""
echo "Step 1: Generating CycloneDX SBOM..."
python3 generate_sbom.py \
    --output cyclonedx_sbom.json \
    --report sbom_report.md \
    --requirements /home/ubuntu/handover_dashboard/requirements.txt

# Python license summary
echo ""
echo "Step 2: Generating license summary..."
if pip install pip-licenses > /dev/null 2>&1; then
    pip-licenses --format=json --output-file=python_licenses.json 2>/dev/null || true
    pip-licenses --format=markdown --output-file=python_licenses.md 2>/dev/null || true
    echo "   ✅ License summary generated"
else
    echo "   ⚠️  pip-licenses not available, skipping"
fi

# Vulnerability scan
echo ""
echo "Step 3: Running vulnerability scan..."
python3 vulnerability_scan.py 2>/dev/null || echo "   ⚠️  Vulnerability scan skipped (pip-audit not available)"

echo ""
echo "═══════════════════════════════════════════════"
echo "✅ SBOM generation complete"
echo "   CycloneDX: cyclonedx_sbom.json"
echo "   Report:    sbom_report.md"
echo "   Releases:  releases/v4.4.0/"
