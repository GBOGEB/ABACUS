"""
Analyze load test results and compare against performance baselines.

Usage:
    python analyze_results.py --csv-prefix reports/load_test_smoke_test_20260517
    python analyze_results.py --report-dir reports/
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_baselines(path: str = "performance_baselines.json") -> Dict[str, Any]:
    """Load performance baselines."""
    with open(path) as f:
        return json.load(f)


def parse_locust_stats(csv_path: str) -> List[Dict[str, Any]]:
    """Parse Locust stats CSV output."""
    results = []
    try:
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                results.append(row)
    except FileNotFoundError:
        pass
    return results


def grade_performance(
    stats: List[Dict[str, Any]],
    baselines: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Grade performance against baselines.

    Returns:
        {
            "grade": "A",
            "score": 95.0,
            "endpoints": [...],
            "regressions": [...],
            "recommendations": [...]
        }
    """
    endpoint_baselines = baselines.get("api_endpoints", {})
    regressions = []
    endpoint_results = []
    total_score = 0
    count = 0

    for stat in stats:
        name = stat.get("Name", "")
        if name == "Aggregated" or not name:
            continue

        p50 = float(stat.get("50%", 0))
        p95 = float(stat.get("95%", 0))
        p99 = float(stat.get("99%", 0))
        fail_count = int(stat.get("Failure Count", 0))
        req_count = int(stat.get("Request Count", 1))
        error_rate = (fail_count / max(req_count, 1)) * 100

        # Find matching baseline
        baseline = None
        for path, bl in endpoint_baselines.items():
            if path in name or name in path:
                baseline = bl
                break

        ep_score = 100.0
        if baseline:
            if p95 > baseline.get("p95_ms", 999999):
                regression = f"{name}: p95={p95}ms exceeds baseline {baseline['p95_ms']}ms"
                regressions.append(regression)
                ep_score -= 20
            if p99 > baseline.get("p99_ms", 999999):
                ep_score -= 10
            if error_rate > float(str(baseline.get("error_rate_pct", "1")).rstrip("%")):
                regressions.append(f"{name}: error_rate={error_rate:.2f}% exceeds baseline")
                ep_score -= 30

        ep_score = max(0, ep_score)
        total_score += ep_score
        count += 1

        endpoint_results.append({
            "name": name,
            "p50_ms": p50,
            "p95_ms": p95,
            "p99_ms": p99,
            "error_rate_pct": round(error_rate, 2),
            "requests": req_count,
            "score": ep_score,
        })

    avg_score = total_score / max(count, 1)

    # Grade mapping
    if avg_score >= 95:
        grade = "A"
    elif avg_score >= 85:
        grade = "B"
    elif avg_score >= 70:
        grade = "C"
    elif avg_score >= 50:
        grade = "D"
    else:
        grade = "F"

    recommendations = []
    if regressions:
        recommendations.append("Investigate performance regressions listed above")
    if avg_score < 85:
        recommendations.append("Consider scaling up resources or optimizing slow endpoints")

    return {
        "grade": grade,
        "score": round(avg_score, 1),
        "endpoints": endpoint_results,
        "regressions": regressions,
        "recommendations": recommendations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze QPLANT load test results")
    parser.add_argument("--csv-prefix", help="Locust CSV output prefix")
    parser.add_argument("--baselines", default="performance_baselines.json")
    parser.add_argument("--output", help="Output JSON file")
    args = parser.parse_args()

    if not args.csv_prefix:
        # Find most recent stats CSV
        reports = sorted(Path("reports").glob("*_stats.csv"), reverse=True)
        if not reports:
            print("❌ No load test results found in reports/")
            sys.exit(1)
        csv_path = str(reports[0])
        print(f"Using most recent: {csv_path}")
    else:
        csv_path = f"{args.csv_prefix}_stats.csv"

    baselines = load_baselines(args.baselines)
    stats = parse_locust_stats(csv_path)

    if not stats:
        print(f"❌ No stats found in {csv_path}")
        sys.exit(1)

    result = grade_performance(stats, baselines)

    print(f"\n{'═' * 50}")
    print(f"Performance Grade: {result['grade']} ({result['score']}/100)")
    print(f"{'═' * 50}")

    print(f"\nEndpoints:")
    for ep in result["endpoints"]:
        status = "✅" if ep["score"] >= 80 else "⚠️" if ep["score"] >= 50 else "❌"
        print(f"  {status} {ep['name']}")
        print(f"     p50={ep['p50_ms']}ms  p95={ep['p95_ms']}ms  err={ep['error_rate_pct']}%")

    if result["regressions"]:
        print(f"\n⚠️  Regressions:")
        for r in result["regressions"]:
            print(f"  - {r}")

    if result["recommendations"]:
        print(f"\n💡 Recommendations:")
        for r in result["recommendations"]:
            print(f"  - {r}")

    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\n📄 Report saved to {args.output}")


if __name__ == "__main__":
    main()
