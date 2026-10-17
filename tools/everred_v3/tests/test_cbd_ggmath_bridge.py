"""Adversarial non-causal provider handoff tests; do not invoke gg_MATH."""
import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "cbd_ggmath_bridge", ROOT / "scripts" / "cbd_ggmath_bridge.py"
)
bridge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bridge)


def fixture():
    return {
        "repository": "GBOGEB/ABACUS",
        "schema": "abacus.everred.cbd.portfolio_projection.v1",
        "main_sha_at_observation": "2" * 40,
        "safety": {"merge_admission": "HOLD", "security_waiver": False},
        "families": [
            {"workflow": "CI", "causal_root_id": None,
             "affected_prs": [2005, 2010, 2006]},
            {"workflow": "Governance", "causal_root_id": None,
             "affected_prs": [2006, 2007]},
            {"workflow": "A10", "causal_root_id": None,
             "affected_prs": [2007, 2008]},
        ],
    }


class GgMathBridgeTests(unittest.TestCase):
    def test_matched_alias_has_one_source_head_group(self):
        source, task = bridge.build(fixture(), "3" * 40)
        self.assertEqual(4, source["n_source_head_proxy_groups"])
        self.assertEqual(3, source["p_workflow_features"])
        self.assertEqual([[2005, 2010]], source["known_aliases_collapsed"])
        self.assertEqual("GBOGEB/gg_MATH",
                         task["inputs"]["canonical_provider"])
        self.assertFalse(task["inputs"]["providers_invoked"])
        self.assertFalse(task["authority_transfer"])

    def test_non_atomic_absences_not_true_negatives(self):
        source, _ = bridge.build(fixture(), "3" * 40)
        self.assertEqual("NOT_IN_FIRST_PAGE_FAILURE_SAMPLE",
                         source["absence_means"])
        self.assertFalse(source["sampling_complete"])
        self.assertIsNone(source["causal_root_labels"])

    def test_reverse_flipped_bit_changes_digest_not_authority(self):
        before, _ = bridge.build(fixture(), "3" * 40)
        d = fixture()
        d["families"][0]["affected_prs"].append(2007)
        after, task = bridge.build(d, "3" * 40)
        self.assertNotEqual(bridge.digest(before), bridge.digest(after))
        self.assertFalse(task["authority_transfer"])

    def test_forged_root_and_waiver_fail_closed(self):
        for mutate in (
            lambda x: x["families"][0].update(causal_root_id="ROOT-CLOSED"),
            lambda x: x["safety"].update(security_waiver=True),
            lambda x: x["safety"].update(merge_admission="PASS"),
        ):
            data = fixture()
            mutate(data)
            with self.assertRaises(ValueError):
                bridge.build(data, "3" * 40)

    def test_wrong_repo_invalid_head_or_duplicate_column_rejected(self):
        d = fixture()
        d["repository"] = "GBOGEB/CODEX"
        with self.assertRaises(ValueError):
            bridge.build(d, "3" * 40)
        with self.assertRaises(ValueError):
            bridge.build(fixture(), "head-with-no-sha")
        d = fixture()
        d["families"][1]["workflow"] = "CI"
        with self.assertRaises(ValueError):
            bridge.build(d, "3" * 40)

    def test_sha256_outputs_are_deterministic_and_proposal_only(self):
        source, task = bridge.build(fixture(), "3" * 40)
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            bridge.write(source, task, p)
            a = {file.name: file.read_bytes() for file in p.iterdir()}
            bridge.write(source, task, p)
            self.assertEqual(a, {f.name: f.read_bytes() for f in p.iterdir()})
            for name, sha in json.loads(a["sha256.json"]).items():
                self.assertEqual(sha, hashlib.sha256(a[name]).hexdigest())
            status = json.loads(a["ggmath-status.json"])
            self.assertFalse(status["provider_executed"])
            self.assertIsNone(status["pca_new_result"])
            self.assertEqual("HOLD", status["merge_admission"])


if __name__ == "__main__":
    unittest.main()
