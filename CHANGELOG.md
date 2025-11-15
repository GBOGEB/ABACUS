
# CHANGELOG

## 2025-11-12 — Bridge Layer additions (v0.1.0)

- task_runner/runner.py: TaskRunner with planning loader, export_mapping, DAG execution, idempotency records. (v0.1.0)
- planning_matrix.json: sample canonical planning entries (v0.1.0)
- tests/test_edge_missing_input.py: pytest starter template for missing/partial input scenario. (v0.1.0)
- .github/workflows/dmaic-ci.yml: minimal CI workflow for export-mapping, smoke runs, and optional tests (v0.1.0)
- glob.yaml: minimal machine-readable handover manifest (v0.1.0)

Notes: No test data included. Handover recipient must supply TEST_DATA_DIR or curated workspace snapshots.
