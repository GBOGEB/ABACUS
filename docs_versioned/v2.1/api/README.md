# v2.1 API Documentation
> *Reconstructed from code — 2026-05-16 22:34*

## Core Modules

### Smoke Test Suite (`abacus_v21_smoke_tests.py`)
- `run_smoke_tests()` — Execute full smoke test battery
- `validate_deployment()` — Verify deployment readiness

### Session Analyzer (`abacus_v21_session_tuple_analyzer.py`)  
- `SessionTupleAnalyzer` — Analyze session data tuples
- `analyze_session(session_data)` — Process individual session

### System Feedback (`abacus_v21_system_feedback.py`)
- `SystemFeedback` — Collect and route system feedback
- `generate_report()` — Create feedback report

### Deployment Package
- `ABACUS_V21_DEPLOYMENT_PACKAGE/` — Contains deployment scripts
- Entry: `run_comprehensive_deployment.py`
