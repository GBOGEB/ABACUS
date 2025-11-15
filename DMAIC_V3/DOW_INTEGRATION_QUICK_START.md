# DOW Integration Quick Start Guide

**Version:** 1.0  
**Date:** 2025-01-15  
**Purpose:** Quick reference for executing DOW integration pipeline

---

## 🚀 Quick Start

### Prerequisites

```bash
# Ensure you're in the project root
cd /path/to/Master_Input

# Activate virtual environment (if using one)
# source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate     # Windows

# Verify Python version
python --version  # Should be 3.8+
```

### One-Command Execution

```bash
# Execute complete DOW integration pipeline for iteration 1
python DMAIC_V3/dow_integration_executor.py --iteration 1 --verbose
```

---

## 📋 Step-by-Step Execution

### Step 1: Verify Setup

```bash
# Check that all agent files exist
ls DMAIC_V3/local_mcp/agents/dow_*.py

# Expected output:
# dow_convergence_calculator.py
# dow_knowledge_extractor.py
# dow_metadata_injector.py
# dow_recursive_hooks_injector.py
```

### Step 2: Run Individual Agents (Optional)

```bash
# Stage 1: Metadata Injection
python DMAIC_V3/local_mcp/agents/dow_metadata_injector.py \
  --iteration 1 \
  --target DMAIC_CANONICAL_OUTPUT \
  --verbose

# Stage 2: Recursive Hooks Injection
python DMAIC_V3/local_mcp/agents/dow_recursive_hooks_injector.py \
  --iteration 1 \
  --target DMAIC_CANONICAL_OUTPUT \
  --verbose

# Stage 3: Convergence Calculation
python DMAIC_V3/local_mcp/agents/dow_convergence_calculator.py \
  --iteration 1 \
  --target DMAIC_CANONICAL_OUTPUT \
  --verbose

# Stage 4: Knowledge Extraction
python DMAIC_V3/local_mcp/agents/dow_knowledge_extractor.py \
  --target DMAIC_CANONICAL_OUTPUT \
  --verbose
```

### Step 3: Run Complete Pipeline

```bash
# Execute all stages in sequence
python DMAIC_V3/dow_integration_executor.py \
  --iteration 1 \
  --target DMAIC_CANONICAL_OUTPUT \
  --verbose
```

### Step 4: Verify Results

```bash
# Check that JSON files have DOW structure
python -c "
import json
from pathlib import Path

target = Path('DMAIC_CANONICAL_OUTPUT')
json_files = list(target.glob('*.json'))

for file in json_files:
    with open(file) as f:
        data = json.load(f)
    
    has_metadata = 'metadata' in data
    has_hooks = 'recursive_hooks' in data
    has_convergence = 'convergence_metrics' in data
    has_knowledge = 'knowledge_gain' in data
    
    status = '✅' if all([has_metadata, has_hooks, has_convergence, has_knowledge]) else '❌'
    print(f'{status} {file.name}')
"
```

---

## 🔄 Recursive Iteration Loop

### Manual Iteration Loop

```bash
# Iteration 0 (Baseline)
python DMAIC_V3/dow_integration_executor.py --iteration 0

# Iteration 1
python DMAIC_V3/dow_integration_executor.py --iteration 1

# Iteration 2
python DMAIC_V3/dow_integration_executor.py --iteration 2

# Continue until convergence...
```

### Automated Iteration Loop

```bash
# Run until convergence (max 10 iterations)
for i in {0..10}; do
  echo "Running iteration $i..."
  python DMAIC_V3/dow_integration_executor.py --iteration $i
  
  # Check convergence status
  if grep -q '"convergence_status": "converged"' DMAIC_CANONICAL_OUTPUT/*.json; then
    echo "✅ Convergence achieved at iteration $i"
    break
  fi
done
```

---

## 📊 Monitoring & Validation

### Check Pipeline Status

```bash
# View latest execution results
cat dow_integration_results_iteration_1.json | python -m json.tool

# Check ranking output
cat ranking.json | python -m json.tool

# View logs
tail -f logs/ranking.log
```

### Validate DOW Structure

```bash
# Run validation script
python -c "
import json
from pathlib import Path

def validate_dow_structure(file_path):
    with open(file_path) as f:
        data = json.load(f)
    
    checks = {
        'metadata': 'metadata' in data,
        'recursive_hooks': 'recursive_hooks' in data,
        'convergence_metrics': 'convergence_metrics' in data,
        'knowledge_gain': 'knowledge_gain' in data
    }
    
    return checks

target = Path('DMAIC_CANONICAL_OUTPUT')
for file in target.glob('*.json'):
    checks = validate_dow_structure(file)
    status = '✅' if all(checks.values()) else '❌'
    print(f'{status} {file.name}')
    for check, passed in checks.items():
        icon = '✅' if passed else '❌'
        print(f'  {icon} {check}')
"
```

---

## 🛠️ Troubleshooting

### Common Issues

#### Issue 1: Target directory not found

```bash
# Error: Target directory not found: DMAIC_CANONICAL_OUTPUT

# Solution: Create the directory
mkdir -p DMAIC_CANONICAL_OUTPUT

# Or use a different target
python DMAIC_V3/dow_integration_executor.py \
  --iteration 1 \
  --target DMAIC_V3_OUTPUT/iteration_1
```

#### Issue 2: No JSON files found

```bash
# Error: No JSON files found in DMAIC_CANONICAL_OUTPUT

# Solution: Run DMAIC pipeline first to generate outputs
python DMAIC_V3/temporal_phase_runner.py --iteration 1

# Then run DOW integration
python DMAIC_V3/dow_integration_executor.py --iteration 1
```

#### Issue 3: Agent script not found

```bash
# Error: Agent not found: DMAIC_V3/local_mcp/agents/dow_metadata_injector.py

# Solution: Verify agent files exist
ls DMAIC_V3/local_mcp/agents/dow_*.py

# If missing, re-create them from the execution plan
```

#### Issue 4: Permission denied

```bash
# Error: Permission denied

# Solution: Make scripts executable
chmod +x DMAIC_V3/dow_integration_executor.py
chmod +x DMAIC_V3/local_mcp/agents/dow_*.py
```

---

## 📈 Expected Output

### Successful Execution

```
================================================================================
DOW INTEGRATION PIPELINE - ITERATION 1
================================================================================

────────────────────────────────────────────────────────────────────────────────
STAGE 1: Metadata Injection
────────────────────────────────────────────────────────────────────────────────
🔄 Processing 6 JSON files...

✅ Metadata injection complete:
   Total: 6
   Success: 6
   Failed: 0

────────────────────────────────────────────────────────────────────────────────
STAGE 2: Recursive Hooks Injection
────────────────────────────────────────────────────────────────────────────────
🔄 Processing 6 JSON files...

✅ Recursive hooks injection complete:
   Total: 6
   Success: 6
   Failed: 0

────────────────────────────────────────────────────────────────────────────────
STAGE 3: Convergence Calculation
────────────────────────────────────────────────────────────────────────────────
🔄 Processing 6 JSON files...

✅ Convergence calculation complete:
   Total: 6
   Success: 6
   Failed: 0

────────────────────────────────────────────────────────────────────────────────
STAGE 4: Knowledge Extraction
────────────────────────────────────────────────────────────────────────────────
🔄 Processing 6 JSON files...

✅ Knowledge extraction complete:
   Total: 6
   Success: 6
   Failed: 0

────────────────────────────────────────────────────────────────────────────────
STAGE 5: Recursive Self-Ranking
────────────────────────────────────────────────────────────────────────────────
✅ Recursive self-ranking completed successfully

────────────────────────────────────────────────────────────────────────────────
STAGE 6: Validation
────────────────────────────────────────────────────────────────────────────────
✅ Validation completed successfully

================================================================================
PIPELINE EXECUTION SUMMARY
================================================================================

Total Stages: 6
✅ Success: 6
⚠️ Warning: 0
❌ Error: 0
⏭️ Skipped: 0

Stage Results:
  1. ✅ dow_metadata_injector: success
  2. ✅ dow_recursive_hooks_injector: success
  3. ✅ dow_convergence_calculator: success
  4. ✅ dow_knowledge_extractor: success
  5. ✅ recursive_self_ranking: success
  6. ✅ smoke_test: success

📄 Results saved to: dow_integration_results_iteration_1.json

🎉 DOW Integration Pipeline completed successfully!
```

---

## 🎯 Next Steps

After successful execution:

1. **Review Results**
   ```bash
   # Check DOW structure in JSON files
   cat DMAIC_CANONICAL_OUTPUT/phase1_define.json | python -m json.tool
   
   # Review ranking output
   cat ranking.json | python -m json.tool
   ```

2. **Run Next Iteration**
   ```bash
   python DMAIC_V3/dow_integration_executor.py --iteration 2
   ```

3. **Monitor Convergence**
   ```bash
   # Check convergence status
   grep -r "convergence_status" DMAIC_CANONICAL_OUTPUT/*.json
   ```

4. **Generate Reports**
   ```bash
   # Generate convergence report
   python DMAIC_V3/utils/generate_convergence_report.py
   ```

---

## 📚 Additional Resources

- **Full Execution Plan:** `DMAIC_V3/MCP_ALIGNED_DOW_INTEGRATION_EXECUTION_PLAN.md`
- **Orchestrator Config:** `orchestrator_config.yaml`
- **Ranking Config:** `ranking.yaml`
- **Agent Documentation:** `DMAIC_V3/local_mcp/agents/README.md`

---

## 🆘 Support

If you encounter issues:

1. Check logs: `logs/ranking.log`
2. Review execution results: `dow_integration_results_iteration_*.json`
3. Validate setup: Run individual agents with `--verbose` flag
4. Consult full documentation: `DMAIC_V3/MCP_ALIGNED_DOW_INTEGRATION_EXECUTION_PLAN.md`

---

**Status:** ✅ READY FOR EXECUTION  
**Last Updated:** 2025-01-15
