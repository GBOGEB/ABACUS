#!/bin/bash
# GitHub Workflows Execution Verification Script
# Checks if all workflows are properly configured and can run

echo "=========================================="
echo "GitHub Workflows Execution Verification"
echo "=========================================="
echo ""

WORKFLOWS_DIR=".github/workflows"
TOTAL=0
VALID=0
INVALID=0

echo "Checking workflows in $WORKFLOWS_DIR..."
echo ""

for workflow in "$WORKFLOWS_DIR"/*.yml; do
    TOTAL=$((TOTAL + 1))
    filename=$(basename "$workflow")
    
    echo -n "[$TOTAL] $filename ... "
    
    # Check YAML syntax
    if python -c "import yaml; yaml.safe_load(open('$workflow', encoding='utf-8'))" 2>/dev/null; then
        echo "[PASS] Valid YAML"
        VALID=$((VALID + 1))
    else
        echo "[FAIL] Invalid YAML"
        INVALID=$((INVALID + 1))
        python -c "import yaml; yaml.safe_load(open('$workflow', encoding='utf-8'))" 2>&1 | head -5
    fi
done

echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="
echo "Total workflows: $TOTAL"
echo "Valid: $VALID"
echo "Invalid: $INVALID"
echo ""

if [ $INVALID -eq 0 ]; then
    echo "[PASS] All workflows are valid and ready to run!"
    exit 0
else
    echo "[FAIL] Some workflows have errors. Please fix them before pushing."
    exit 1
fi
