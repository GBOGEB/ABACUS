# v2.1 API Documentation
> *Reconstructed from code — 2026-05-16 22:34*

## Core Modules

### Smoke Test Suite (`abacus_v21_smoke_tests.py`)
- `ABACUSv21SmokeTests` — Smoke test runner class
- `run_all_tests()` — Execute full smoke test battery

### Session Analyzer (`abacus_v21_session_tuple_analyzer.py`)  
- `SessionTupleAnalyzer` — Analyze session data tuples
- `analyze_session()` — Process session artifacts from workspace

### System Feedback (`abacus_v21_system_feedback.py`)
- `SystemFeedbackGenerator` — Collect and route system feedback
- `generate_feedback_report()` — Create system feedback report

### Deployment Package
- `ABACUS_V21_DEPLOYMENT_PACKAGE/` — Contains deployment scripts
- Entry: `run_comprehensive_deployment.py`
