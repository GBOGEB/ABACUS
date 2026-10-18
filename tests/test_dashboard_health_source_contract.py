"""Native dashboard-health regression contract; no deployment or issue mutation.

Execute the real workflow shell scanner against isolated synthetic HTML to
qualify exact dynamic-expression suppression while retaining true missing
link failures. The runtime generator must remain the existing W007 source.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "dashboard-health.yml"
INDEX = ROOT / "docs" / "index.html"
MANIFEST = ROOT / "docs" / "runtime-artifact-manifest.json"
PAGES = ROOT / ".github" / "workflows" / "pages.yml"


def _report_shell() -> str:
    lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
    try:
        start = lines.index("      - name: Report broken links")
        run = lines.index("        run: |", start + 1)
        stop = lines.index("        id: link_check", run + 1)
    except ValueError as exc:
        raise AssertionError("dashboard scan source layout changed") from exc
    block = lines[run + 1 : stop]
    if not block or any(not line.startswith("          ") for line in block if line):
        raise AssertionError("dashboard shell scanner indentation changed")
    return "\n".join(line[10:] if line else "" for line in block) + "\n"


def _fixture_scan(*, malicious_link: str) -> tuple[str, str]:
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        docs = folder / "docs"
        docs.mkdir()
        (docs / "present.html").write_text("<h1>Present</h1>", encoding="utf-8")
        (docs / "index.html").write_text(
            '<a href="present.html">available</a>'
            '<a href="missing.html">missing</a>'
            '<a href="https://github.com">external</a>'
            '<a href="#inside">anchor</a>'
            + malicious_link,
            encoding="utf-8",
        )
        output = folder / "output.txt"
        env = {**os.environ, "GITHUB_OUTPUT": str(output)}
        result = subprocess.run(
            ["bash", "-c", _report_shell()],
            cwd=folder,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        return result.stdout, output.read_text(encoding="utf-8")


class DashboardHealthContracts(unittest.TestCase):
    def test_scanner_keeps_missing_link_and_skips_exact_js_interpolation(self):
        stdout, output = _fixture_scan(
            malicious_link="<script>const a = '<a href=\"'+url+'\">x</a>';</script>"
        )
        self.assertIn("Broken: docs/index.html", stdout)
        self.assertIn("missing.html", stdout)
        self.assertIn("Dynamic JavaScript URL expression skipped", stdout)
        self.assertIn("Total broken internal links: 1", stdout)
        self.assertIn("broken_links=1", output)

    def test_scanner_does_not_skip_arbitrary_url_looking_missing_path(self):
        stdout, output = _fixture_scan(
            malicious_link='<a href="foo+url+bar.html">still missing</a>'
        )
        self.assertIn("Total broken internal links: 2", stdout)
        self.assertIn("broken_links=2", output)

    def test_portable_scanner_and_parent_relative_missing_link(self):
        # The scanner runs on macOS and Windows as well as Linux.
        # PCRE grep -P is not portable; it used to silently return 0 links.
        scanner = _report_shell()
        self.assertNotIn("grep -oP", scanner)
        self.assertIn("grep -oE", scanner)
        stdout, output = _fixture_scan(
            malicious_link='<a href="../absent.html?rev=7">missing parent</a>'
        )
        self.assertIn("missing.html", stdout)
        self.assertIn("../absent.html?rev=7", stdout)
        self.assertIn("Total broken internal links: 2", stdout)
        self.assertIn("broken_links=2", output)

    def test_unpublished_myrrha_and_contract_pages_not_advertised_as_live(self):
        html = INDEX.read_text(encoding="utf-8")
        self.assertNotIn('href="myrrha_handover/"', html)
        self.assertNotIn(
            'href="qplant/canonical_master/CONTRACT_Baseline_full.html"', html
        )
        self.assertIn("MYRRHA (unpublished)", html)
        self.assertIn("Contract Baseline unavailable", html)
        self.assertIn('href="qplant/canonical_master/MASTER_Input_full.html"', html)
        self.assertTrue(
            (ROOT / "docs/qplant/canonical_master/MASTER_Input_full.html").is_file()
        )

    def test_runtime_status_generated_with_same_source_as_pages(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        pages = PAGES.read_text(encoding="utf-8")
        marker = "python scripts/write_runtime_governance_status.py"
        report = "docs/reports/runtime_governance_status.json"
        self.assertIn(marker, workflow)
        self.assertIn(marker, pages)
        self.assertIn(report, workflow)
        self.assertIn(report, pages)
        self.assertLess(
            workflow.index("Reproduce Pages runtime-governance evidence"),
            workflow.index("Report broken links"),
        )
        manifest = MANIFEST.read_text(encoding="utf-8")
        self.assertIn('"status": "runtime_generated"', manifest)
        self.assertIn('"producer": "scripts/write_runtime_governance_status.py"', manifest)

    def test_required_exit_on_missing_links_not_weakened(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("BROKEN=$((BROKEN+1))", workflow)
        self.assertIn("broken_links=$BROKEN", workflow)
        self.assertIn("Fail job on broken dashboards or links", workflow)
        self.assertIn("exit 1", workflow)


if __name__ == "__main__":
    unittest.main()
