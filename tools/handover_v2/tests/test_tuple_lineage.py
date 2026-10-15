"""Negative controls: semantic prompt-response and BD lineage."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("tuple_lineage",HERE/"tuple_lineage.py")
core=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(core)
ROOT=HERE.parents[1]/"handover/mip_20261015"
INPUT=(ROOT/"CHAT_TUPLE_LEDGER_v1.json").read_bytes()
TEXT=(ROOT/"GOLDEN_THREAD_TUPLES_v1.md").read_bytes()
MANIFEST=(ROOT/"TUPLE_MANIFEST_v1.json").read_bytes()

class TupleLineageTest(unittest.TestCase):
    def test_integrity_and_counts(self):
        receipt=core.check(INPUT,TEXT,MANIFEST)
        self.assertEqual((8,15),(receipt["tuples"],receipt["todos"]))
        self.assertIsNone(receipt["operational_bd_closed"])
    def test_replay_stability(self):
        self.assertEqual(core.check(INPUT,TEXT,MANIFEST),
                         core.check(INPUT,TEXT,MANIFEST))
    def test_manifest_tampering_rejected(self):
        with self.assertRaises(ValueError):
            core.check(INPUT,TEXT+b"tampered",MANIFEST)
    def semantic_check(self, modified):
        """Reseal a modified input so tests reach semantic validation."""
        payload=(json.dumps(modified)+"\n").encode()
        updated=json.loads(MANIFEST)
        updated["files"]["CHAT_TUPLE_LEDGER.json"]=core.h(payload)
        sealed=(json.dumps(updated)+"\n").encode()
        return core.check(payload,TEXT,sealed)
    def test_false_root_closure_rejected(self):
        s=json.loads(INPUT)
        s["todo_records"][0]["operational_root_credit"]="CLOSED"
        with self.assertRaises(ValueError):
            self.semantic_check(s)
    def test_zero_is_not_unknown(self):
        s=json.loads(INPUT)
        s["operational_roots_closed"]=0
        with self.assertRaises(ValueError):
            self.semantic_check(s)
    def test_no_fake_verbatim(self):
        s=json.loads(INPUT)
        s["fidelity"]="VERBATIM"
        with self.assertRaises(ValueError):
            self.semantic_check(s)
    def test_no_orphan_source_tuple(self):
        s=json.loads(INPUT)
        s["todo_records"][0]["source_tuple_ids"]=["T99"]
        with self.assertRaises(ValueError):
            self.semantic_check(s)


    def test_pulse_telemetry_exact_head(self):
        head="269de48db9b70a91383b2fcdf8822ec0e6496634"
        runs={
            "38775913287": {"source_sha":head,"conclusion":"success",
                             "url":"https://github.com/GBOGEB/ABACUS/actions/runs/38775913287"},
            "38775913386": {"source_sha":head,"conclusion":"success",
                             "url":"https://github.com/GBOGEB/ABACUS/actions/runs/38775913386"},
        }
        receipt=core.pulse_metrics(json.loads(INPUT),head_sha=head,observed_ci=runs)
        self.assertEqual((2,2),(receipt["workflow_terminal"],receipt["workflow_pass"]))
        self.assertEqual(100.0,receipt["workflow_pass_pct"])
        self.assertEqual(15,sum(receipt["todo_state_count"].values()))
        self.assertIsNone(receipt["operational_roots_closed"])
        self.assertIsNone(receipt["canonical_coverage"])
    def test_pulse_unknown_is_not_zero(self):
        head="269de48db9b70a91383b2fcdf8822ec0e6496634"
        receipt=core.pulse_metrics(json.loads(INPUT),head_sha=head,observed_ci={})
        self.assertIsNone(receipt["workflow_pass_pct"])
        self.assertIsNone(receipt["todo_closed"])
        self.assertIsNone(receipt["crew_launches"])
    def test_pulse_rejects_cross_head_green(self):
        head="269de48db9b70a91383b2fcdf8822ec0e6496634"
        with self.assertRaises(ValueError):
            core.pulse_metrics(json.loads(INPUT),head_sha=head,observed_ci={
                "1":{"source_sha":"0"*40,"conclusion":"success",
                     "url":"https://github.com/GBOGEB/ABACUS/actions/runs/1"}
            })
    def test_pulse_rejects_pending_as_terminal(self):
        head="269de48db9b70a91383b2fcdf8822ec0e6496634"
        with self.assertRaises(ValueError):
            core.pulse_metrics(json.loads(INPUT),head_sha=head,observed_ci={
                "1":{"source_sha":head,"conclusion":"pending",
                     "url":"https://github.com/GBOGEB/ABACUS/actions/runs/1"}
            })
    def test_scope_changed_does_not_claim_uplift(self):
        ledger=json.loads(INPUT)
        before=core.pulse_metrics(ledger,head_sha="0"*40,observed_ci={})
        after=core.pulse_metrics(ledger,head_sha="1"*40,observed_ci={})
        delta=core.compare_pulses(before,after)
        self.assertFalse(delta["same_exact_head_and_run_set"])
        self.assertIsNone(delta["workflow_pass_delta"])
        self.assertIsNone(delta["coverage_delta"])

if __name__=="__main__":
    unittest.main()
