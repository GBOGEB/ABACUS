"""Behavioral regression and negative evidence tests for V2 capsule producer.

This test source is a disjoint, test-only candidate. It asserts real replay
behaviour and explicitly does not confer repository admission or remote trust.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
GITHUB_CORE = ROOT / "tools" / "handover_v2" / "build_handover.py"
LOCAL_CORE = Path(__file__).with_name("build_handover.py")
SOURCE = GITHUB_CORE if GITHUB_CORE.exists() else LOCAL_CORE
SPEC = importlib.util.spec_from_file_location("handover_v2_scaled_producer", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("The canonical V2 producer is unavailable")
core = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(core)

HEAD = "a" * 40
OLD = "b" * 40
CONFIG = "c" * 64
UTC = "2026-10-16T08:00:00Z"


def evidence(ident="NATIVE", source=HEAD, kind="WORKFLOW_RUN", observation="REMOTE_OBSERVED"):
    return {
        "id": ident, "label": ident, "kind": kind, "observation": observation,
        "uri": "https://github.com/example/proof/actions/runs/123",
        "source_sha": source, "observed_at_utc": UTC, "run_id": 123,
        "run_attempt": 1, "job_id": None, "artifact_id": None,
        "event": "pull_request", "sha256": None, "note": "fixture only",
    }


def basis():
    return {
        "scope_id": "v2_line", "paths": ["tools/handover_v2/build_handover.py"],
        "unit_definition": "eligible_changed_source_lines", "instrumentor": "coverage.py",
        "instrumentor_version": "7.16.2", "configuration_sha256": CONFIG,
        "selection": "tests/test_handover_v2_scale.py",
    }


def metric(ident, source, n, d, state="MEASURED"):
    return {
        "id": ident, "label": ident, "state": state, "measure_type": "RATIO",
        "unit": "source-lines", "source_sha": source if state != "UNKNOWN" else None,
        "evidence_ids": ["NATIVE"] if source == HEAD and state != "UNKNOWN" else
                        (["HIST"] if state != "UNKNOWN" else []),
        "numerator": n if state != "UNKNOWN" else None,
        "denominator": d if state != "UNKNOWN" else None,
        "value": None, "basis": basis(),
        "missing_reason": "No native measurement" if state == "UNKNOWN" else None,
        "note": "fixture metric",
    }


def state():
    return {
        "protocol": core.PROTOCOL, "schema_version": "2.0.0",
        "snapshot": {
            "captured_at_utc": UTC, "title": "V2 behavioral capsule test",
            "objective": "Prove tamper rejection", "fidelity_mode": "OPERATIONAL",
            "transcript_completeness": "NOT_ASSERTED", "parent_manifest_root_sha256": None,
            "sensitivity": "PUBLIC", "replay_boundary": "Local fixtures only",
        },
        "subject": {
            "repository": "GBOGEB/ABACUS", "work_item": "PR #2006",
            "url": "https://github.com/GBOGEB/ABACUS/pull/2006",
            "branch": "tests/disjoint-v2", "head_sha": HEAD,
            "base_sha": OLD, "default_branch_sha": OLD,
        },
        "authority": {
            "merge_decision": "HOLD", "merged": False,
            "effective_branch_protection": "UNKNOWN",
            "independent_approval": "NOT_ESTABLISHED", "security_waiver": False,
            "authority_transfer": False, "formal_credit_delta": 0,
            "engineering_credit_delta": 0,
        },
        "evidence": [evidence(), evidence("HIST", OLD)],
        "metrics": [metric("current.line", HEAD, 8, 10),
                    metric("historical.line", OLD, 6, 10, "HISTORICAL"),
                    metric("unmeasured.branch", None, None, None, "UNKNOWN")],
        "targets": [{"id": "TARGET", "metric_id": "current.line",
                     "operator": ">=", "percent": 80, "reason": "Required branch"}],
        "comparisons": [{"id": "C1", "before_metric_id": "historical.line",
                         "after_metric_id": "current.line", "label": "Same scope",
                         "required_comparability": True}],
        "gates": [
            {"id": "CI", "label": "CI", "scope": "EXACT_HEAD", "status": "PASS",
             "required_for_admission": True, "source_sha": HEAD,
             "evidence_ids": ["NATIVE"], "run_id": 123, "note": ""},
            {"id": "A10", "label": "A10", "scope": "INDEPENDENT_AUTHORITY",
             "status": "UNKNOWN", "required_for_admission": True,
             "source_sha": None, "evidence_ids": [], "run_id": None, "note": ""},
        ],
        "blockers": [
            {"id": "B1", "classification": "ROOT", "disposition": "OPEN",
             "signature": "Missing admission", "owner": "governance",
             "source_sha": None, "source_path": None,
             "runtime": {"debug_session_id": None, "worker_launch_id": None,
                         "port_lease_id": None, "rex_receipt_uri": None},
             "evidence_ids": [], "gate_ids": ["A10"],
             "next_action": "Obtain independent review", "root_cause_fingerprint": None,
             "note": "Fixture is not admission"},
        ],
        "unknowns": [
            {"id": "U1", "question": "Native admission?", "reason": "No authority",
             "needed_evidence": "Server-side protection", "acquisition": "Read GitHub",
             "owner": "governance", "priority": 1},
        ],
        "actions": [
            {"id": "A1", "order": 1, "title": "Acquire", "owner": "observer",
             "instruction": "Fetch native bytes", "acceptance": "Artifact hash",
             "depends_on": [], "blocked_by": ["B1"], "evidence_required": [],
             "stop_condition": None},
            {"id": "A2", "order": 2, "title": "Verify", "owner": "verifier",
             "instruction": "Check source match", "acceptance": "Hash equality",
             "depends_on": ["A1"], "blocked_by": [], "evidence_required": [],
             "stop_condition": "No fake proof"},
        ],
        "decisions": [
            {"id": "D1", "status": "HOLD", "reason": "No independent decision",
             "source_sha": HEAD, "evidence_ids": []},
        ],
        "raw_sources": [], "byte_equalities": [], "numeric_bindings": [],
        "constraints": ["Fail closed"], "tool_limitations": ["No remote network"],
    }


def add_archive(s, base):
    s["snapshot"]["fidelity_mode"] = "EVIDENCE_ARCHIVE"
    paths = (base / "raw" / "sample.json", base / "raw" / "duplicate.json")
    for p in paths:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b'{"measurements":{"covered":8,"eligible":10},"rows":[1,2,3]}\n')
    sha = core.sha256(paths[0].read_bytes())
    ev = evidence("ARCHIVE", HEAD, "ARTIFACT", "LOCAL_BYTES_VERIFIED")
    ev["sha256"] = sha
    s["evidence"].append(ev)
    s["metrics"][0]["evidence_ids"].append("ARCHIVE")
    s["raw_sources"] = [
        {"path": f"raw/{p.name}", "sha256": sha,
         "evidence_id": "ARCHIVE", "description": "Verified fixture byte"}
        for p in paths
    ]
    s["byte_equalities"] = [{"id": "EQ1", "left_path": "raw/sample.json",
                             "right_path": "raw/duplicate.json", "purpose": "Lossless copy"}]
    s["numeric_bindings"] = [
        {"id": "NB1", "metric_id": "current.line", "field": "numerator",
         "source_path": "raw/sample.json", "json_pointer": "/measurements/covered",
         "operation": "IDENTITY"},
        {"id": "NB2", "metric_id": "current.line", "field": "denominator",
         "source_path": "raw/sample.json", "json_pointer": "/measurements/eligible",
         "operation": "IDENTITY"},
    ]
    return paths


def make_protocol(temp_root):
    """Run producer against a synthetic protocol directory, not fake GitHub."""
    dest = temp_root / "protocol"
    dest.mkdir()
    for filename in core.PROTOCOL_FILES:
        if filename == "build_handover.py":
            dest.joinpath(filename).write_bytes(SOURCE.read_bytes())
        elif filename == "handover_input.schema.json":
            actual = SOURCE.parent / filename
            # On GitHub the real v2 schema is available and must be exercised.
            schema = actual.read_bytes() if actual.exists() else b'{"type":"object"}\n'
            dest.joinpath(filename).write_bytes(schema)
        else:
            dest.joinpath(filename).write_text("fixture protocol input\n")
    return dest


class TestHandoverV2Scale(unittest.TestCase):
    def test_positive_semantics_operational_and_archive(self):
        with TemporaryDirectory() as tmp:
            s = state()
            core.semantic_validate(s, Path(tmp))
            add_archive(s, Path(tmp))
            core.semantic_validate(s, Path(tmp))

    def test_render_all_outputs_and_unknown_preservation(self):
        s = state()
        outputs = core.compute_generated(s)
        self.assertEqual(set(outputs), set(core.CORE_FILES))
        report = outputs["handover.md"].decode()
        self.assertIn("## 8. Ordered next operations and DoV", report)
        self.assertIn("A10", report)
        self.assertIn("UNKNOWN", report)
        self.assertIn("No security waivers", outputs["dropin.md"].decode())
        self.assertFalse(json.loads(outputs["qa_report.json"])["remote_urls_fetched_by_generator"])
        self.assertEqual(json.loads(outputs["unknowns.json"])["counts"]["explicit"], 1)

    def test_comparable_and_ineligible_metric_basis(self):
        s = state()
        comp = core.compute_comparisons(s)["comparisons"][0]
        self.assertEqual(comp["status"], "COMPARABLE")
        self.assertEqual(comp["delta_covered"], 2)
        self.assertEqual(comp["delta_percentage_points"], 20)
        bad = copy.deepcopy(s)
        bad["metrics"][1]["basis"]["selection"] = "different tests"
        self.assertIn("Different selection", core.compute_comparisons(bad)["comparisons"][0]["reasons"])

    def test_unknown_and_count_comparisons_refuse_numeric_uplift(self):
        s = state()
        old = s["metrics"][2]
        current = s["metrics"][0]
        self.assertIn("Missing", core.comparability(old, current, "x", "Z")["reasons"][0])
        cc = copy.deepcopy(current)
        cc.update(measure_type="COUNT", numerator=None, denominator=None, value=5)
        self.assertIn("Ratio comparison", core.comparability(cc, current, "x", "Z")["reasons"][0])

    def test_producer_full_build_verify_and_changed_byte_deny(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            inp = root / "input.json"
            inp.write_bytes(core.canonical(state()))
            protocol = make_protocol(root)
            files, manifest = core.expected_files(inp, protocol, root)
            capsule = root / "capsule"
            for name, contents in files.items():
                path = capsule / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(contents)
            verified, man = core.capsule_verify(capsule)
            self.assertEqual(verified["subject"]["head_sha"], HEAD)
            self.assertEqual(man["manifest_root_sha256"], json.loads(manifest)["manifest_root_sha256"])
            (capsule / "dropin.md").write_text("silent alteration")
            with self.assertRaisesRegex(ValueError, "Manifest content hash mismatch"):
                core.capsule_verify(capsule)

    def test_archive_numeric_json_pointer_binding_and_replay(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            s = state()
            add_archive(s, root)
            inp = root / "input.json"
            inp.write_bytes(core.canonical(s))
            protocol = make_protocol(root)
            files, _ = core.expected_files(inp, protocol, root)
            capsule = root / "capsule"
            for name, contents in files.items():
                p = capsule / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(contents)
            core.capsule_verify(capsule)
            self.assertEqual(json.loads((capsule / "qa_report.json").read_text())[
                "numeric_source_bindings_count"], 2)

    def test_archive_rejects_missing_or_corrupt_sources(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            s = state()
            a, b = add_archive(s, root)
            for case, expected in (("hash", "hash mismatch"), ("missing", "unavailable"),
                                   ("equal", "Byte equality failed")):
                x = copy.deepcopy(s)
                if case == "hash":
                    x["raw_sources"][0]["sha256"] = "0" * 64
                elif case == "missing":
                    x["raw_sources"][0]["path"] = "raw/nonexistent.json"
                else:
                    b.write_bytes(b'{"different":true}\n')
                    different_sha = core.sha256(b.read_bytes())
                    x["raw_sources"][1]["sha256"] = different_sha
                    x["raw_sources"][1]["evidence_id"] = "ARCHIVE2"
                    ev2 = evidence("ARCHIVE2", HEAD, "FILE", "LOCAL_BYTES_VERIFIED")
                    ev2["sha256"] = different_sha
                    x["evidence"].append(ev2)
                with self.subTest(case=case):
                    with self.assertRaisesRegex(ValueError, expected):
                        core.semantic_validate(x, root)
                b.write_bytes(a.read_bytes())

    def test_raw_file_sources_fail_closed(self):
        with TemporaryDirectory() as tmp:
            s = state()
            for path in ("/tmp/leak.txt", "raw/../leak.txt", "outside/sample.txt",
                         "raw\\sample.txt", "raw//sample.txt"):
                x = copy.deepcopy(s)
                x["raw_sources"] = [{"path": path, "sha256": "0" * 64,
                                     "evidence_id": "NATIVE", "description": "test"}]
                with self.subTest(path=path), self.assertRaises(ValueError):
                    core.semantic_validate(x, Path(tmp))

    def test_state_missing_links_and_action_dependencies(self):
        for which, mutate, err in [
            ("blocked", lambda s: s["actions"][0]["blocked_by"].append("ghost"), "absent blocker"),
            ("action", lambda s: s["actions"][1]["depends_on"].append("ghost"), "unknown dependency"),
            ("cycle", lambda s: s["actions"][0]["depends_on"].append("A2"), "cycle"),
            ("order", lambda s: s["actions"][0].update(order=3), "Dependency cannot run after"),
            ("target", lambda s: s["targets"][0].update(metric_id="ghost"), "Target must address"),
            ("comparison", lambda s: s["comparisons"][0].update(before_metric_id="ghost"), "missing metric"),
            ("gate", lambda s: s["blockers"][0]["gate_ids"].append("ghost"), "Unknown linked gate"),
        ]:
            with self.subTest(case=which):
                s = state()
                mutate(s)
                with self.assertRaisesRegex(ValueError, err):
                    core.semantic_validate(s, Path("."))

    def test_observations_and_gate_anti_forgery(self):
        cases = [
            ("pass_head", lambda s: s["gates"][0].update(source_sha=OLD), "not bound to latest head"),
            ("gate_run", lambda s: s["gates"][0].update(run_id=99), "Gate run ID disagrees"),
            ("unknown_gate", lambda s: s["gates"][1].update(source_sha=HEAD), "UNKNOWN gate"),
            ("pass_unverified", lambda s: s["evidence"][0].update(observation="UNVERIFIED"), "unverified"),
            ("no_native", lambda s: s["evidence"][0].update(kind="USER_NOTE"), "native"),
            ("metric_head", lambda s: s["metrics"][0].update(source_sha=OLD), "other SHA"),
            ("metric_ratio", lambda s: s["metrics"][0].update(numerator=999), "Invalid ratio"),
            ("metric_unknown", lambda s: s["metrics"][2].update(value=0), "UNKNOWN metric"),
            ("waiver", lambda s: s["authority"].update(security_waiver=True), "No security waiver"),
            ("transfer", lambda s: s["authority"].update(authority_transfer=True), "No security waiver"),
            ("merged", lambda s: s["authority"].update(merged=True), "merged=true requires"),
            ("approval", lambda s: s["authority"].update(merge_decision="APPROVED"), "Admission cannot proceed"),
            ("secret", lambda s: s["constraints"].append("authorization: bearer SUPER-SECRET-123"), "secret"),
        ]
        for key, f, regex in cases:
            with self.subTest(key=key):
                s = state()
                f(s)
                with self.assertRaisesRegex(ValueError, regex):
                    core.semantic_validate(s, Path("."))

    def test_archive_rejects_fabricated_numeric_bindings(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            s = state()
            add_archive(s, root)
            mods = [
                ("missing_numeric", lambda x: x["numeric_bindings"].pop(), "missing measured numeric"),
                ("bad_path", lambda x: x["numeric_bindings"][0].update(source_path="raw/missing.json"), "archived source"),
                ("bad_metric", lambda x: x["numeric_bindings"][0].update(metric_id="ghost"), "missing metric"),
                ("duplicate", lambda x: x["numeric_bindings"].append(copy.deepcopy(x["numeric_bindings"][0])), "Duplicate numeric"),
                ("double_field", lambda x: x["numeric_bindings"][1].update(field="numerator"), "Duplicate binding"),
                ("wrong_pointer", lambda x: x["numeric_bindings"][0].update(json_pointer="/measurements/absent"), "Invalid numeric source pointer"),
                ("wrong_value", lambda x: x["metrics"][0].update(numerator=7), "disagrees with raw"),
                ("wrong_observation", lambda x: x["metrics"][0].update(evidence_ids=["NATIVE"]), "not SHA/evidence-bound"),
                ("pointer_not_slash", lambda x: x["numeric_bindings"][0].update(json_pointer="measurements/covered"), "Invalid numeric source pointer"),
                ("non_numeric", lambda x: x["numeric_bindings"][0].update(json_pointer="/rows"), "did not resolve to a number"),
                ("boolean", lambda x: x["numeric_bindings"][0].update(json_pointer="/measurements"), "did not resolve to a number"),
            ]
            for key, f, regex in mods:
                with self.subTest(key=key):
                    x = copy.deepcopy(s)
                    f(x)
                    with self.assertRaisesRegex(ValueError, regex):
                        core.semantic_validate(x, root)

    def test_archive_list_length_numeric_operation(self):
        with TemporaryDirectory() as tmp:
            s = state()
            add_archive(s, Path(tmp))
            s["numeric_bindings"][0].update(json_pointer="/rows", operation="LIST_LENGTH")
            s["metrics"][0]["numerator"] = 3
            core.semantic_validate(s, Path(tmp))
            s["numeric_bindings"][0]["json_pointer"] = "/measurements/covered"
            with self.assertRaisesRegex(ValueError, "LIST_LENGTH source not list"):
                core.semantic_validate(s, Path(tmp))

    def test_invalid_json_schema_and_missing_fields(self):
        with self.assertRaisesRegex(ValueError, "SCHEMA INVALID"):
            core.validate_input(state(), {"type": "object", "required": ["unprovided"]}, Path("."))
        with self.assertRaises(Exception):
            core.validate_input({}, {"type": "not_a_jsonschema_type"}, Path("."))

    def test_previous_manifest_required_and_lineage_mismatch(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            inp = root / "input.json"
            inp.write_bytes(core.canonical(state()))
            protocol = make_protocol(root)
            with self.assertRaisesRegex(ValueError, "previous manifest"):
                core.expected_files(inp, protocol, root, previous=state())
            parent = {"manifest_root_sha256": "d" * 64}
            with self.assertRaisesRegex(ValueError, "Parent manifest root differs"):
                core.expected_files(inp, protocol, root, previous=state(), previous_manifest=parent)

    def test_capsule_manifest_tampering_and_extra_file(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            inp = root / "input.json"
            inp.write_bytes(core.canonical(state()))
            files, _ = core.expected_files(inp, make_protocol(root), root)
            cap = root / "capsule"
            for name, blob in files.items():
                target = cap / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(blob)
            (cap / "unexpected.txt").write_text("injected")
            with self.assertRaisesRegex(ValueError, "Unexpected or missing"):
                core.capsule_verify(cap)
            (cap / "unexpected.txt").unlink()
            man = json.loads((cap / "manifest.json").read_text())
            man["manifest_root_sha256"] = "f" * 64
            (cap / "manifest.json").write_bytes(core.canonical(man))
            with self.assertRaisesRegex(ValueError, "root digest mismatch"):
                core.capsule_verify(cap)

    def test_producer_build_cli_and_preexisting_output_guard(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_protocol(root)
            inp = root / "input.json"
            inp.write_bytes(core.canonical(state()))
            cap = root / "cap"
            with patch.object(core, "__file__", str(root / "protocol" / "build_handover.py")):
                core.build(SimpleNamespace(input=str(inp), out=str(cap), previous=None, replace=False))
                self.assertTrue((cap / "manifest.json").exists())
                with self.assertRaisesRegex(ValueError, "already populated"):
                    core.build(SimpleNamespace(input=str(inp), out=str(cap), previous=None, replace=False))
                core.build(SimpleNamespace(input=str(inp), out=str(cap), previous=None, replace=True))
                core.verify(SimpleNamespace(capsule=str(cap)))
                other = root / "other"
                other.mkdir()
                with self.assertRaisesRegex(ValueError, "Not a capsule"):
                    core.verify(SimpleNamespace(capsule=str(other)))

    def test_iteration_comparison_changes_only_with_eligible_basis(self):
        before, after = state(), state()
        before["subject"]["head_sha"] = OLD
        before["metrics"][0]["source_sha"] = OLD
        before["metrics"][0]["evidence_ids"] = ["HIST"]
        before["metrics"][0]["numerator"] = 4
        after["metrics"][0]["numerator"] = 9
        comp = core.compute_comparisons(after, before)
        entries = [x for x in comp["comparisons"] if x["id"] == "ITERATION.current.line"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["delta_covered"], 5)
        before["metrics"][0]["basis"]["configuration_sha256"] = None
        self.assertEqual(core.compute_comparisons(after, before)["comparisons"][-1]["status"], "INELIGIBLE")

    def test_verified_parent_child_chain_and_diff_receipt(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            protocol = make_protocol(root)
            old = state()
            old["subject"]["head_sha"] = OLD
            old["metrics"][0]["source_sha"] = OLD
            old["evidence"][0]["source_sha"] = OLD
            old["gates"][0]["source_sha"] = OLD
            old["metrics"][0]["numerator"] = 5
            parent_input = root / "old.json"
            parent_input.write_bytes(core.canonical(old))
            parent_files, parent_man_bytes = core.expected_files(parent_input, protocol, root)
            parent_cap = root / "parent"
            for name, blob in parent_files.items():
                p = parent_cap / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(blob)
            core.capsule_verify(parent_cap)
            parent_manifest = json.loads(parent_man_bytes)
            after = state()
            after["snapshot"]["parent_manifest_root_sha256"] = parent_manifest["manifest_root_sha256"]
            after_input = root / "after.json"
            after_input.write_bytes(core.canonical(after))
            after_files, _ = core.expected_files(
                after_input, protocol, root, previous=old, previous_manifest=parent_manifest
            )
            child_cap = root / "child"
            for name, blob in after_files.items():
                p = child_cap / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(blob)
            child, _ = core.capsule_verify(child_cap)
            self.assertEqual(child["subject"]["head_sha"], HEAD)
            self.assertTrue((child_cap / "previous" / "state.json").is_file())
            self.assertTrue((child_cap / "previous" / "manifest.json").is_file())
            out = root / "diff.json"
            core.diff(SimpleNamespace(before=str(parent_cap), after=str(child_cap), out=str(out)))
            diff = json.loads(out.read_text())
            self.assertIn("gate_transitions", diff)
            self.assertEqual(diff["after_head"], HEAD)
            self.assertFalse(diff["independent_admission_claimed"])
            with patch.object(core, "__file__", str(protocol / "build_handover.py")):
                built = root / "built"
                core.build(SimpleNamespace(
                    input=str(after_input), out=str(built), previous=str(parent_cap), replace=False
                ))
                self.assertTrue((built / "previous" / "manifest.json").exists())
            bad = copy.deepcopy(after)
            bad["snapshot"]["parent_manifest_root_sha256"] = "0" * 64
            after_input.write_bytes(core.canonical(bad))
            with patch.object(core, "__file__", str(protocol / "build_handover.py")):
                with self.assertRaisesRegex(ValueError, "Parent root does not match"):
                    core.build(SimpleNamespace(
                        input=str(after_input), out=str(root / "bad"),
                        previous=str(parent_cap), replace=False
                    ))

    def test_cli_readback_and_fail_closed_command(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            protocol = make_protocol(root)
            inp = root / "input.json"
            inp.write_bytes(core.canonical(state()))
            cap = root / "capsule"
            with patch.object(core, "__file__", str(protocol / "build_handover.py")):
                for args in (
                    ["build", "--input", str(inp), "--out", str(cap)],
                    ["verify", "--capsule", str(cap)],
                ):
                    with self.subTest(args=args), patch.object(
                        core.sys, "argv", [str(protocol / "build_handover.py"), *args]
                    ):
                        core.main()
                with patch.object(core.sys, "argv", ["build_handover.py", "verify",
                                                          "--capsule", str(root / "missing")]):
                    with self.assertRaises(SystemExit) as cm:
                        core.main()
                    self.assertEqual(cm.exception.code, 2)

    def test_head_gate_and_observation_reference_edge_cases(self):
        cases = [
            ("bad_timestamp", lambda x: x["snapshot"].update(captured_at_utc="bad"), "UTC capture"),
            ("non_utc", lambda x: x["snapshot"].update(captured_at_utc="2026-10-16T08:00:00+02:00"), "UTC capture"),
            ("unsupported_protocol", lambda x: x.update(protocol="OTHER"), "Unsupported protocol"),
            ("dup_evidence", lambda x: x["evidence"].append(copy.deepcopy(x["evidence"][0])), "Duplicate evidence ID"),
            ("no_evidence", lambda x: x["metrics"][0].update(evidence_ids=[]), "requires evidence"),
            ("bad_metric_ref", lambda x: x["metrics"][0].update(evidence_ids=["ghost"]), "absent evidence"),
            ("bad_decision_ref", lambda x: x["decisions"][0].update(evidence_ids=["ghost"]), "Unknown decision evidence"),
            ("bad_blocker_ref", lambda x: x["blockers"][0].update(evidence_ids=["ghost"]), "Unknown blocker evidence"),
            ("unverified_with_digest", lambda x: x["evidence"][0].update(observation="UNVERIFIED", sha256="0" * 64), "verified digest"),
        ]
        for name, mutate, message in cases:
            with self.subTest(name=name):
                x = state()
                mutate(x)
                with self.assertRaisesRegex(ValueError, message):
                    core.semantic_validate(x, Path("."))

    def test_capsule_refuses_external_symlink_even_when_hashes_match(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            inp = root / "input.json"
            inp.write_bytes(core.canonical(state()))
            files, _ = core.expected_files(inp, make_protocol(root), root)
            cap = root / "cap"
            for name, blob in files.items():
                path = cap / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(blob)
            external = root / "outside_payload.md"
            external.write_bytes((cap / "dropin.md").read_bytes())
            (cap / "dropin.md").unlink()
            try:
                (cap / "dropin.md").symlink_to(external)
            except OSError:
                self.skipTest("The filesystem cannot create symlinks")
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                core.capsule_verify(cap)


if __name__ == "__main__":
    unittest.main()
