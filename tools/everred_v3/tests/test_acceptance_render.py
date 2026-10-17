import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from acceptance import core, graph, render, telemetry
from test_acceptance_core import fixture
from test_acceptance_telemetry import snapshot


def data():
    c, ctx, event = fixture()
    a = event()
    p = core.project(c, ctx, [a])
    g = graph.graph_projection(p)
    s = graph.sipoc(p)
    t = telemetry.analyze([snapshot(0, []), snapshot(1, [a])])
    return p, g, s, t


class DashboardAndLedgerTests(unittest.TestCase):
    def test_html_has_separate_disabled_acceptance_controls(self):
        html = render.render_html(*data())
        self.assertIn("Evidence captured", html)
        self.assertIn("Independently admitted", html)
        self.assertIn("disabled checked", html)
        self.assertIn("Admission HOLD", html)
        self.assertIn("github.com/GBOGEB/ABACUS/actions/runs", html)

    def test_html_filters_and_accessibility(self):
        html = render.render_html(*data())
        self.assertIn("id='repoFilter'", html)
        self.assertIn("id='stateFilter'", html)
        self.assertIn("id='searchFilter'", html)
        self.assertIn("aria-live='polite'", html)
        self.assertIn("viewport", html)

    def test_title_from_untrusted_obligation_is_escaped(self):
        p, g, s, t = data()
        p["obligations"][0]["title"] = "<script>alert(1)</script>"
        html = render.render_html(p, g, s, t)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_markdown_checkmarks_only_observation(self):
        p, _, _, _ = data()
        report = render.markdown_debt(p)
        self.assertIn("| [x] | [ ] |", report)
        self.assertNotIn("| [x] | [x] |", report)
        self.assertIn("HOLD", report)

    def test_hashes_deterministic(self):
        p, g, s, t = data()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            render.write_bundle(path, p, g, s, t)
            a = {file.name: file.read_bytes() for file in path.iterdir()}
            render.write_bundle(path, p, g, s, t)
            b = {file.name: file.read_bytes() for file in path.iterdir()}
            self.assertEqual(a, b)
            m = json.loads(a["sha256.json"])
            for name, hashcode in m.items():
                self.assertEqual(hashlib.sha256(a[name]).hexdigest(), hashcode)

    def test_ledger_does_not_promote_authority(self):
        p, g, s, t = data()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            render.write_bundle(path, p, g, s, t)
            lines = (
                path.joinpath("ledger_proposals.jsonl").read_text().strip().splitlines()
            )
            self.assertEqual(1, len(lines))
            self.assertFalse(json.loads(lines[0])["authority_transfer"])
            self.assertFalse(json.loads(lines[0])["security_waiver"])
            self.assertEqual(
                "HOLD",
                json.loads(path.joinpath("acceptance.json").read_text())["admission"],
            )

    def test_unknown_current_coverage_not_zero(self):
        p, g, s, t = data()
        h = render.render_html(p, g, s, t)
        self.assertIn("Main coverage", h)
        self.assertIn("UNKNOWN", h)
        self.assertIsNone(p["metrics"]["current_diff_coverage"])

    def test_network_free_offline_html(self):
        h = render.render_html(*data())
        self.assertNotIn("fetch(", h)
        self.assertNotIn('src="https:', h)
        self.assertNotIn("<iframe", h)
        self.assertIn("<!doctype html>", h)

    def test_footer_pulse_scope_not_independent(self):
        h = render.render_html(*data())
        self.assertIn("Not three independent Github experiments", h)
        self.assertIn(
            "status_stability",
            json.dumps(telemetry.analyze([snapshot(0, []), snapshot(1, [])])),
        )

    def test_report_accepts_scoped_local_run_measurements(self):
        p, g, s, t = data()
        h = render.render_html(
            p, g, s, t, {"tests_passed": 48, "coverage_percent": 99.6}
        )
        self.assertIn("48 cases", h)
        self.assertIn("99.6%", h)
        self.assertIn("not GitHub admission", h)

    def test_unverified_acceptance_promotion_fails_closed(self):
        p, g, s, t = data()
        p["admission"] = "MERGED"
        with self.assertRaisesRegex(ValueError, "cannot represent"):
            render.render_html(p, g, s, t)


if __name__ == "__main__":
    unittest.main()
