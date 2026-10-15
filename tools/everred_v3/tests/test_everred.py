import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import everred

SCHEMA = everred.SCHEMA
InvalidEvidence = everred.InvalidEvidence
append_event = everred.append_event
coverage_rate = everred.coverage_rate
overlap = everred.overlap
read_ledger = everred.read_ledger
snapshot = everred.snapshot
validate_event = everred.validate_event

SHA = "e9f34b22967064c779891a4d2ac40541f370e812"
WHEN = "2026-10-14T08:04:49Z"


def event(kind="note", id="unit-0001", **args):
    e = {
        "schema": SCHEMA,
        "id": id,
        "kind": kind,
        "occurred_at": WHEN,
        "repo": "GBOGEB/ABACUS",
        "provenance": "proposed",
        "evidence": {},
    }
    e.update(args)
    return e


class EvidenceContract(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.p = pathlib.Path(self.d.name) / "ledger.jsonl"

    def tearDown(self):
        self.d.cleanup()

    def lease(self, id, root, path, key, authorized=True):
        return event(
            "lease_acquired",
            id=id,
            root_id=root,
            sha=SHA,
            evidence={
                "principal": "worker-a",
                "paths": [path],
                "idempotency_key": key,
                "authorized": authorized,
            },
        )

    def test_roundtrip(self):
        append_event(self.p, event())
        self.assertEqual(len(read_ledger(self.p)), 1)

    def test_tamper_hash_detected(self):
        append_event(self.p, event())
        x = self.p.read_text()
        self.p.write_text(x.replace("unit-0001", "unit-0002"))
        with self.assertRaisesRegex(InvalidEvidence, "tampered"):
            read_ledger(self.p)

    def test_invalid_schema(self):
        e = event()
        e["schema"] = "old"
        with self.assertRaises(InvalidEvidence):
            validate_event(e)

    def test_missing_provenance(self):
        e = event()
        e.pop("provenance")
        with self.assertRaises(InvalidEvidence):
            validate_event(e)

    def test_duplicate_event_rejected(self):
        append_event(self.p, event())
        with self.assertRaisesRegex(InvalidEvidence, "duplicate"):
            append_event(self.p, event())

    def test_conflicting_leases_blocked(self):
        append_event(self.p, self.lease("lease-1", "r1", "src/abacus", "k1"))
        with self.assertRaisesRegex(InvalidEvidence, "overlapping"):
            append_event(
                self.p, self.lease("lease-2", "r2", "src/abacus/pipeline.py", "k2")
            )

    def test_disjoint_leases_allowed(self):
        append_event(self.p, self.lease("lease-1", "r1", "src/abacus", "k1"))
        append_event(self.p, self.lease("lease-2", "r2", "tests/scanner", "k2"))
        self.assertEqual(len(read_ledger(self.p)), 2)

    def test_unprivileged_mutation_rejected(self):
        with self.assertRaisesRegex(InvalidEvidence, "authorized"):
            validate_event(self.lease("lease-1", "r1", "src/a", "k1", False))

    def test_duplicate_idempotency_rejected(self):
        append_event(self.p, self.lease("lease-1", "r1", "src/a", "k1"))
        with self.assertRaisesRegex(InvalidEvidence, "idempotency"):
            append_event(self.p, self.lease("lease-2", "r2", "src/b", "k1"))

    def test_release_reopens_path(self):
        append_event(self.p, self.lease("lease-1", "r1", "src/a", "k1"))
        append_event(
            self.p,
            event(
                "lease_released",
                id="release1",
                root_id="r1",
                evidence={"acquired_event_id": "lease-1"},
            ),
        )
        append_event(self.p, self.lease("lease-2", "r2", "src/a", "k2"))
        self.assertEqual(len(read_ledger(self.p)), 3)

    def test_unmatched_release_rejected(self):
        with self.assertRaisesRegex(InvalidEvidence, "without active"):
            append_event(self.p, event("lease_released", id="release1", root_id="r1"))

    def test_path_traversal_rejected(self):
        with self.assertRaisesRegex(InvalidEvidence, "unsafe"):
            validate_event(self.lease("lease-1", "r1", "../src", "k1"))

    def test_admission_missing_gates_rejected(self):
        e = event(
            "admission",
            sha=SHA,
            evidence={"decision": "ADMIT", "gates": {"security": "PASS"}},
        )
        with self.assertRaisesRegex(InvalidEvidence, "missing admission gates"):
            validate_event(e)

    def test_admission_unknown_blocked(self):
        gates = {
            k: "PASS"
            for k in (
                "exact_head_ci",
                "security",
                "coverage",
                "workflow_governance",
                "branch_protection",
                "independent_review",
                "review_conversations",
            )
        }
        gates["branch_protection"] = "UNKNOWN"
        e = event("admission", sha=SHA, evidence={"decision": "ADMIT", "gates": gates})
        with self.assertRaisesRegex(InvalidEvidence, "cannot admit"):
            validate_event(e)

    def test_proposal_cannot_admit_even_all_pass(self):
        gates = {
            k: "PASS"
            for k in (
                "exact_head_ci",
                "security",
                "coverage",
                "workflow_governance",
                "branch_protection",
                "independent_review",
                "review_conversations",
            )
        }
        e = event("admission", sha=SHA, evidence={"decision": "ADMIT", "gates": gates})
        with self.assertRaisesRegex(InvalidEvidence, "offline ledger"):
            validate_event(e)

    def test_hold_with_unknown_allowed(self):
        gates = {
            k: "UNKNOWN"
            for k in (
                "exact_head_ci",
                "security",
                "coverage",
                "workflow_governance",
                "branch_protection",
                "independent_review",
                "review_conversations",
            )
        }
        validate_event(
            event("admission", sha=SHA, evidence={"decision": "HOLD", "gates": gates})
        )

    def test_unknown_numeric_not_zero(self):
        e = event(
            "coverage",
            sha=SHA,
            evidence={
                "scope": "other",
                "unit": "lines",
                "covered": None,
                "eligible": None,
                "config_id": "unknown",
            },
        )
        validate_event(e)
        self.assertIsNone(coverage_rate(e))

    def test_invalid_denominator_zero(self):
        with self.assertRaisesRegex(InvalidEvidence, "denominator"):
            validate_event(
                event(
                    "coverage",
                    sha=SHA,
                    evidence={
                        "scope": "focused",
                        "unit": "lines",
                        "covered": 0,
                        "eligible": 0,
                        "config_id": "cfg",
                    },
                )
            )

    def test_missing_config_prohibited(self):
        with self.assertRaisesRegex(InvalidEvidence, "config identity"):
            validate_event(
                event(
                    "coverage",
                    sha=SHA,
                    evidence={
                        "scope": "focused",
                        "unit": "lines",
                        "covered": 1,
                        "eligible": 3,
                    },
                )
            )

    def test_scope_kept_separate(self):
        a = event(
            "coverage",
            sha=SHA,
            evidence={
                "scope": "focused",
                "unit": "statements",
                "covered": 49,
                "eligible": 61,
                "config_id": "f",
            },
        )
        b = event(
            "coverage",
            id="unit-0002",
            sha=SHA,
            evidence={
                "scope": "broad",
                "unit": "statements",
                "covered": 12731,
                "eligible": 29093,
                "config_id": "b",
            },
        )
        s = snapshot([a, b])
        self.assertEqual(len(s["coverage_scopes"]), 2)
        self.assertNotEqual(
            s["coverage_scopes"]["focused:statements"]["value"],
            s["coverage_scopes"]["broad:statements"]["value"],
        )

    def test_path_prefix_exact(self):
        self.assertTrue(overlap("src", "src/b"))
        self.assertFalse(overlap("src/a", "src/a2"))

    def test_missing_sha_blocked(self):
        with self.assertRaisesRegex(InvalidEvidence, "SHA"):
            validate_event(event("verification", evidence={}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
