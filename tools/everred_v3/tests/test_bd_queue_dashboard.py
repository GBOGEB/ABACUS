"""BD queue HTML operator I/O: source-bound, replayable and fail closed."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_bd_queue import render, validate, SCHEMA

SOURCE = ROOT / "data/bd_queue_20261014.json"
TEMPLATE = ROOT / "dashboard/bd_queue_template.html"
HTML = ROOT / "dashboard/bd_queue.html"


class BDQueueCards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(SOURCE.read_text(encoding="utf-8"))
        cls.template = TEMPLATE.read_text(encoding="utf-8")

    def test_source_bound_denominators_and_no_inferred_root(self):
        item = validate(copy.deepcopy(self.data))
        self.assertEqual(item["schema"], SCHEMA)
        self.assertEqual(len(item["families"]), 8)
        self.assertEqual(sum(len(x["observations"]) for x in item["families"]), 16)
        self.assertEqual(item["causal_confirmation"], "NO_SHARED_ROOTS_CONFIRMED")
        self.assertFalse(item["security_waiver"])
        self.assertFalse(item["authority_transfer"])
        self.assertEqual(item["disposition"], "ADMISSION_HOLD")

    def test_committed_html_matches_deterministic_generator(self):
        self.assertEqual(render(self.data, self.template),
                         HTML.read_text(encoding="utf-8"))
        self.assertEqual(render(self.data, self.template),
                         render(self.data, self.template))

    def test_foreign_or_swapped_head_rejected(self):
        bad = copy.deepcopy(self.data)
        bad["families"][0]["observations"][0]["sha"] = "a" * 40
        with self.assertRaisesRegex(ValueError, "exact PR head"):
            validate(bad)

    def test_unbound_and_malicious_link_rejected(self):
        bad = copy.deepcopy(self.data)
        bad["families"][0]["observations"][0]["url"] = (
            "https://github.com.evil/GBOGEB/ABACUS/actions/runs/1"
        )
        with self.assertRaisesRegex(ValueError, "non-native"):
            validate(bad)

    def test_duplicate_bd_identity_and_empty_proof_fail(self):
        bad = copy.deepcopy(self.data)
        bad["families"][1]["id"] = bad["families"][0]["id"]
        with self.assertRaisesRegex(ValueError, "family ID"):
            validate(bad)
        bad = copy.deepcopy(self.data)
        bad["families"][0]["observations"] = []
        with self.assertRaisesRegex(ValueError, "lacks evidence"):
            validate(bad)

    def test_authority_promotion_never_allowed(self):
        for field, value in (("authority_transfer", True),
                             ("security_waiver", True),
                             ("formal_credit_delta", 1),
                             ("disposition", "ADMIT")):
            bad = copy.deepcopy(self.data)
            bad[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(
                ValueError, "authority"
            ):
                validate(bad)

    def test_script_termination_escaped(self):
        bad = copy.deepcopy(self.data)
        bad["families"][0]["summary"] = "</script><script>window.pwned()</script>"
        out = render(bad, self.template)
        self.assertNotIn("</script><script>window.pwned()", out)
        self.assertIn("<\\/script>", out)

    def test_primary_io_and_no_unauthenticated_network(self):
        source = self.template
        self.assertIn('class="legend"', source)
        self.assertIn('id="search"', source)
        self.assertIn('id="lane"', source)
        self.assertIn('id="priority"', source)
        self.assertIn('id="export"', source)
        self.assertIn('id="copy"', source)
        self.assertIn("Evidence leaves", source)
        self.assertIn("Justification / causal confidence", source)
        self.assertIn("Treatment / acceptance DoV", source)
        self.assertNotIn("fetch(", source)
        self.assertNotIn("XMLHttpRequest", source)
        self.assertNotIn("github.rest", source)

    def test_missing_or_duplicate_template_marker_fails(self):
        for source in (self.template.replace("@@BD_QUEUE_JSON@@", ""),
                       self.template + "@@BD_QUEUE_JSON@@"):
            with self.subTest(size=len(source)), self.assertRaisesRegex(
                ValueError, "marker"
            ):
                render(self.data, source)


if __name__ == "__main__":
    unittest.main()
