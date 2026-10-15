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

if __name__=="__main__":
    unittest.main()
