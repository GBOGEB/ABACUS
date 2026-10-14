"""TOP21 census: denominator separation, provenance rejection, deterministic replay."""
import copy
import pathlib
import sys
import tempfile
import unittest
import json

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from top21_rollout import rollout_census, InvalidCensus, RANK_SCHEMA, RECEIPT_SCHEMA
from build_top21_rollout import main

REPOS = ["GBOGEB/ABACUS", "GBOGEB/CODEX", "GBOGEB/cryoplant-project",
         "GBOGEB/CODESPACES_jyperter", "GBOGEB/morris.js"]


def contract():
    return {"schema_version": "1.0.0",
            "authority": {"authority_transfer": False, "formal_credit_delta": 0,
                          "engineering_credit_delta": 0},
            "rollout": {"repository_candidates": list(REPOS),
                        "top21_definition": "pending owner approval"}}


def receipt():
    return {"repository": REPOS[0], "source_sha": "a" * 40, "run_id": 123,
            "job_id": 456, "kind": "CI",
            "evidence_url": "https://github.com/GBOGEB/ABACUS/actions/runs/123"}


def ranked():
    return {"schema": RANK_SCHEMA, "items": [
        {"rank": 1, "root_candidate_id": "ABACUS-RC-2026-0001",
         "origin_repository": REPOS[0]}]}


class Top21Tests(unittest.TestCase):
    def test_nomination_is_not_deployment(self):
        r = rollout_census(contract())
        self.assertEqual(r["root_ranking"]["capacity"], 21)
        self.assertEqual(r["repository_rollout"]["nominated_inventory"], 5)
        self.assertEqual(r["repository_rollout"]["repositories_with_declared_receipts"], 0)
        self.assertIsNone(r["repository_rollout"]["authenticated_deployments"])
        self.assertIsNone(r["evidence"]["live_worker_count"])
        self.assertEqual(r["admission"], "HOLD")

    def test_receipt_is_not_native_proof(self):
        r = rollout_census(contract(), {"schema": RECEIPT_SCHEMA, "items": [receipt()]})
        d = r["repository_rollout"]
        self.assertEqual(d["declared_receipt_presence_pct"], 20)
        self.assertEqual(d["source_bound_manifest_count"], 1)
        self.assertIsNone(d["verified_deployment_coverage_pct"])

    def test_rank_cannot_confirm_cause(self):
        r = rollout_census(contract(), ranking=ranked())
        self.assertEqual(r["root_ranking"]["capacity_fill_pct"], 4.76)
        self.assertIsNone(r["root_ranking"]["approved_or_confirmed_roots"])

    def test_duplicates_and_overflow_fail(self):
        for field, value in (("rank", 1), ("root_candidate_id", "ABACUS-RC-2026-0001")):
            x = ranked()
            y = dict(x["items"][0])
            y.update(rank=2, root_candidate_id="ABACUS-RC-2026-0002")
            y[field] = value
            x["items"].append(y)
            with self.subTest(field=field), self.assertRaises(InvalidCensus):
                rollout_census(contract(), ranking=x)
        x = {"schema": RANK_SCHEMA, "items": [{"rank": i,
             "root_candidate_id": f"RC-{i:03d}", "origin_repository": REPOS[0]}
             for i in range(1, 23)]}
        with self.assertRaises(InvalidCensus):
            rollout_census(contract(), ranking=x)

    def test_invalid_source_binding_fails(self):
        for delta in ({"source_sha": "HEAD"}, {"run_id": False},
                      {"job_id": 0}, {"evidence_url": "https://github.com.evil/x"},
                      {"repository": "GBOGEB/UNAPPROVED"}, {"verified": True}):
            x = dict(receipt(), **delta)
            with self.subTest(delta=delta), self.assertRaises(InvalidCensus):
                rollout_census(contract(), {"schema": RECEIPT_SCHEMA, "items": [x]})

    def test_duplicate_or_mixed_heads_fail(self):
        x = receipt()
        y = dict(x, source_sha="b" * 40, run_id=124,
                 evidence_url="https://github.com/GBOGEB/ABACUS/actions/runs/124")
        for pair in ([x, x], [x, y]):
            with self.subTest(pair=pair), self.assertRaises(InvalidCensus):
                rollout_census(contract(), {"schema": RECEIPT_SCHEMA, "items": pair})

    def test_zero_changed_lines_na(self):
        x = dict(receipt(), kind="COVERAGE", artifact_sha256="c" * 64,
                 measurement={"scope": "changed_lines", "unit": "lines",
                              "covered": 0, "eligible": 0, "config_digest": "d" * 64,
                              "tool_version": "coverage-7", "test_selection": "focused"})
        r = rollout_census(contract(), {"schema": RECEIPT_SCHEMA, "items": [x]})
        self.assertIsNone(r["repository_rollout"]["inventory"][0]["coverage_by_scope"][0]["reported_pct"])
        x["measurement"]["scope"] = "broad"
        with self.assertRaises(InvalidCensus):
            rollout_census(contract(), {"schema": RECEIPT_SCHEMA, "items": [x]})

    def test_authority_never_imported(self):
        x = contract()
        x["authority"]["authority_transfer"] = True
        with self.assertRaises(InvalidCensus):
            rollout_census(x)

    def test_stable_check_mode(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            contract_file, report = root / "contract.json", root / "report.json"
            contract_file.write_text(json.dumps(contract()), encoding="utf-8")
            args = ["--contract", str(contract_file), "--output", str(report)]
            self.assertEqual(main(args), 0)
            before = report.read_bytes()
            self.assertEqual(main(args + ["--check"]), 0)
            self.assertEqual(main(args), 0)
            self.assertEqual(before, report.read_bytes())
            report.write_text("stale", encoding="utf-8")
            self.assertEqual(main(args + ["--check"]), 1)


if __name__ == "__main__":
    unittest.main()
