"""
Predefined load test scenarios for QPLANT API v4.4.0.

Usage:
    python load_test_scenarios.py --scenario smoke_test
    python load_test_scenarios.py --scenario normal_load
    python load_test_scenarios.py --list
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

SCENARIOS: Dict[str, Dict[str, Any]] = {
    "smoke_test": {
        "users": 10,
        "spawn_rate": 2,
        "run_time": "2m",
        "description": "Quick smoke test with 10 users",
        "tags": None,
    },
    "normal_load": {
        "users": 100,
        "spawn_rate": 10,
        "run_time": "10m",
        "description": "Normal production load — 100 concurrent users",
        "tags": None,
    },
    "peak_load": {
        "users": 300,
        "spawn_rate": 20,
        "run_time": "15m",
        "description": "Peak load — 300 concurrent users (2× expected)",
        "tags": None,
    },
    "stress_test": {
        "users": 500,
        "spawn_rate": 50,
        "run_time": "20m",
        "description": "Stress test — find breaking point",
        "tags": ["stress"],
    },
    "endurance_test": {
        "users": 150,
        "spawn_rate": 10,
        "run_time": "60m",
        "description": "Endurance test — sustained load for 1 hour",
        "tags": None,
    },
}


def run_scenario(
    name: str,
    host: str = "http://localhost:8000",
    report_dir: str = "reports",
) -> int:
    """Execute a load test scenario with Locust."""
    if name not in SCENARIOS:
        print(f"❌ Unknown scenario: {name}")
        print(f"   Available: {', '.join(SCENARIOS)}")
        return 1

    scenario = SCENARIOS[name]
    Path(report_dir).mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"{report_dir}/load_test_{name}_{timestamp}.html"
    csv_prefix = f"{report_dir}/load_test_{name}_{timestamp}"

    cmd = [
        "locust",
        "-f", "locustfile.py",
        "--host", host,
        "--headless",
        "--users", str(scenario["users"]),
        "--spawn-rate", str(scenario["spawn_rate"]),
        "--run-time", scenario["run_time"],
        "--html", report_file,
        "--csv", csv_prefix,
    ]

    if scenario.get("tags"):
        for tag in scenario["tags"]:
            cmd.extend(["--tags", tag])

    print(f"🔥 Running scenario: {name}")
    print(f"   {scenario['description']}")
    print(f"   Users: {scenario['users']}, Spawn: {scenario['spawn_rate']}/s, Duration: {scenario['run_time']}")
    print(f"   Report: {report_file}")
    print()

    try:
        result = subprocess.run(cmd, cwd=str(Path(__file__).parent))
        return result.returncode
    except FileNotFoundError:
        print("❌ Locust not installed. Run: pip install locust")
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="QPLANT Load Test Runner")
    parser.add_argument("--scenario", help="Scenario name to run")
    parser.add_argument("--host", default="http://localhost:8000", help="Target host")
    parser.add_argument("--list", action="store_true", help="List available scenarios")
    parser.add_argument("--export-json", help="Export scenarios to JSON file")
    args = parser.parse_args()

    if args.list:
        print("Available Load Test Scenarios:")
        print()
        for name, s in SCENARIOS.items():
            print(f"  {name:20s} — {s['description']}")
            print(f"  {'':20s}   Users: {s['users']}, Duration: {s['run_time']}")
            print()
        return

    if args.export_json:
        with open(args.export_json, "w") as f:
            json.dump(SCENARIOS, f, indent=2)
        print(f"✅ Scenarios exported to {args.export_json}")
        return

    if args.scenario:
        sys.exit(run_scenario(args.scenario, args.host))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
