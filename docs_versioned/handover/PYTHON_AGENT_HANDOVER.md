# Python Coding Agent Handover


**Version:** 2.3.0  
**Generated:** 2025-11-08T19:22:20.318046+00:00  
## Critical Information for Python Agents

### Purpose
This package analyzes cryogenic refrigeration loads for a LINAC particle accelerator across multiple operational scenarios.

---

## Execution Checklist

### 1. Environment Setup
```bash
# Check Python version (3.8+ required)
python --version

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import openpyxl, pandas, matplotlib, numpy, yaml; print('OK')"
```

### 2. Pre-Flight Validation
```bash
# Run self-smoke test (REQUIRED before production)
python selfsmoke_test.py

# Expected output: All tests pass
```

### 3. Main Execution
```bash
# Run analysis
python cryo_analysis.py

# Generate human-readable report
python generate_report.py
```

---

## Unicode Handling (CRITICAL)

### The Problem
Original code contained Unicode symbols that break execution:
- → (arrow)
- ✓ (checkmark)
- ⚠ (warning)
- ❌ (cross)

### The Solution
**Dual-mode symbol system** via `symbol_manager.py`:

```python
# In code (ASCII mode)
from symbol_manager import symbols as S

print(f"{S.ARROW} Processing...")  # Uses ASCII internally
print(f"{S.CHECK} Complete")       # Uses ASCII internally

# Output (Unicode mode - for humans)
# → Processing...
# ✓ Complete
```

### How It Works
1. **Code execution**: Uses ASCII equivalents (`->`, `[OK]`, `[WARN]`, `[ERR]`)
2. **Terminal output**: Translates to Unicode if supported
3. **Report generation**: Always uses Unicode for readability

### Configuration
Edit `unicode_config.json` to customize:
```json
{
  "mode": "auto",
  "symbols": {
    "arrow": {"unicode": "→", "ascii": "->"},
    "check": {"unicode": "✓", "ascii": "[OK]"}
  }
}
```

---

## File Descriptions

### Core Python Files

#### `cryo_analysis.py` (Main Engine)
- **Purpose**: Load Excel data, calculate loads, generate plots
- **Pre-run**: NO (you must run it)
- **Dependencies**: openpyxl, pandas, matplotlib
- **Input**: Excel workbook (CRYO Heat Loads - LINAC calculator)
- **Output**: CSV files, PNG plots

#### `symbol_manager.py` (Unicode Handler)
- **Purpose**: Translate symbols between ASCII/Unicode
- **Pre-run**: NO (imported by other scripts)
- **Dependencies**: None (stdlib only)
- **Usage**: `from symbol_manager import symbols as S`

#### `selfsmoke_test.py` (Validation)
- **Purpose**: Pre-flight checks before production
- **Pre-run**: NO (you must run it first!)
- **Tests**:
  - File existence
  - Python dependencies
  - Unicode handling
  - Data integrity
  - Calculation accuracy

#### `generate_report.py` (Report Generator)
- **Purpose**: Create human-readable markdown/HTML reports
- **Pre-run**: NO (run after cryo_analysis.py)
- **Output**: `CRYO_ANALYSIS_REPORT.md`, `CRYO_ANALYSIS_REPORT.html`

#### `index_generator.py` (Documentation)
- **Purpose**: Generate INDEX_MASTER.md with cross-references
- **Pre-run**: NO (optional utility)

---

## Special Requirements

### Python Packages
```txt
openpyxl>=3.0.0      # Excel file handling
pandas>=1.3.0        # Data analysis
matplotlib>=3.4.0    # Plotting
numpy>=1.21.0        # Numerical operations
pyyaml>=5.4.0        # YAML parsing
colorama>=0.4.4      # Terminal colors (optional)
```

### System Requirements
- Python 3.8 or higher
- 500 MB free disk space
- Excel file access (read-only)

### Optional Enhancements
- `colorama` for colored terminal output
- `rich` for enhanced console formatting
- `pytest` for extended testing

---

## Execution Flow

```
1. selfsmoke_test.py
   ├─ Check environment
   ├─ Validate files
   └─ Test calculations

2. cryo_analysis.py
   ├─ Load Excel data
   ├─ Process scenarios
   ├─ Calculate loads
   ├─ Generate plots
   └─ Export CSV

3. generate_report.py
   ├─ Read analysis results
   ├─ Format for humans
   └─ Create MD/HTML
```

---

## Unicode Translation Examples

### In Code (ASCII)
```python
from symbol_manager import symbols as S

def process_scenario(name):
    print(f"{S.ARROW} Processing {name}")
    try:
        result = calculate_loads(name)
        print(f"{S.CHECK} Success: {result}")
    except Exception as e:
        print(f"{S.ERROR} Failed: {e}")
```

### Terminal Output (Unicode - Auto-detected)
```
→ Processing Baseline
✓ Success: 1234.5 W

→ Processing High-Power
✓ Success: 2345.6 W
```

### Report Output (Unicode - Always)
```markdown
## Results

✓ Baseline: 1234.5 W  
✓ High-Power: 2345.6 W  
⚠ Margin applied: 20%
```

### ASCII Fallback (If Unicode Not Supported)
```
-> Processing Baseline
[OK] Success: 1234.5 W

-> Processing High-Power
[OK] Success: 2345.6 W
```

---

## Error Handling

### Common Issues

#### 1. Unicode Errors
```python
# BAD (will break)
print("→ Processing")

# GOOD (will work)
from symbol_manager import symbols as S
print(f"{S.ARROW} Processing")
```

#### 2. Missing Dependencies
```bash
# Error: ModuleNotFoundError: No module named 'openpyxl'
# Fix:
pip install -r requirements.txt
```

#### 3. File Not Found
```python
# Error: FileNotFoundError: Excel file not found
# Fix: Ensure Excel file is in same directory or update path
```

---

## Integration with Other Tools

### Jupyter Notebooks
```python
# Cell 1: Setup
%pip install -r requirements.txt
from symbol_manager import symbols as S
import cryo_analysis as ca

# Cell 2: Run analysis
results = ca.run_analysis()

# Cell 3: Display
ca.plot_results(results)
```

### CI/CD Pipeline
```yaml
# .github/workflows/cryo-analysis.yml
name: CRYO Analysis
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: python selfsmoke_test.py
      - name: Run analysis
        run: python cryo_analysis.py
```

---

## Output Files

### Generated by cryo_analysis.py
- `scenario_summary.csv` - Tabular results
- `load_breakdown.png` - Stacked bar chart
- `scenario_comparison.png` - Comparison plot
- `margin_analysis.png` - Margin impact plot

### Generated by generate_report.py
- `CRYO_ANALYSIS_REPORT.md` - Markdown report
- `CRYO_ANALYSIS_REPORT.html` - HTML report (with embedded plots)

---

## Testing

### Run All Tests
```bash
python selfsmoke_test.py
```

### Expected Output
```
→ Running CRYO LINAC Self-Smoke Tests
→ Test 1/5: File existence... [OK]
→ Test 2/5: Dependencies... [OK]
→ Test 3/5: Unicode handling... [OK]
→ Test 4/5: Data integrity... [OK]
→ Test 5/5: Calculation accuracy... [OK]
✓ All tests passed!
```

---

## Troubleshooting

### Issue: Unicode characters in error messages
**Solution**: Ensure `symbol_manager.py` is imported at the top of every script

### Issue: Plots not displaying
**Solution**: Check matplotlib backend: `matplotlib.use('Agg')` for non-interactive

### Issue: Excel file locked
**Solution**: Close Excel before running Python scripts

---

## Summary for Python Agents

1. ✅ Install requirements: `pip install -r requirements.txt`
2. ✅ Run validation: `python selfsmoke_test.py`
3. ✅ Execute analysis: `python cryo_analysis.py`
4. ✅ Generate report: `python generate_report.py`
5. ✅ Use symbol_manager for all output

**No files are pre-run. You must execute them.**

**Unicode is handled automatically via symbol_manager.py**

---

**Version**: 3.0.0  
**Date**: 2025-11-08  
**Status**: Production Ready
