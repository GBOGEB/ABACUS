#!/bin/bash
# DMAIC V3 Generators - Test Script (Bash)
# Version: 3.1.0
# Last Updated: 2025-11-10

set -e  # Exit on error

echo "================================================================================"
echo "DMAIC V3 GENERATORS - REAL EXECUTION TEST (BASH)"
echo "================================================================================"
echo "Version: 3.1.0"
echo "DMAIC Version: V3"
echo "Integration Mode: BIDIRECTIONAL"
echo "================================================================================"
echo ""

# Step 1: Check Python version
echo "Step 1: Checking Python version..."
python --version
echo ""

# Step 2: Create virtual environment
echo "Step 2: Creating virtual environment..."
if [ -d "venv_dmaic_v3" ]; then
    echo "  Virtual environment already exists. Removing..."
    rm -rf venv_dmaic_v3
fi
python -m venv venv_dmaic_v3
echo "  ✓ Virtual environment created"
echo ""

# Step 3: Activate virtual environment
echo "Step 3: Activating virtual environment..."
source venv_dmaic_v3/Scripts/activate || source venv_dmaic_v3/bin/activate
echo "  ✓ Virtual environment activated"
echo ""

# Step 4: Install requirements
echo "Step 4: Installing requirements..."
pip install --upgrade pip
pip install -r DMAIC_V3/generators/requirements.txt
echo "  ✓ Requirements installed"
echo ""

# Step 5: Run execution tracker
echo "Step 5: Running execution tracker..."
python -m DMAIC_V3.generators execute --root master_document_system --timeout 30
echo ""

# Step 6: Run documentation aligner
echo "Step 6: Running documentation aligner..."
python -m DMAIC_V3.generators align-docs --docs-dir master_document_system
echo ""

# Step 7: Check victory conditions
echo "Step 7: Checking victory conditions..."
python -m DMAIC_V3.generators version
echo ""

# Step 8: Deactivate virtual environment
echo "Step 8: Deactivating virtual environment..."
deactivate
echo "  ✓ Virtual environment deactivated"
echo ""

echo "================================================================================"
echo "TEST COMPLETE"
echo "================================================================================"
echo "Check output/execution_reports/ for detailed results"
echo "================================================================================"
