"""Negative and positive proof for the MIP wave-series read-only consumer."""

import hashlib
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest import mock

PATH = pathlib.Path(__file__).resolve().parents[1] / "tools/mip2/mip_wave_series.py"
SPEC = importlib.util.spec_from_file_location("mip_wave_series", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
SHA_D = "d" * 40
STATES = MODULE.STATES


def create_wave(
    root,
    label,
    base,
    head,
    roots=None,
    fingerprints=None,
    coverage=None,
    tests=None,
    merge_admitted=False,
):
    target = root / label
    target.mkdir()
    roots = roots if roots is not None else {"R1": "OPEN"}
    fingerprints = fingerprints if fingerprints is not None else {"R1": ["F1", "F1"]}
    coverage = coverage if coverage is not None else {}
    tests = tests if tests is not None else {"passed": 3, "failed": 0, "skipped": 0}
    row = {
        "schema": MODULE.PULSE_SCHEMA,
        "repository": "GBOGEB/ABACUS",
        "base_sha": base,
        "head_sha": head,
        "wave_id": label,
        "roots": [
            {
                "root_id": rid,
                "owner": "MIP",
                "status": state,
                "fingerprints": fingerprints.get(rid, []),
            }
            for rid, state in roots.items()
        ],
        "first_reds": (
            [{"root_id": "R1", "fingerprint": "F1", "classification": "inherited"}]
            if "R1" in roots
            else []
        ),
        "workers": [],
        "tests": tests,
        "coverage": coverage,
        "admission": {"merge_admitted": merge_admitted},
    }
    if merge_admitted:
        row["admission"]["verified_main_sha"] = head
    for root_item in row["roots"]:
        if root_item["status"] == "ROOT_CLOSED":
            root_item["closure_proof"] = {
                "main_sha": head,
                "native_run_url": "https://github.com/example/actions/runs/1",
                "artifact_sha256": "f" * 64,
            }
    raw = json.dumps(row, sort_keys=True).encode("utf-8")
    (target / "wave-input.json").write_bytes(raw)
    counts = {s.lower(): list(roots.values()).count(s) for s in STATES}
    if not coverage:
        cv = {"status": "UNKNOWN", "reason": "missing comparable evidence"}
    elif all(
        coverage["before"][k] == coverage["after"][k]
        for k in ("scope", "config_id", "total_lines", "total_branches")
    ):
        a, b = coverage["before"], coverage["after"]
        denom = b["total_lines"] + b["total_branches"]
        cv = {
            "status": "COMPARABLE",
            "scope": b["scope"],
            "config_id": b["config_id"],
            "before_sha": base,
            "after_sha": head,
            "delta_lines": b["covered_lines"] - a["covered_lines"],
            "delta_branches": b["covered_branches"] - a["covered_branches"],
            "delta_pp": round(
                100
                * (
                    b["covered_lines"]
                    + b["covered_branches"]
                    - a["covered_lines"]
                    - a["covered_branches"]
                )
                / denom,
                8,
            ),
        }
    else:
        cv = {"status": "INCOMPARABLE", "reason": "scope/config/denominator mismatch"}
    pulse = {
        "schema": MODULE.PULSE_SCHEMA,
        "repository": row["repository"],
        "wave_id": label,
        "base_sha": base,
        "head_sha": head,
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "coverage": cv,
        "tests": tests,
        "worker_count": 0,
        "first_reds": row["first_reds"],
        "root_counts": counts,
        "merge_admitted": merge_admitted,
    }
    backlog = {
        "schema": MODULE.BACKLOG_SCHEMA,
        "repository": row["repository"],
        "wave_id": label,
        "head_sha": head,
        "distinct_root_counts": counts,
        "fingerprint_manifestations": sum(len(fingerprints.get(r, [])) for r in roots),
        "formal_verified_closures": counts["root_closed"],
        "closure_disposition": (
            "EXACT_MAIN_PROVEN" if counts["root_closed"] else "NO_CLOSURE_CREDIT"
        ),
    }
    (target / "mip_wave_pulse.json").write_text(json.dumps(pulse))
    (target / "mip_backlog_delta.json").write_text(json.dumps(backlog))
    return target


def change_file(folder, name, transform):
    path = folder / name
    payload = json.loads(path.read_text())
    transform(payload)
    path.write_text(json.dumps(payload))


def coverage_pair(base, head, denominator=150, configuration="cfg"):
    before = {
        "scope": "299-matched",
        "config_id": configuration,
        "source_sha": base,
        "covered_lines": 60,
        "total_lines": 100,
        "covered_branches": 20,
        "total_branches": denominator - 100,
    }
    after = dict(before, source_sha=head, covered_lines=65, covered_branches=22)
    return {"before": before, "after": after}


class WaveSeriesTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = pathlib.Path(self.folder.name)

    def test_two_pulses_track_root_and_fingerprint_without_credit(self):
        a = create_wave(self.root, "W1", SHA_A, SHA_B)
        b = create_wave(
            self.root,
            "W2",
            SHA_B,
            SHA_C,
            roots={"R1": "REPAIRED", "R2": "OPEN"},
            fingerprints={"R1": ["F1"], "R2": ["F2"]},
            coverage=coverage_pair(SHA_B, SHA_C),
        )
        out = MODULE.rollup([a, b], "SYNTHETIC")
        self.assertEqual(out["wave_count"], 2)
        self.assertEqual(out["waves"][1]["first_seen_fingerprint_pairs"], 1)
        self.assertEqual(out["waves"][1]["repeated_fingerprint_pairs"], 1)
        self.assertEqual(out["waves"][1]["root_ids_added"], ["R2"])
        self.assertEqual(out["waves"][1]["coverage"]["delta_pp"], 4.66666667)
        self.assertEqual(out["waves"][1]["coverage_gain_credited"], 0)
        self.assertIsNone(out["cumulative"]["verified_root_closure"])
        self.assertEqual(out["cumulative"]["process_stability_m2"], "HOLD")
        self.assertIn("SYNTHETIC", MODULE.as_markdown(out))

    def test_unverified_operational_source_not_promoted(self):
        wave = create_wave(self.root, "W1", SHA_A, SHA_B)
        report = MODULE.rollup([wave], "OPERATIONAL_UNVERIFIED")
        self.assertIsNone(report["waves"][0]["native_receipt_verified"])
        self.assertEqual(report["cumulative"]["merge_admission"], "HOLD")

    def test_duplicate_id_fails(self):
        a = create_wave(self.root, "W1", SHA_A, SHA_B)
        with self.assertRaisesRegex(ValueError, "duplicate wave ID"):
            MODULE.rollup([a, a], "SYNTHETIC")

    def test_sha_chain_mismatch_fails(self):
        a = create_wave(self.root, "W1", SHA_A, SHA_B)
        b = create_wave(self.root, "W2", SHA_D, SHA_C)
        with self.assertRaisesRegex(ValueError, "non-contiguous"):
            MODULE.rollup([a, b], "SYNTHETIC")

    def test_input_bytes_digest_tamper_fails(self):
        a = create_wave(self.root, "W1", SHA_A, SHA_B)
        path = a / "wave-input.json"
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "input bytes"):
            MODULE.rollup([a], "SYNTHETIC")

    def test_backlog_count_mismatch_fails(self):
        a = create_wave(self.root, "W1", SHA_A, SHA_B)
        change_file(
            a,
            "mip_backlog_delta.json",
            lambda x: x["distinct_root_counts"].update({"open": 99}),
        )
        with self.assertRaisesRegex(ValueError, "root census mismatch"):
            MODULE.rollup([a], "SYNTHETIC")

    def test_backlog_occurrences_mismatch_fails(self):
        a = create_wave(self.root, "W1", SHA_A, SHA_B)
        change_file(
            a,
            "mip_backlog_delta.json",
            lambda x: x.update({"fingerprint_manifestations": 0}),
        )
        with self.assertRaisesRegex(ValueError, "manifestation"):
            MODULE.rollup([a], "SYNTHETIC")

    def test_report_false_coverage_delta_fails(self):
        a = create_wave(
            self.root, "W1", SHA_A, SHA_B, coverage=coverage_pair(SHA_A, SHA_B)
        )
        change_file(
            a, "mip_wave_pulse.json", lambda x: x["coverage"].update({"delta_pp": 30.0})
        )
        with self.assertRaisesRegex(ValueError, "delta mismatch"):
            MODULE.rollup([a], "SYNTHETIC")

    def test_changed_denominator_is_incomparable(self):
        pair = coverage_pair(SHA_A, SHA_B)
        pair["after"]["total_lines"] = 110
        a = create_wave(self.root, "W1", SHA_A, SHA_B, coverage=pair)
        report = MODULE.rollup([a], "SYNTHETIC")
        self.assertEqual(report["waves"][0]["coverage"]["status"], "INCOMPARABLE")
        self.assertEqual(report["waves"][0]["coverage_gain_credited"], 0)

    def test_wrong_coverage_sha_fails(self):
        pair = coverage_pair(SHA_A, SHA_B)
        pair["after"]["source_sha"] = SHA_D
        a = create_wave(self.root, "W1", SHA_A, SHA_B, coverage=pair)
        with self.assertRaisesRegex(ValueError, "coverage not bound"):
            MODULE.rollup([a], "SYNTHETIC")

    def test_disappearance_not_assigned_root_closure(self):
        a = create_wave(self.root, "W1", SHA_A, SHA_B)
        b = create_wave(self.root, "W2", SHA_B, SHA_C, roots={}, fingerprints={})
        out = MODULE.rollup([a, b], "SYNTHETIC")
        self.assertEqual(
            out["waves"][1]["root_ids_disappeared_without_closure_credit"],
            ["R1"],
        )
        self.assertEqual(out["waves"][1]["formal_root_closure_delta_credited"], 0)

    def test_source_claimed_closure_never_formal_credit(self):
        a = create_wave(self.root, "W1", SHA_A, SHA_B)
        b = create_wave(
            self.root,
            "W2",
            SHA_B,
            SHA_C,
            roots={"R1": "ROOT_CLOSED"},
            merge_admitted=True,
        )
        out = MODULE.rollup([a, b], "OPERATIONAL_UNVERIFIED")
        self.assertEqual(out["waves"][1]["source_claimed_closure_transitions"], ["R1"])
        self.assertEqual(out["waves"][1]["formal_root_closure_delta_credited"], 0)

    def test_no_closure_without_even_source_admission(self):
        a = create_wave(self.root, "W1", SHA_A, SHA_B, roots={"R1": "ROOT_CLOSED"})
        with self.assertRaisesRegex(
            ValueError, "root closure requires source-admitted"
        ):
            MODULE.rollup([a], "SYNTHETIC")

    def test_forged_root_closure_main_proof_rejected(self):
        a = create_wave(
            self.root,
            "W1",
            SHA_A,
            SHA_B,
            roots={"R1": "ROOT_CLOSED"},
            merge_admitted=True,
        )
        source = a / "wave-input.json"
        payload = json.loads(source.read_text())
        payload["roots"][0]["closure_proof"]["main_sha"] = SHA_D
        source.write_text(json.dumps(payload))
        change_file(
            a,
            "mip_wave_pulse.json",
            lambda x: x.update(
                {"input_sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
            ),
        )
        with self.assertRaisesRegex(ValueError, "closure main SHA disagrees"):
            MODULE.rollup([a], "OPERATIONAL_UNVERIFIED")

    def test_unsupported_repo_fails(self):
        a = create_wave(self.root, "W1", SHA_A, SHA_B)
        change_file(
            a, "mip_wave_pulse.json", lambda x: x.update({"repository": "GBOGEB/CODEX"})
        )
        with self.assertRaisesRegex(ValueError, "disagree"):
            MODULE.rollup([a], "SYNTHETIC")

    def test_cli_generates_json_and_markdown(self):
        a = create_wave(self.root, "W1", SHA_A, SHA_B)
        out = self.root / "out"
        with (
            mock.patch.object(
                sys,
                "argv",
                [
                    "mip_wave_series",
                    "--wave-dir",
                    str(a),
                    "--classification",
                    "SYNTHETIC",
                    "--output-dir",
                    str(out),
                ],
            ),
            redirect_stdout(StringIO()) as stdout,
        ):
            MODULE.main()
        self.assertEqual(
            json.loads((out / "mip_wave_series.json").read_text())["wave_count"], 1
        )
        self.assertIn("SYNTHETIC", (out / "mip_wave_series.md").read_text())
        self.assertEqual(json.loads(stdout.getvalue())["native_verified"], None)

    def test_invalid_classification_fails(self):
        a = create_wave(self.root, "W1", SHA_A, SHA_B)
        with self.assertRaisesRegex(ValueError, "classification"):
            MODULE.rollup([a], "ACCEPTED")

    def test_symlink_input_fails_closed(self):
        a = create_wave(self.root, "W1", SHA_A, SHA_B)
        other = self.root / "copy.json"
        orig = a / "wave-input.json"
        other.write_bytes(orig.read_bytes())
        orig.unlink()
        orig.symlink_to(other)
        with self.assertRaisesRegex(ValueError, "linked input"):
            MODULE.rollup([a], "SYNTHETIC")


if __name__ == "__main__":
    unittest.main()
