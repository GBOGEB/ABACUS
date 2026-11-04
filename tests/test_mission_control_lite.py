import json
import sys
import tempfile
import unittest
from contextlib import closing, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from mission_control_lite.core import census, ingest, receipt, verify
from mission_control_lite.policy import authorize


class TestMissionControlLite(unittest.TestCase):
    def test_native_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "output.json"
            p.write_text('{"ok":true}')
            r = receipt("m1", "t1", "root1", "a" * 40, "run1", [p])
            self.assertTrue(verify(r, d))
            p.write_text('{"ok":false}')
            self.assertFalse(verify(r, d))
            p.write_text('{"ok":true}')
            self.assertTrue(verify(r, d))
            db = Path(d) / "registry.sqlite"
            ingest(db, r, d)
            result = census(db)
            self.assertEqual(result["verified_roots_with_receipts"], 1)
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

    def test_exact_duplicate_ingest_rejected_without_second_event(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "output.json"
            p.write_bytes(b"trusted")
            db = Path(d) / "registry.sqlite"
            r = receipt("m", "task", "root", "a" * 40, "42", [p])
            ingest(db, r, d)
            with self.assertRaisesRegex(ValueError, "duplicate or conflicting"):
                ingest(db, r, d)
            import sqlite3

            with closing(sqlite3.connect(db)) as connection:
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM receipts").fetchone()[0], 1
                )
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM events").fetchone()[0], 1
                )
            self.assertEqual(census(db)["verified_roots_with_receipts"], 1)
            self.assertFalse(census(db)["roots"][0]["closed"])

    def test_conflicting_receipt_identity_rejected_with_rollback(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "output.json"
            p.write_bytes(b"trusted")
            db = Path(d) / "registry.sqlite"
            original = receipt("m", "task", "root", "a" * 40, "42", [p])
            ingest(db, original, d)
            # Keep the same unique mission/task/run, but forge root and SHA.
            conflict = json.loads(json.dumps(original))
            conflict["root_id"] = "forged-root"
            conflict["source_sha"] = "b" * 40
            with self.assertRaisesRegex(ValueError, "duplicate or conflicting"):
                ingest(db, conflict, d)
            import sqlite3

            with closing(sqlite3.connect(db)) as connection:
                rows = connection.execute(
                    "SELECT root, source_sha FROM receipts"
                ).fetchall()
                self.assertEqual(rows, [("root", "a" * 40)])
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM events").fetchone()[0], 1
                )

    def test_external_actor_authorization_negative(self):
        scope = {
            "repository": "GBOGEB/ABACUS",
            "source_sha": "a" * 40,
            "write": False,
            "actor": "untrusted-external",
        }
        for action in ("merge", "modify_ruleset", "shell", "patch", "ingest"):
            self.assertFalse(
                authorize(
                    action,
                    scope,
                    authenticated_actor="untrusted-external",
                    trusted_actors={"GBOGEB"},
                )
            )
        self.assertFalse(
            authorize(
                "test",
                scope,
                authenticated_actor="untrusted-external",
                trusted_actors={"GBOGEB"},
            )
        )

    def test_ingest_rejects_missing_outside_and_length_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "trusted"
            root.mkdir()
            other = Path(d) / "other"
            other.mkdir()
            p = root / "evidence.json"
            p.write_bytes(b"payload")
            db = Path(d) / "registry.sqlite"
            valid = receipt("m", "t", "r", "a" * 40, "run", [p])
            self.assertTrue(verify(valid, root))
            cases = []
            missing = json.loads(json.dumps(valid))
            missing["artifacts"][0]["path"] = str(root / "absent.json")
            cases.append(missing)
            bad_length = json.loads(json.dumps(valid))
            bad_length["artifacts"][0]["bytes"] += 1
            cases.append(bad_length)
            outside = other / "evidence.json"
            outside.write_bytes(p.read_bytes())
            escapes = json.loads(json.dumps(valid))
            escapes["artifacts"][0]["path"] = str(outside)
            cases.append(escapes)
            for candidate in cases:
                with self.subTest(candidate=candidate["artifacts"][0]["path"]):
                    with self.assertRaises(ValueError):
                        ingest(db, candidate, root)
            self.assertEqual(census(db)["verified_roots_with_receipts"], 0)

    def test_sqlite_handle_reopens_and_census_is_nonclosure(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "output.json"
            p.write_text('{"ok":true}')
            db = Path(d) / "registry.sqlite"
            for task in ("one", "two"):
                ingest(db, receipt("mission", task, "root", "a" * 40, task, [p]), d)
                self.assertEqual(census(db)["roots"][0]["closed"], False)
            self.assertEqual(census(db)["roots"][0]["tasks_with_receipts"], 2)
            db.unlink()
            self.assertFalse(db.exists())

    def test_actor_scope_cannot_self_assert_trust(self):
        scope = {
            "repository": "GBOGEB/ABACUS",
            "source_sha": "a" * 40,
            "write": False,
            "actor": "GBOGEB",
            "trusted": True,
        }
        self.assertFalse(authorize("test", scope))
        self.assertFalse(
            authorize(
                "test", scope, authenticated_actor="external", trusted_actors={"GBOGEB"}
            )
        )
        self.assertTrue(
            authorize(
                "test", scope, authenticated_actor="GBOGEB", trusted_actors={"GBOGEB"}
            )
        )

    def test_receipt_rejects_same_size_byte_forgery(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "payload.json"
            p.write_bytes(b"first")
            r = receipt("m", "t", "root", "a" * 40, "run", [p])
            p.write_bytes(b"other")
            self.assertEqual(p.stat().st_size, r["artifacts"][0]["bytes"])
            with self.assertRaises(ValueError):
                ingest(Path(d) / "db.sqlite", r, d)

    def test_receipt_rejects_parent_directory_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "trusted"
            root.mkdir()
            outside = Path(d) / "payload"
            outside.write_bytes(b"proof")
            r = receipt("m", "t", "root", "a" * 40, "run", [outside])
            r["artifacts"][0]["path"] = "../payload"
            with self.assertRaises(ValueError):
                ingest(Path(d) / "db.sqlite", r, root)

    def test_receipt_rejects_symlink_escape(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "trusted"
            root.mkdir()
            outside = Path(d) / "payload"
            outside.write_bytes(b"proof")
            link = root / "payload"
            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            r = receipt("m", "t", "root", "a" * 40, "run", [outside])
            r["artifacts"][0]["path"] = "payload"
            with self.assertRaises(ValueError):
                ingest(Path(d) / "db.sqlite", r, root)

    def test_cli_receipt_binds_multiple_telemetry_outputs(self):
        from mission_control_lite.cli import main

        with tempfile.TemporaryDirectory() as d:
            first = Path(d) / "output.json"
            second = Path(d) / "coverage-pulse.json"
            first.write_bytes(b"proof")
            second.write_bytes(b'{"coverage":"UNKNOWN"}')
            rec = Path(d) / "receipt.json"
            with patch.object(
                sys,
                "argv",
                [
                    "mcl",
                    "produce",
                    "--mission",
                    "m",
                    "--task",
                    "t",
                    "--root",
                    "r",
                    "--sha",
                    "a" * 40,
                    "--run",
                    "1",
                    "--output",
                    str(first),
                    "--output",
                    str(second),
                    "--receipt",
                    str(rec),
                ],
            ):
                main()
            content = json.loads(rec.read_text())
            self.assertEqual(len(content["artifacts"]), 2)
            self.assertTrue(verify(content, d))
            second.write_bytes(b'{"coverage":"FORGED"}')
            with self.assertRaises(ValueError):
                ingest(Path(d) / "registry.sqlite", content, d)

    def test_empty_output_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "empty"
            p.write_bytes(b"")
            with self.assertRaises(ValueError):
                receipt("m", "t", "r", "a" * 40, "run", [p])

    def test_cli_produce_ingest_census(self):
        from mission_control_lite.cli import main

        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / "output.json"
            output.write_text('{"ok":true}')
            rec = Path(d) / "receipt.json"
            db = Path(d) / "registry.sqlite"
            with patch.object(
                sys,
                "argv",
                [
                    "mcl",
                    "produce",
                    "--mission",
                    "m",
                    "--task",
                    "t",
                    "--root",
                    "r",
                    "--sha",
                    "a" * 40,
                    "--run",
                    "1",
                    "--output",
                    str(output),
                    "--receipt",
                    str(rec),
                ],
            ):
                main()
            self.assertTrue(verify(json.loads(rec.read_text()), d))
            with patch.object(
                sys,
                "argv",
                [
                    "mcl",
                    "ingest",
                    str(rec),
                    "--db",
                    str(db),
                    "--artifact-root",
                    d,
                ],
            ):
                main()
            buf = StringIO()
            with (
                patch.object(
                    sys,
                    "argv",
                    [
                        "mcl",
                        "census",
                        "--db",
                        str(db),
                    ],
                ),
                redirect_stdout(buf),
            ):
                main()
            data = json.loads(buf.getvalue())
            self.assertEqual(data["verified_roots_with_receipts"], 1)
            self.assertFalse(data["roots"][0]["closed"])

    def test_cli_rejects_invalid_receipt(self):
        from mission_control_lite.cli import main

        with tempfile.TemporaryDirectory() as d:
            rec = Path(d) / "invalid.json"
            rec.write_text("{}")
            with patch.object(
                sys,
                "argv",
                [
                    "mcl",
                    "ingest",
                    str(rec),
                    "--db",
                    str(Path(d) / "registry.sqlite"),
                    "--artifact-root",
                    d,
                ],
            ):
                with self.assertRaises(ValueError):
                    main()

    def test_agent_denials(self):
        s = {"repository": "GBOGEB/ABACUS", "source_sha": "a" * 40, "write": False}
        for action in ("merge", "modify_ruleset", "shell", "patch"):
            self.assertFalse(authorize(action, s))
        self.assertTrue(
            authorize(
                "test", s, authenticated_actor="GBOGEB", trusted_actors={"GBOGEB"}
            )
        )
        self.assertFalse(
            authorize(
                "test",
                {**s, "write": True},
                authenticated_actor="GBOGEB",
                trusted_actors={"GBOGEB"},
            )
        )
        self.assertFalse(authorize("test", s))
        self.assertFalse(
            authorize(
                "test", s, authenticated_actor="external", trusted_actors={"GBOGEB"}
            )
        )


if __name__ == "__main__":
    unittest.main()
