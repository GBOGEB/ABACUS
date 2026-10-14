import tempfile
import unittest
from pathlib import Path
from mission_control_lite.core import receipt, verify, ingest, census
from mission_control_lite.policy import authorize
class TestMissionControlLite(unittest.TestCase):
    def test_native_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"output.json"; p.write_text('{"ok":true}')
            r=receipt("m1","t1","root1","a"*40,"run1",[p])
            self.assertTrue(verify(r))
            db=Path(d)/"registry.sqlite"
            ingest(db,r)
            result=census(db)
            self.assertEqual(result["verified_roots_with_receipts"],1)
            self.assertFalse(result["roots"][0]["closed"])
    def test_empty_output_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"empty";p.write_bytes(b"")
            with self.assertRaises(ValueError):
                receipt("m","t","r","a"*40,"run",[p])
    def test_agent_denials(self):
        s={"repository":"GBOGEB/ABACUS","source_sha":"a"*40,"write":False}
        for action in ("merge","modify_ruleset","shell","patch"):
            self.assertFalse(authorize(action,s))
        self.assertTrue(authorize("test",s))
        self.assertFalse(authorize("test",{**s,"write":True}))
if __name__=="__main__":unittest.main()
