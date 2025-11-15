# DMAIC V3 Generators - Quick Reference

**Version**: 3.1.0 | **DMAIC**: V3 | **Integration**: BIDIRECTIONAL

---

## Commands

### Full Run (Execute + Align)
```bash
python -m DMAIC_V3.generators full-run --root . --docs-dir master_document_system
```

### Execute Code Only
```bash
python -m DMAIC_V3.generators execute --root . --timeout 30
```

### Align Documentation Only
```bash
python -m DMAIC_V3.generators align-docs --docs-dir master_document_system
```

### Version Information
```bash
python -m DMAIC_V3.generators version
```

---

## Victory Conditions

| # | Condition | Description |
|---|-----------|-------------|
| 1 | Python Execution | All Python files execute without errors |
| 2 | VBA Validation | All VBA files validate successfully |
| 3 | Statistics Tracking | Execution stats tracked per file |
| 4 | Error Classification | Error types classified and reported |
| 5 | Documentation Alignment | All markdown files version-aligned |
| 6 | Report Generation | JSON/YAML reports generated and linked |

**Current Status**: 5/6 met (83.3%)

---

## Generated Reports

### Execution Reports
- `output/execution_reports/execution_report.json`
- `output/execution_reports/execution_report.yaml`
- `output/execution_reports/EXECUTION_REPORT.md`

### Version Information
- `master_document_system/VERSION_INFO.json`
- `master_document_system/VERSION_INFO.yaml`

### Aligned Documentation
- `master_document_system/INTEGRATION_PLAN.md`
- `master_document_system/DEPLOYMENT_COMPLETE.md`
- `master_document_system/IMPLEMENTATION_SUMMARY.md`
- `master_document_system/README.md`

---

## Error Types Tracked

```python
ErrorType.SYNTAX_ERROR          # Python syntax errors
ErrorType.IMPORT_ERROR          # Missing imports/modules
ErrorType.RUNTIME_ERROR         # Runtime exceptions
ErrorType.TYPE_ERROR            # Type mismatches
ErrorType.VALUE_ERROR           # Invalid values
ErrorType.ATTRIBUTE_ERROR       # Missing attributes
ErrorType.NAME_ERROR            # Undefined names
ErrorType.FILE_NOT_FOUND        # Missing files
ErrorType.PERMISSION_ERROR      # Access denied
ErrorType.TIMEOUT_ERROR         # Execution timeout
ErrorType.VBA_SYNTAX_ERROR      # VBA syntax errors
ErrorType.VBA_VALIDATION_ERROR  # VBA validation errors
ErrorType.UNKNOWN_ERROR         # Unclassified errors
```

---

## Statistics Tracked

- Total files executed (Python + VBA)
- Success/failure rates
- Execution time per file
- Lines of code analyzed
- Functions and classes counted
- Error breakdown by type
- Victory condition status

---

## Integration Points

### 1. DMAIC V3 Engine (to be implemented)
```python
from DMAIC_V3.generators import DocumentGenerator
generator = DocumentGenerator(config)
generator.generate(output_formats=['docx', 'json'])
```

### 2. Recursive Engine (to be implemented)
```python
from DMAIC_V3.generators import ArtifactProcessor
processor = ArtifactProcessor(config)
processor.process_artifacts(artifacts)
```

### 3. Standalone CLI (✓ operational)
```bash
python -m DMAIC_V3.generators full-run
```

---

## Files Structure

```
DMAIC_V3/
└── generators/
    ├── __init__.py                          # Module initialization
    ├── __main__.py                          # CLI entry point
    ├── execution_tracker.py                 # Code execution & stats
    ├── documentation_aligner.py             # Doc version alignment
    ├── EXECUTION_FRAMEWORK_COMPLETE.md      # Full documentation
    └── QUICK_REFERENCE.md                   # This file

output/
└── execution_reports/
    ├── execution_report.json                # JSON report
    ├── execution_report.yaml                # YAML report
    └── EXECUTION_REPORT.md                  # Markdown report

master_document_system/
├── VERSION_INFO.json                        # Version info (JSON)
├── VERSION_INFO.yaml                        # Version info (YAML)
├── INTEGRATION_PLAN.md                      # Aligned docs
├── DEPLOYMENT_COMPLETE.md                   # Aligned docs
├── IMPLEMENTATION_SUMMARY.md                # Aligned docs
└── README.md                                # Aligned docs
```

---

## Next Steps

1. **Fix path resolution** in `execution_tracker.py`
2. **Implement DocumentGenerator** from `master_engine.py`
3. **Implement ArtifactProcessor** for 50K+ files
4. **Integrate with DMAIC V3 phases**
5. **Connect to recursive engine**

---

## Links

- [Full Documentation](./EXECUTION_FRAMEWORK_COMPLETE.md)
- [Execution Tracker](./execution_tracker.py)
- [Documentation Aligner](./documentation_aligner.py)
- [Integration Plan](../../master_document_system/INTEGRATION_PLAN.md)
- [Latest Execution Report](../../output/execution_reports/EXECUTION_REPORT.md)
