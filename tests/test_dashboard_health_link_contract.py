"""Focused dashboard-health link evidence regressions (standard library only)."""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import re
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
WORKFLOW = ROOT / ".github/workflows/dashboard-health.yml"


class _Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() not in ("a", "link"):
            return
        self.links.extend(value for key, value in attrs if key and key.lower() == "href" and value)


def missing_targets(page: Path):
    parser = _Parser()
    parser.feed(page.read_text(encoding="utf-8"))
    broken = []
    for href in parser.links:
        if href.startswith(("#", "/")) or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", href):
            continue
        target = unquote(urlsplit(href).path)
        if target and not (page.parent / target).resolve().exists():
            broken.append(href)
    return broken

# Publication policy is semantic: preserve unavailable-target gating even when
# explanatory prose changes. Raw/URL-encoded hrefs both fail closed.
UNPUBLISHED_TARGETS = ("myrrha_handover/", "contract_baseline_full.html")


def unpublished_targets(html_text: str):
    parser = _Parser()
    parser.feed(html_text)
    return [href for href in parser.links
            if any(part in unquote(urlsplit(href).path).lower()
                   for part in UNPUBLISHED_TARGETS)]


class DashboardLinks(unittest.TestCase):
    def test_index_links_exist(self):
        self.assertEqual(missing_targets(DOCS / "index.html"), [])

    def test_runtime_links_exist(self):
        self.assertEqual(missing_targets(DOCS / "runtime.html"), [])

    def test_dynamic_js_string_is_not_anchor(self):
        self.assertEqual(missing_targets(DOCS / "code_purple_execution_graph.html"), [])

    def test_broken_true_static_link_still_fails(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "fixture.html"
            p.write_text('<script>const t = "href=\\"ignored-not-an-anchor.html\\"";</script>'
                         '<a href="missing-static.html">Missing</a>', encoding="utf-8")
            self.assertEqual(missing_targets(p), ["missing-static.html"])

    def test_unpublished_pages_are_explicitly_disclosed(self):
        home = (DOCS / "index.html").read_text(encoding="utf-8")
        run = (DOCS / "runtime.html").read_text(encoding="utf-8")
        self.assertIn("a source-authorized publication receipt is required", home)
        self.assertIn("Contract Baseline HTML is absent from this published build", home)
        self.assertIn("live JSON is not published", run)
        self.assertRegex(home, r'<span[^>]*aria-disabled="true"[^>]*>Handover link unavailable</span>')
        self.assertRegex(home, r'<span[^>]*aria-disabled="true"[^>]*>Contract Baseline unavailable</span>')
        self.assertEqual(unpublished_targets(home), [],
                         "Unpublished engineering targets must not gain a live link")
        self.assertNotIn('href="reports/runtime_governance_status.json"', run)

    def test_unpublished_url_encoded_and_alias_links_fail_closed(self):
        html_text = ('<a href="myrrha_handover/index.html">MYRRHA</a>'
                     '<a href="qplant/canonical_master/CONTRACT_Baseline_full.html">Contract</a>'
                     '<a href="qplant%2Fcanonical_master%2Fcontract_baseline_full.html">Encoded</a>')
        self.assertEqual(len(unpublished_targets(html_text)), 3)
        self.assertEqual(unpublished_targets('<span aria-disabled="true">Unavailable</span>'), [])

    def test_native_workflow_still_fails_closed(self):
        src = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('if [ "$href" = "\'+url+\'" ]; then', src)
        self.assertIn('case "$src" in', src)
        self.assertIn("Fail job on broken dashboards or links", src)
        self.assertIn("exit 1", src)


if __name__ == "__main__":
    unittest.main()
