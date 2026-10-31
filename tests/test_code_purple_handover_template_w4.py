"""Guard the non-authoritative GitHub-first handover against false promotion."""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
H = ROOT / "handover" / "code_purple_20261018"


class TestW4Handover(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((H / "W4_STATE.json").read_text(encoding="utf-8"))

    def test_original_protocol_not_replaced(self):
        t = (ROOT / "handover" / "HANDOVER_MESSAGE_TEMPLATE.md").read_text(
            encoding="utf-8"
        )
        for phrase in (
            "LOSSLESS_HANDOVER_V2",
            "CP.HANDOFF",
            "CP.RESUME",
            "G3P",
            "DoV",
            "SHA-256",
            "UNKNOWN",
        ):
            self.assertIn(phrase, t)
        self.assertTrue((ROOT / "tools" / "handover_v2" / "process_spec.json").exists())

    def test_nine_cell_bytes_and_nonpromotion(self):
        s = self.s
        v = s["nine_cell"]
        self.assertEqual(
            (
                v["jobs_pass"],
                v["artifacts_verified"],
                v["json_junit_pairs_verified"],
                v["testcases_passed"],
            ),
            (9, 9, 9, 225),
        )
        a = v["provider_artifacts"]
        self.assertEqual(len(a), 9)
        self.assertEqual(len({(x["os"], x["python"]) for x in a}), 9)
        self.assertEqual(len({x["artifact_id"] for x in a}), 9)
        self.assertTrue(all(re.fullmatch(r"[0-9a-f]{64}", x["zip_sha256"]) for x in a))
        self.assertEqual(s["governance"]["merge_admission"], "HOLD")
        self.assertIsNone(s["governance"]["governed_merge_sha"])
        self.assertIsNone(s["governance"]["accepted_rex"])
        self.assertFalse(s["governance"]["security_waiver"])
        self.assertFalse(s["governance"]["authority_transfer"])

    def test_old_B0_not_promoted_as_current(self):
        s = self.s
        self.assertEqual(len(s["repo_heads"]), 5)
        self.assertEqual(
            [
                x["branch"]
                for x in s["repo_heads"]
                if "pipeline-automation-hub" in x["repo"]
            ],
            ["master"],
        )
        self.assertEqual(s["historical_b0"]["fail"], 1)
        self.assertNotEqual(s["historical_b0"]["sha"], s["source_base_sha"])
        self.assertIsNone(s["current_main_terminal_b0"])
        self.assertIsNone(s["matched_main_or_diff_delta"])
        self.assertIn("CP.RESUME", (H / "DROPIN.md").read_text(encoding="utf-8"))
        self.assertIn("flowchart TD", (H / "W4_DAG.mmd").read_text(encoding="utf-8"))
