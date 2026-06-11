"""
Visual Regression Testing for QPLANT HTML Outputs.

Uses Playwright to capture screenshots and PIL for pixel comparison.

Usage:
    python visual_tests.py --mode create-baseline --all
    python visual_tests.py --mode test --threshold 0.1
    python visual_tests.py --mode test --page dashboard
"""

from __future__ import annotations

import argparse
import json
import hashlib
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Test page registry ───────────────────────────────────────────────

TEST_PAGES: List[Dict[str, str]] = [
    {"url": "file:///home/ubuntu/recursive_review_dashboard.html", "name": "recursive_dashboard"},
    {"url": "file:///home/ubuntu/project_dashboard.html", "name": "project_dashboard"},
    {"url": "file:///home/ubuntu/monitoring_dashboard/index.html", "name": "monitoring_dashboard"},
    {"url": "file:///home/ubuntu/handover_dashboard/docs/index.html", "name": "docs_index"},
    {"url": "file:///home/ubuntu/handover_dashboard/docs/index_v4_0.html", "name": "docs_v4"},
    {"url": "file:///home/ubuntu/handover_dashboard/docs/index_v3_1.html", "name": "docs_v3_1"},
    {"url": "file:///home/ubuntu/handover_dashboard/docs/dashboard.html", "name": "triage_dashboard"},
    {"url": "file:///home/ubuntu/handover_dashboard/docs/calculations.html", "name": "calculations"},
    {"url": "file:///home/ubuntu/handover_dashboard/docs/executive_summary.html", "name": "exec_summary"},
    {"url": "file:///home/ubuntu/handover_dashboard/docs/handover.html", "name": "handover"},
    {"url": "file:///home/ubuntu/handover_dashboard/docs/rtm_traceability.html", "name": "rtm_traceability"},
    {"url": "file:///home/ubuntu/handover_dashboard/docs/triage_compliance.html", "name": "compliance"},
    {"url": "file:///home/ubuntu/handover_dashboard/docs/STAKEHOLDER_PRESENTATION.html", "name": "stakeholder"},
    {"url": "file:///home/ubuntu/handover_dashboard/docs/compressors/HP_Redundancy_Analysis.html", "name": "hp_redundancy"},
    {"url": "file:///home/ubuntu/handover_dashboard/docs/compressors/WCS_HP_Protection.html", "name": "wcs_protection"},
    {"url": "file:///home/ubuntu/handover_dashboard/docs/liquid_he/Liquid_Operations_Guide.html", "name": "liquid_ops"},
]


class VisualRegressionTester:
    """Capture screenshots and compare against baselines for visual regression."""

    def __init__(
        self,
        baseline_dir: str = "baselines",
        output_dir: str = "screenshots",
        diff_dir: str = "diffs",
    ) -> None:
        self.baseline_dir = Path(baseline_dir)
        self.output_dir = Path(output_dir)
        self.diff_dir = Path(diff_dir)
        self.baseline_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.diff_dir.mkdir(parents=True, exist_ok=True)
        self._browser = None
        self._playwright = None

    def _ensure_browser(self) -> None:
        """Lazily launch Playwright browser."""
        if self._browser is None:
            from playwright.sync_api import sync_playwright
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)

    def close(self) -> None:
        """Clean up browser resources."""
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def capture_screenshot(
        self,
        url: str,
        name: str,
        viewport: Tuple[int, int] = (1920, 1080),
        target_dir: Optional[Path] = None,
    ) -> Path:
        """Capture a full-page screenshot."""
        self._ensure_browser()
        target = target_dir or self.output_dir
        page = self._browser.new_page(
            viewport={"width": viewport[0], "height": viewport[1]}
        )
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(1000)  # Extra settle time
            screenshot_path = target / f"{name}.png"
            page.screenshot(path=str(screenshot_path), full_page=True)
            return screenshot_path
        except Exception as e:
            print(f"  ⚠️  Failed to capture {name}: {e}")
            return Path("")
        finally:
            page.close()

    def compare_screenshots(
        self,
        baseline_path: Path,
        current_path: Path,
        name: str,
        threshold: float = 0.1,
    ) -> Dict[str, Any]:
        """
        Compare two screenshots pixel-by-pixel.

        Returns dict with diff_percentage, passed status, and diff image path.
        """
        from PIL import Image
        import numpy as np

        if not baseline_path.exists():
            return {"name": name, "passed": False, "reason": "no_baseline", "diff_pct": 100.0}
        if not current_path.exists():
            return {"name": name, "passed": False, "reason": "capture_failed", "diff_pct": 100.0}

        baseline = Image.open(baseline_path).convert("RGB")
        current = Image.open(current_path).convert("RGB")

        # Resize to match if needed
        if baseline.size != current.size:
            current = current.resize(baseline.size, Image.LANCZOS)

        bl_arr = np.array(baseline, dtype=np.float32)
        cr_arr = np.array(current, dtype=np.float32)

        # Per-pixel difference
        diff = np.abs(bl_arr - cr_arr)
        diff_mask = np.any(diff > 10, axis=2)  # Threshold per channel
        diff_pct = (diff_mask.sum() / diff_mask.size) * 100.0

        # Generate diff image (red overlay on changed pixels)
        diff_image = np.array(current, dtype=np.uint8).copy()
        diff_image[diff_mask] = [255, 0, 0]  # Red for changed pixels
        diff_img = Image.fromarray(diff_image)
        diff_path = self.diff_dir / f"{name}_diff.png"
        diff_img.save(str(diff_path))

        passed = diff_pct < threshold
        return {
            "name": name,
            "passed": passed,
            "diff_pct": round(diff_pct, 4),
            "diff_image": str(diff_path),
            "baseline": str(baseline_path),
            "current": str(current_path),
        }

    def create_baselines(self, pages: Optional[List[Dict[str, str]]] = None) -> List[str]:
        """Capture baseline screenshots for all test pages."""
        pages = pages or TEST_PAGES
        captured = []
        for page in pages:
            print(f"  📸 Capturing baseline: {page['name']}")
            path = self.capture_screenshot(
                page["url"], page["name"], target_dir=self.baseline_dir
            )
            if path.exists():
                captured.append(page["name"])
        # Save manifest
        manifest = {
            "created": datetime.now().isoformat(),
            "pages": len(captured),
            "baselines": captured,
        }
        (self.baseline_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
        return captured

    def run_tests(
        self,
        pages: Optional[List[Dict[str, str]]] = None,
        threshold: float = 0.1,
    ) -> Dict[str, Any]:
        """Run visual regression tests against baselines."""
        pages = pages or TEST_PAGES
        results = []

        for page in pages:
            print(f"  🔍 Testing: {page['name']}")
            current = self.capture_screenshot(page["url"], page["name"])
            baseline = self.baseline_dir / f"{page['name']}.png"
            result = self.compare_screenshots(baseline, current, page["name"], threshold)
            results.append(result)
            status = "✅" if result["passed"] else "❌"
            print(f"     {status} diff={result['diff_pct']:.4f}%")

        passed = sum(1 for r in results if r["passed"])
        total = len(results)
        return {
            "timestamp": datetime.now().isoformat(),
            "threshold_pct": threshold,
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate_pct": round(passed / max(total, 1) * 100, 1),
            "results": results,
        }


def generate_report_html(test_results: Dict[str, Any], output: str = "visual_regression_report.html") -> None:
    """Generate interactive HTML report from test results."""
    passed = test_results["passed"]
    failed = test_results["failed"]
    total = test_results["total"]
    rate = test_results["pass_rate_pct"]

    rows = []
    for r in test_results["results"]:
        status_class = "passed" if r["passed"] else "failed"
        status_icon = "✅" if r["passed"] else "❌"
        rows.append(f"""
        <div class="comparison {status_class}">
            <div class="comp-header">
                <span class="status-icon">{status_icon}</span>
                <span class="page-name">{r['name']}</span>
                <span class="diff-pct">Diff: {r['diff_pct']:.4f}%</span>
            </div>
            <div class="images">
                <div><h4>Baseline</h4><img src="{r.get('baseline', '')}" alt="baseline" onerror="this.alt='Not available'"/></div>
                <div><h4>Current</h4><img src="{r.get('current', '')}" alt="current" onerror="this.alt='Not available'"/></div>
                <div><h4>Diff</h4><img src="{r.get('diff_image', '')}" alt="diff" onerror="this.alt='Not available'"/></div>
            </div>
        </div>""")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>QPLANT Visual Regression Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: system-ui, sans-serif; background: #0d1117; color: #c9d1d9; padding: 2rem; }}
        h1 {{ color: #58a6ff; margin-bottom: 0.5rem; }}
        .summary {{ display: flex; gap: 2rem; margin: 1.5rem 0; }}
        .metric {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 1rem 1.5rem; }}
        .metric .value {{ font-size: 2rem; font-weight: 700; }}
        .metric .label {{ color: #8b949e; font-size: 0.9rem; }}
        .green {{ color: #3fb950; }}
        .red {{ color: #f85149; }}
        .comparison {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; margin: 1rem 0; padding: 1rem; }}
        .comparison.passed {{ border-left: 4px solid #3fb950; }}
        .comparison.failed {{ border-left: 4px solid #f85149; }}
        .comp-header {{ display: flex; align-items: center; gap: 1rem; margin-bottom: 0.5rem; }}
        .page-name {{ font-weight: 600; font-size: 1.1rem; }}
        .diff-pct {{ color: #8b949e; margin-left: auto; }}
        .images {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; }}
        .images img {{ max-width: 100%; border-radius: 4px; border: 1px solid #30363d; }}
        .images h4 {{ color: #8b949e; margin-bottom: 0.5rem; }}
        .timestamp {{ color: #8b949e; font-size: 0.85rem; }}
    </style>
</head>
<body>
    <h1>🔍 Visual Regression Test Results</h1>
    <p class="timestamp">Generated: {test_results['timestamp']} | Threshold: {test_results['threshold_pct']}%</p>

    <div class="summary">
        <div class="metric"><div class="value">{total}</div><div class="label">Total Pages</div></div>
        <div class="metric"><div class="value green">{passed}</div><div class="label">Passed</div></div>
        <div class="metric"><div class="value {'green' if failed == 0 else 'red'}">{failed}</div><div class="label">Failed</div></div>
        <div class="metric"><div class="value {'green' if rate >= 90 else 'red'}">{rate}%</div><div class="label">Pass Rate</div></div>
    </div>

    <h2>Page Comparisons</h2>
    {''.join(rows)}
</body>
</html>"""

    Path(output).write_text(html)
    print(f"\n📄 Report: {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="QPLANT Visual Regression Testing")
    parser.add_argument("--mode", choices=["create-baseline", "test"], required=True)
    parser.add_argument("--threshold", type=float, default=0.1, help="Max diff %% to pass")
    parser.add_argument("--page", help="Test single page by name")
    parser.add_argument("--all", action="store_true", help="Process all pages")
    parser.add_argument("--report", default="html", choices=["html", "json"])
    args = parser.parse_args()

    tester = VisualRegressionTester()

    try:
        pages = TEST_PAGES
        if args.page:
            pages = [p for p in TEST_PAGES if p["name"] == args.page]
            if not pages:
                print(f"❌ Page not found: {args.page}")
                print(f"   Available: {', '.join(p['name'] for p in TEST_PAGES)}")
                sys.exit(1)

        if args.mode == "create-baseline":
            print("📸 Creating baselines...")
            captured = tester.create_baselines(pages)
            print(f"\n✅ Captured {len(captured)} baselines")

        elif args.mode == "test":
            print("🔍 Running visual regression tests...")
            results = tester.run_tests(pages, args.threshold)
            if args.report == "html":
                generate_report_html(results)
            else:
                print(json.dumps(results, indent=2))

            if results["failed"] > 0:
                sys.exit(1)

    finally:
        tester.close()


if __name__ == "__main__":
    main()
