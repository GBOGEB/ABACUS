"""Negative and exact-byte tests for executable MCW cold DAG slice."""

import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "mcw_dag", ROOT / "tools" / "mcw_artifact_dag_execute.py"
)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
HEAD = "a" * 40
CHILD = "b" * 40


class ColdDagTests(unittest.TestCase):
    def setup(self, root):
        (root / "source.json").write_text('{"value": 1}')
        catalog = {
            "schema": "mcw.artifact.catalog.v1",
            "artifacts": [
                {"id": "src", "role": "repository_source", "path": "source.json"},
                {"id": "review", "role": "generated_output"},
                {"id": "external", "role": "controlled_input"},
            ],
        }
        style = {"version": "0.2.0"}
        raw_catalog = json.dumps(catalog).encode()
        raw_style = json.dumps(style).encode()
        html = b"<html>read-only</html>"
        receipt = {
            "repository": "GBOGEB/ABACUS",
            "source_sha": HEAD,
            "merge_admission": "HOLD",
            "binary_release_admitted": False,
            "stages": list(M.STAGES),
            "html_sha256": M.sha256(html),
            "catalog_file_sha256": M.sha256(raw_catalog),
            "style_file_sha256": M.sha256(raw_style),
            "style_version": style["version"],
            "artifacts": [
                {
                    "id": "src",
                    "role": "repository_source",
                    "evidence": {
                        "state": "LOCAL_BYTES_VERIFIED",
                        "sha256": M.sha256((root / "source.json").read_bytes()),
                    },
                },
                {
                    "id": "review",
                    "role": "generated_output",
                    "evidence": {"state": "NOT_GENERATED_IN_COLD_VIEW", "sha256": None},
                },
                {
                    "id": "external",
                    "role": "controlled_input",
                    "evidence": {
                        "state": "CONTROLLED_EXTERNAL_UNKNOWN",
                        "sha256": None,
                    },
                },
            ],
        }
        child = {
            "schema": "mcw.upstream.child.reference.v1",
            "owner": "GBOGEB/cryoplant-project",
            "ref_kind": "OPEN_PR_CANDIDATE",
            "commit_sha": CHILD,
            "pr_number": 1926,
            "evidence_class": "SOURCE_POINTER_ONLY",
            "physical_evidence_bytes": "NOT_VERIFIED",
            "child_disposition": "UNKNOWN",
            "source_pins": [{"path": "docs/lineage.md", "git_blob_sha": CHILD}],
        }
        return (
            catalog,
            style,
            html,
            receipt,
            {"valid": True},
            child,
            raw_catalog,
            raw_style,
        )

    def run_assess(self, root, data):
        return M.assess(root, HEAD, *data)

    def test_cold_stages_and_no_release_promotion(self):
        with tempfile.TemporaryDirectory() as d:
            data = self.setup(Path(d))
            result = self.run_assess(Path(d), data)
            self.assertEqual(result["stage_pass"], 2)
            self.assertEqual(result["first_blocker"], "SOURCE_FREEZE")
            self.assertEqual(result["stages"][2]["status"], "BLOCKED")
            self.assertEqual(result["stages"][-1]["status"], "HOLD")
            self.assertEqual(result["preview_gate"], "PASS_COLD_SOURCE_ONLY")
            self.assertFalse(result["physical_evidence_verified"])
            self.assertEqual(result["child_engineering_credit"], 0)
            self.assertEqual(result["merge_admission"], "HOLD")

    def test_tampered_html_or_source_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            base = self.setup(root)
            mutated = list(copy.deepcopy(base))
            mutated[2] = b"<html>forged</html>"
            with self.assertRaisesRegex(ValueError, "HTML bytes"):
                self.run_assess(root, mutated)
            (root / "source.json").write_text('{"value": 2}')
            with self.assertRaisesRegex(ValueError, "source byte"):
                self.run_assess(root, base)

    def test_raw_catalog_and_style_bytes_required(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            base = self.setup(root)
            for field in (6, 7):
                bad = list(base)
                bad[field] = b"altered"
                with self.subTest(field=field), self.assertRaises(ValueError):
                    self.run_assess(root, bad)
            with self.assertRaisesRegex(ValueError, "raw SSOT"):
                M.assess(root, HEAD, *base[:6])

    def test_rejects_stale_sha_and_false_binary_credit(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            base = list(self.setup(root))
            base[3]["source_sha"] = CHILD
            with self.assertRaises(ValueError):
                self.run_assess(root, base)
            base = list(self.setup(root))
            base[3]["binary_release_admitted"] = True
            with self.assertRaises(ValueError):
                self.run_assess(root, base)
            base = list(self.setup(root))
            base[3]["artifacts"][1]["evidence"]["sha256"] = "f" * 64
            with self.assertRaises(ValueError):
                self.run_assess(root, base)

    def test_rejects_child_authority_escalation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for key, value in (
                ("child_disposition", "ACCEPT"),
                ("physical_evidence_bytes", "VERIFIED"),
                ("evidence_class", "RELEASE_AUTHORITY"),
            ):
                base = list(self.setup(root))
                base[5][key] = value
                with self.subTest(key=key), self.assertRaises(ValueError):
                    self.run_assess(root, base)

    def test_rejects_forged_child_pins(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for path in ("../private", "/tmp/private"):
                base = list(self.setup(root))
                base[5]["source_pins"][0]["path"] = path
                with self.subTest(path=path), self.assertRaises(ValueError):
                    self.run_assess(root, base)
            base = list(self.setup(root))
            base[5]["source_pins"][0]["git_blob_sha"] = "not-a-sha"
            with self.assertRaises(ValueError):
                self.run_assess(root, base)

    def test_rejects_cycle_via_wrong_stage_contract(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            base = list(self.setup(root))
            base[3]["stages"] = ["CENSUS", "SOURCE_FREEZE", "SSOT_PIN"]
            with self.assertRaises(ValueError):
                self.run_assess(root, base)

    def test_rejects_missing_source_and_bogus_authority(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            base = list(self.setup(root))
            base[0]["artifacts"][0]["path"] = "../private"
            with self.assertRaises(ValueError):
                self.run_assess(root, base)
            base = list(self.setup(root))
            base[4]["valid"] = False
            with self.assertRaises(ValueError):
                self.run_assess(root, base)


if __name__ == "__main__":
    unittest.main()
