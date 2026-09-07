#!/usr/bin/env bash
set -euo pipefail

REPORTS_DIR="${REPORTS_DIR:-test_reports}"
MODE="${1:-full}"

mkdir -p "${REPORTS_DIR}"

case "${MODE}" in
  smoke)
    echo "Running bootstrap bridge smoke tests"
    python -m pytest tests/test_integration_bootstrap_bridges.py -m smoke -v --tb=short
    ;;
  bootstrap)
    echo "Running bootstrap statistics tests"
    python -m pytest tests/test_bootstrap_eval.py -v --tb=short
    ;;
  bridges)
    echo "Running bootstrap bridge integration tests"
    python -m pytest tests/test_integration_bootstrap_bridges.py -v --tb=short
    ;;
  full)
    echo "Running bootstrap deployment validation suite"
    python -m pytest tests/test_bootstrap_eval.py tests/test_integration_bootstrap_bridges.py -v --tb=short
    python tests/bootstrap_bridge.py
    ;;
  *)
    echo "usage: $0 [smoke|bootstrap|bridges|full]" >&2
    exit 2
    ;;
esac
