import tempfile
import json
import sys
from unittest.mock import patch
from contextlib import redirect_stdout
from io import StringIO
import unittest
from pathlib import Path
from mission_control_lite.core import receipt, verify, ingest, census
from mission_control_lite.policy import authorize
class TestMissionControlLite(unittest.TestCase):
    def test_native_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"output.json"; p.write_text('{"ok":true}')
            r=receipt("m1","t1","root1","a"*40,"run1",[p])
            self.assertTrue(verify(r, d))
            p.write_text('{"ok":false}')
            self.assertFalse(verify(r, d))
            p.write_text('{"ok":true}')
            self.assertTrue(verify(r, d))
            db=Path(d)/"registry.sqlite"
            ingest(db,r,d)
            result=census(db)
            self.assertEqual(result["verified_roots_with_receipts"],1)
            self.assertFalse(result["roots"][0]["closed"])
    def test_core_ingest_rejects_forgery_and_missing_trust_root(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "output.json"
            p.write_text('{"ok":true}')
            db = Path(d) / "registry.sqlite"
            r = receipt("m", "t", "root", "a" * 40, "1", [p])
            with self.assertRaises(ValueError):
                ingest(db, r)
            tampered = json.loads(json.dumps(r))
            tampered["artifacts"][0]["sha256"] = "0" * 64
            with self.assertRaises(ValueError):
                ingest(db, tampered, d)
            p.write_text('{"ok":false}')
            with self.assertRaises(ValueError):
                ingest(db, r, d)
            self.assertEqual(census(db)["verified_roots_with_receipts"], 0)

    def test_external_actor_authorization_negative(self):
        scope = {"repository": "GBOGEB/ABACUS", "source_sha": "a" * 40,
                 "write": False, "actor": "untrusted-external"}
        for action in ("merge", "modify_ruleset", "shell", "patch", "ingest"):
            self.assertFalse(authorize(action, scope))

    def test_empty_output_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"empty";p.write_bytes(b"")
            with self.assertRaises(ValueError):
                receipt("m","t","r","a"*40,"run",[p])
    def test_cli_produce_ingest_census(self):
        from mission_control_lite.cli import main
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / "output.json"
            output.write_text('{"ok":true}')
            rec = Path(d) / "receipt.json"
            db = Path(d) / "registry.sqlite"
            with patch.object(sys, "argv", [
                "mcl", "produce", "--mission", "m", "--task", "t",
                "--root", "r", "--sha", "a" * 40, "--run", "1",
                "--output", str(output), "--receipt", str(rec),
            ]):
                main()
            self.assertTrue(verify(json.loads(rec.read_text()), d))
            with patch.object(sys, "argv", [
                "mcl", "ingest", str(rec), "--db", str(db), "--artifact-root", d,
            ]):
                main()
            buf = StringIO()
            with patch.object(sys, "argv", [
                "mcl", "census", "--db", str(db),
            ]), redirect_stdout(buf):
                main()
            data = json.loads(buf.getvalue())
            self.assertEqual(data["verified_roots_with_receipts"], 1)
            self.assertFalse(data["roots"][0]["closed"])

    def test_cli_rejects_invalid_receipt(self):
        from mission_control_lite.cli import main
        with tempfile.TemporaryDirectory() as d:
            rec = Path(d) / "invalid.json"
            rec.write_text("{}")
            with patch.object(sys, "argv", [
                "mcl", "ingest", str(rec), "--db",
                str(Path(d) / "registry.sqlite"), "--artifact-root", d,
            ]):
                with self.assertRaises(ValueError):
                    main()

    def test_agent_denials(self):
        s={"repository":"GBOGEB/ABACUS","source_sha":"a"*40,"write":False}
        for action in ("merge","modify_ruleset","shell","patch"):
            self.assertFalse(authorize(action,s))
        self.assertTrue(authorize("test",s))
        self.assertFalse(authorize("test",{**s,"write":True}))
if __name__=="__main__":unittest.main()
