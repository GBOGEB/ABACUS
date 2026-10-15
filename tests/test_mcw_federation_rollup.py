import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "tools" / "mcw_federation_rollup.py"
SPEC = importlib.util.spec_from_file_location("mcw", SOURCE)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
SHA = "a" * 40
OTHER = "b" * 40


def node(name="a", repo="GBOGEB/ABACUS", family="MCL", sha=SHA):
    return {"id": name, "repository": repo, "source_sha": sha, "family": family}


def proof(n, covered=6):
    return {"schema": M.PROOF_SCHEMA, "repository": n["repository"],
            "source_sha": n["source_sha"], "family": n["family"],
            "run_id": 8, "job_id": 9,
            "tests": {"required": 7, "passed": 7, "failed": 0, "skipped": 0},
            "coverage": {"scope_id": "src/MCL", "config_sha256": "f" * 64,
                         "files": ["core.py"], "covered_lines": covered,
                         "total_lines": 10, "covered_branches": 2,
                         "total_branches": 4}}


class FederationRollupTests(unittest.TestCase):
    def manifest(self, n, root, covered=6):
        content = json.dumps(proof(n, covered), sort_keys=True).encode()
        path = root / (n["id"] + ".json")
        path.write_bytes(content)
        n["artifact"] = {"path": path.name, "sha256": hashlib.sha256(content).hexdigest()}
        return n

    def test_breadth_depth_fanout_and_hold(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            first = self.manifest(node(), root)
            second = node("b", "GBOGEB/CODEX", "REX", OTHER)
            third = node("c", "GBOGEB/ABACUS", "LDAB", SHA)
            bundle = {"schema": M.INPUT_SCHEMA, "wave_id": "W1",
                      "nodes": [first, second, third],
                      "edges": [{"source": "a", "target": "b", "kind": "evidence"},
                                {"source": "a", "target": "c", "kind": "feedback"}]}
            result = M.rollup(bundle, root)
            self.assertEqual(result["counts"]["repositories"], 2)
            self.assertEqual(result["counts"]["families"], 3)
            self.assertEqual(result["counts"]["local_byte_verified_nodes"], 1)
            self.assertEqual(result["counts"]["declared_cross_repository_edges"], 1)
            self.assertEqual(result["counts"]["max_declared_outdegree"], 2)
            self.assertEqual(result["confirmed_root_closures"], 0)
            self.assertIsNone(result["active_runtime_workers"])
            self.assertEqual(result["merge_admission"], "HOLD")
            self.assertFalse(result["nodes"][0]["native_gha_authenticated"])

    def test_comparable_pulses_and_strict_scope(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            n = self.manifest(node(), root, covered=6)
            bundle = {"schema": M.INPUT_SCHEMA, "wave_id": "W1", "nodes": [n], "edges": []}
            old = M.rollup(bundle, root)
            self.manifest(n, root, covered=8)
            new = M.rollup({**bundle, "wave_id": "W2"}, root, old)
            self.assertEqual(new["coverage_deltas"]["a"]["status"], "COMPARABLE")
            self.assertEqual(new["coverage_deltas"]["a"]["line_delta_pp"], 20)
            incompatible = json.loads((root / "a.json").read_text())
            incompatible["coverage"]["scope_id"] = "different"
            raw = json.dumps(incompatible).encode()
            (root / "a.json").write_bytes(raw)
            n["artifact"]["sha256"] = hashlib.sha256(raw).hexdigest()
            again = M.rollup({**bundle, "wave_id": "W3"}, root, new)
            self.assertEqual(again["coverage_deltas"]["a"]["status"], "INCOMPARABLE")

    def test_forged_bytes_and_escape_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            n = self.manifest(node(), root)
            bundle = {"schema": M.INPUT_SCHEMA, "wave_id": "W1", "nodes": [n], "edges": []}
            (root / "a.json").write_text("forged")
            with self.assertRaises(ValueError):
                M.rollup(bundle, root)
            n["artifact"]["path"] = "../outside.json"
            with self.assertRaises(ValueError):
                M.rollup(bundle, root)

    def test_rejects_duplicate_or_dangling_nodes_edges(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            n = node()
            b = {"schema": M.INPUT_SCHEMA, "wave_id": "W", "nodes": [n, n], "edges": []}
            with self.assertRaises(ValueError):
                M.rollup(b, root)
            b["nodes"] = [n]
            b["edges"] = [{"source": "a", "target": "missing", "kind": "dependency"}]
            with self.assertRaises(ValueError):
                M.rollup(b, root)

    def test_rejects_invalid_native_denominators(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            n = node()
            p = proof(n)
            p["tests"]["passed"] = 8
            raw = json.dumps(p).encode()
            (root / "bad.json").write_bytes(raw)
            n["artifact"] = {"path": "bad.json", "sha256": hashlib.sha256(raw).hexdigest()}
            b = {"schema": M.INPUT_SCHEMA, "wave_id": "W", "nodes": [n], "edges": []}
            with self.assertRaises(ValueError):
                M.rollup(b, root)

    def test_proof_without_coverage_and_changed_member_family(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            n = self.manifest(node(), root)
            bundle = {"schema": M.INPUT_SCHEMA, "wave_id": "W1", "nodes": [n], "edges": []}
            old = M.rollup(bundle, root)
            n["family"] = "REX"
            raw = json.dumps(proof(n)).encode()
            (root / "a.json").write_bytes(raw)
            n["artifact"]["sha256"] = hashlib.sha256(raw).hexdigest()
            result = M.rollup({**bundle, "wave_id": "W2"}, root, old)
            self.assertEqual(result["coverage_deltas"]["a"]["status"], "INCOMPARABLE")
            val = json.loads(raw)
            val.pop("coverage")
            raw = json.dumps(val).encode()
            (root / "a.json").write_bytes(raw)
            n["artifact"]["sha256"] = hashlib.sha256(raw).hexdigest()
            result = M.rollup({**bundle, "wave_id": "W3"}, root, result)
            self.assertEqual(result["coverage_deltas"]["a"]["status"], "UNKNOWN")

    def test_main_cli_writes_nonadmitting_json(self):
        from unittest.mock import patch
        import sys
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            inp = root / "input.json"
            out = root / "report.json"
            inp.write_text(json.dumps({"schema": M.INPUT_SCHEMA, "wave_id": "W0",
                                       "nodes": [node()], "edges": []}))
            with patch.object(sys, "argv", [
                "mcw", "--input", str(inp), "--artifact-root", d,
                "--output", str(out),
            ]):
                M.main()
            self.assertEqual(json.loads(out.read_text())["merge_admission"], "HOLD")

    def test_rejects_bad_previous_schema_and_duplicate_edge(self):
        with tempfile.TemporaryDirectory() as d:
            b = {"schema": M.INPUT_SCHEMA, "wave_id": "W",
                 "nodes": [node(), node("b", family="MIP")],
                 "edges": [{"source": "a", "target": "b", "kind": "dependency"}]}
            with self.assertRaises(ValueError):
                M.rollup(b, d, previous={"schema": "forged"})
            b["edges"].append(b["edges"][0])
            with self.assertRaises(ValueError):
                M.rollup(b, d)

    def test_discovery_only_never_credited_as_execution(self):
        b = {"schema": M.INPUT_SCHEMA, "wave_id": "W1",
             "nodes": [node("ldab", family="LDAB")], "edges": []}
        with tempfile.TemporaryDirectory() as d:
            r = M.rollup(b, Path(d))
            self.assertEqual(r["counts"]["local_byte_verified_nodes"], 0)
            self.assertIsNone(r["authenticated_federation_receipts"])
            self.assertEqual(r["coverage_deltas"]["ldab"]["status"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
