#!/bin/bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────
# QPLANT Load Test Runner
# Usage:
#   ./run_load_tests.sh                    # Run all scenarios
#   ./run_load_tests.sh smoke_test         # Run single scenario
#   ./run_load_tests.sh --host http://api  # Custom host
# ─────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOST="${QPLANT_TEST_HOST:-http://localhost:8000}"
REPORT_DIR="$SCRIPT_DIR/reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Parse arguments
SCENARIO="${1:-all}"
if [ "$SCENARIO" = "--host" ]; then
    HOST="${2:-http://localhost:8000}"
    SCENARIO="${3:-all}"
fi

mkdir -p "$REPORT_DIR"

echo "🔥 QPLANT Load Testing — v4.4.0"
echo "   Host:      $HOST"
echo "   Scenario:  $SCENARIO"
echo "   Reports:   $REPORT_DIR"
echo "───────────────────────────────────────────────"

# Check locust installed
if ! command -v locust &> /dev/null; then
    echo "Installing locust..."
    pip install locust > /dev/null 2>&1
fi

run_scenario() {
    local name=$1
    local users=$2
    local rate=$3
    local duration=$4

    echo ""
    echo "▶ Running: $name (${users} users, ${rate}/s, ${duration})"

    locust -f "$SCRIPT_DIR/locustfile.py" \
        --host="$HOST" \
        --headless \
        --users="$users" \
        --spawn-rate="$rate" \
        --run-time="$duration" \
        --html="$REPORT_DIR/load_test_${name}_${TIMESTAMP}.html" \
        --csv="$REPORT_DIR/load_test_${name}_${TIMESTAMP}" \
        --only-summary \
        2>&1 | tail -20

    echo "   ✅ Report: $REPORT_DIR/load_test_${name}_${TIMESTAMP}.html"
}

if [ "$SCENARIO" = "all" ]; then
    run_scenario "smoke_test"    10  2  "2m"
    run_scenario "normal_load"  100 10  "5m"
    run_scenario "peak_load"    300 20  "5m"
    echo ""
    echo "═══════════════════════════════════════════════"
    echo "✅ All load test scenarios complete"
    echo "   Reports in: $REPORT_DIR"
else
    case "$SCENARIO" in
        smoke_test)     run_scenario "smoke_test"    10   2  "2m" ;;
        normal_load)    run_scenario "normal_load"  100  10  "10m" ;;
        peak_load)      run_scenario "peak_load"    300  20  "15m" ;;
        stress_test)    run_scenario "stress_test"  500  50  "20m" ;;
        endurance_test) run_scenario "endurance"    150  10  "60m" ;;
        *)
            echo "❌ Unknown scenario: $SCENARIO"
            echo "   Available: smoke_test, normal_load, peak_load, stress_test, endurance_test, all"
            exit 1
            ;;
    esac
fi
