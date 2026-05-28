#!/bin/bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────
# QPLANT — Run Visual Regression Tests
# ─────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
THRESHOLD="${1:-0.1}"

echo "🔍 Visual Regression Tests — QPLANT v4.4.0"
echo "   Threshold: ${THRESHOLD}%"
echo "───────────────────────────────────────────────"

# Ensure dependencies
pip install playwright Pillow numpy > /dev/null 2>&1
python -m playwright install chromium > /dev/null 2>&1

cd "$SCRIPT_DIR"

# Check baselines exist
if [ ! -d "baselines" ] || [ -z "$(ls baselines/*.png 2>/dev/null)" ]; then
    echo "⚠️  No baselines found. Creating baselines first..."
    python3 visual_tests.py --mode create-baseline --all
fi

# Run tests
python3 visual_tests.py --mode test --threshold "$THRESHOLD" --report html

echo ""
echo "✅ Visual regression tests complete"
echo "   Report: visual_regression_report.html"
