#!/bin/bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────
# QPLANT — Create Visual Regression Baselines
# ─────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "📸 Creating Visual Regression Baselines"
echo "───────────────────────────────────────────────"

# Ensure dependencies
pip install playwright Pillow numpy > /dev/null 2>&1
python -m playwright install chromium > /dev/null 2>&1

cd "$SCRIPT_DIR"
python3 visual_tests.py --mode create-baseline --all

echo ""
echo "✅ Baselines created in baselines/"
echo "   Manifest: baselines/manifest.json"
ls -la baselines/*.png 2>/dev/null | wc -l | xargs -I{} echo "   Total: {} screenshots"
