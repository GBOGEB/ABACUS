import datetime as dt
import io
import json
import pathlib
import sys
import tempfile
import unittest
import urllib.error
import zipfile
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import native_ingest
from admission import effective_policy_from_rules, evaluate
from control import append_history, history_record, read_history, recurrence_alerts
from coordination import apply_operation, registry, sane_path
from everred import InvalidEvidence
from replay import check_manifest

GitHubReadOnly = native_ingest.GitHubReadOnly
_zip_from_github = native_ingest._zip_from_github
bandit_event = native_ingest.bandit_event
coverage_event = native_ingest.coverage_event
events_from_run = native_ingest.events_from_run
junit_events = native_ingest.junit_events
runtime_event = native_ingest.runtime_event
safe_zip_entries = native_ingest.safe_zip_entries

SHA = "e9f34b22967064c779891a4d2ac40541f370e812"
SHA2 = "b45cf45eaad8303c6c4287616492895be4638f56"
REPO = "GBOGEB/ABACUS"
TIME = "2026-10-14T08:00:00Z"
SCOPE = {
    "repository": REPO,
    "source_sha": SHA,
    "run_id": 123,
    "job_id": 456,
    "observed_at": TIME,
}


class Native(unittest.TestCase):
    def job_run(self):
        r = {
            "id": 123,
            "head_sha": SHA,
            "repository": {"full_name": REPO},
            "status": "completed",
            "conclusion": "failure",
            "created_at": TIME,
            "name": "Full CI",
            "run_attempt": 1,
        }
        j = [
            {
                "id": 456,
                "run_id": 123,
                "head_sha": SHA,
                "name": "Tests",
                "status": "completed",
                "conclusion": "failure",
                "completed_at": TIME,
                "steps": [{"number": 2, "name": "pytest", "conclusion": "failure"}],
            }
        ]
        return r, j

    def test_native_job_first_red_unclassified(self):
        r, j = self.job_run()
        events = events_from_run(r, j, REPO, SHA, trusted=True)
        self.assertEqual(
            [e["kind"] for e in events], ["note", "verification", "occurrence"]
        )
        self.assertEqual(events[-1]["evidence"]["causal_status"], "UNCLASSIFIED")
        self.assertEqual(events[1]["evidence"]["source_binding"]["source_sha"], SHA)

    def test_wrong_job_sha_rejected(self):
        r, j = self.job_run()
        j[0]["head_sha"] = SHA2
        with self.assertRaises(InvalidEvidence):
            events_from_run(r, j, REPO, SHA)

    def test_nonterminal_cannot_conclude(self):
        r, j = self.job_run()
        j[0]["status"] = "in_progress"
        with self.assertRaises(InvalidEvidence):
            events_from_run(r, j, REPO, SHA)

    def test_reader_rejects_truncated_jobs(self):
        r, j = self.job_run()

        def transport(req):
            obj = r if "/jobs?" not in req.full_url else {"total_count": 2, "jobs": []}
            return json.dumps(obj).encode()

        reader = GitHubReadOnly("test-token", transport=transport)
        with self.assertRaisesRegex(InvalidEvidence, "pagination"):
            reader.run_and_jobs(REPO, 123, SHA)

    def test_reader_refuses_foreign_run(self):
        r, j = self.job_run()
        r["repository"]["full_name"] = "other/repo"

        def transport(req):
            return json.dumps(r).encode()

        with self.assertRaises(InvalidEvidence):
            GitHubReadOnly("test-token", transport=transport).run_and_jobs(
                REPO, 123, SHA
            )

    def test_github_api_refuses_redirects_before_auth_reuse(self):
        reader = GitHubReadOnly("fake-token")
        redirect = urllib.error.HTTPError(
            "https://api.github.com/repos/GBOGEB/ABACUS",
            302,
            "location changed",
            {"Location": "https://untrusted.example.com/"},
            None,
        )
        with patch("native_ingest.urllib.request.build_opener") as make_opener:
            make_opener.return_value.open.side_effect = redirect
            with self.assertRaisesRegex(InvalidEvidence, "GitHub API HTTP 302"):
                reader.get("/repos/GBOGEB/ABACUS/actions/runs/123")
            self.assertEqual(make_opener.return_value.open.call_count, 1)

    def test_artifact_storage_redirect_rejects_foreign_host(self):
        reader = GitHubReadOnly("fake-token")
        redirect = urllib.error.HTTPError(
            "https://api.github.com/repos/GBOGEB/ABACUS/actions/artifacts/1/zip",
            302,
            "location changed",
            {"Location": "https://attacker.example.com/fake.zip"},
            None,
        )
        with patch("native_ingest.urllib.request.build_opener") as make_opener:
            make_opener.return_value.open.side_effect = redirect
            with self.assertRaisesRegex(InvalidEvidence, "unrecognized artifact"):
                _zip_from_github(reader, REPO, {"id": 1})
            self.assertEqual(make_opener.return_value.open.call_count, 1)

    def test_bandit_exact_config_fingerprint(self):
        finding = {
            "filename": "src/test.py",
            "test_id": "B101",
            "code": "assert foo",
            "issue_text": "bad assert",
        }
        b = json.dumps({"results": [finding, finding]}).encode()
        event = bandit_event(
            b, SCOPE, config_digest="a" * 64, tool_version="1.7", rule_profile="all"
        )
        self.assertEqual(event["evidence"]["raw_findings"], 2)
        self.assertEqual(event["evidence"]["unique_findings"], 1)
        self.assertEqual(event["provenance"], "manual")

    def test_bad_bandit_config_blocked(self):
        with self.assertRaises(InvalidEvidence):
            bandit_event(
                b'{"results":[]}',
                SCOPE,
                config_digest="x",
                tool_version="1.7",
                rule_profile="all",
            )

    def test_bandit_traversal_rejected(self):
        b = json.dumps(
            {"results": [{"filename": "../escape.py", "test_id": "B101"}]}
        ).encode()
        with self.assertRaises(InvalidEvidence):
            bandit_event(
                b, SCOPE, config_digest="a" * 64, tool_version="1", rule_profile="full"
            )

    def test_cobertura_precise_denominator(self):
        b = b'<coverage><packages><package><classes><class filename="src/x.py"><lines><line number="1" hits="3"/><line number="2" hits="0"/></lines></class></classes></package></packages></coverage>'
        x = coverage_event(
            b,
            SCOPE,
            config_id="cfg",
            selection="pytest",
            exclusions="none",
            tool_version="7.0",
        )
        self.assertEqual((x["evidence"]["covered"], x["evidence"]["eligible"]), (1, 2))

    def test_cobertura_duplicate_rejected(self):
        b = b'<coverage><class filename="x.py"><lines><line number="1" hits="1"/><line number="1" hits="1"/></lines></class></coverage>'
        with self.assertRaises(InvalidEvidence):
            coverage_event(
                b,
                SCOPE,
                config_id="cfg",
                selection="all",
                exclusions="none",
                tool_version="7",
            )

    def test_junit_error(self):
        b = b'<testsuite><testcase classname="X" name="fails"><failure message="bad"/></testcase></testsuite>'
        e = junit_events(b, SCOPE)
        self.assertEqual(len(e), 1)
        self.assertEqual(e[0]["evidence"]["failure_message"], "bad")

    def test_xml_entities_rejected(self):
        b = b'<!DOCTYPE foo [<!ENTITY x SYSTEM "file:///etc/passwd">]><coverage></coverage>'
        with self.assertRaises(InvalidEvidence):
            coverage_event(
                b,
                SCOPE,
                config_id="cfg",
                selection="all",
                exclusions="none",
                tool_version="7",
            )

    def test_zip_traversal_and_bomb(self):
        f = io.BytesIO()
        with zipfile.ZipFile(f, "w") as z:
            z.writestr("../bad", "payload")
        with self.assertRaises(InvalidEvidence):
            safe_zip_entries(f.getvalue())

    def test_runtime_only_reported(self):
        obj = {
            "schema": "abacus.everred.runtime.v1",
            **{k: SCOPE[k] for k in ("repository", "source_sha", "run_id", "job_id")},
            "backend": "Docker",
            "exit_code": 0,
            "runner_id": "r1",
            "command_digest": "b" * 64,
            "container_id": "ctr1",
            "image_digest": "sha256:abc",
        }
        e = runtime_event(obj, SCOPE)
        self.assertEqual(e["evidence"]["runtime_trust"], "SELF_REPORTED_UNVERIFIED")

    def test_missing_timestamp_not_fabricated(self):
        s = dict(SCOPE)
        s.pop("observed_at")
        with self.assertRaises(InvalidEvidence):
            junit_events(
                b'<testsuite><testcase name="x"><failure/></testcase></testsuite>', s
            )


class Leases(unittest.TestCase):
    def op(self, rid, path, key):
        return {
            "type": "claim",
            "root_id": rid,
            "paths": [path],
            "idempotency_key": key,
            "principal": "worker-1",
            "expected_source_sha": SHA,
            "authority_reference": "https://github.com/GBOGEB/ABACUS/issues/1860",
        }

    def test_collision_and_disjoint(self):
        s = apply_operation(
            registry(REPO), self.op("RC-0001", "src/alpha", "idkey-0001")
        )
        with self.assertRaisesRegex(InvalidEvidence, "overlapping"):
            apply_operation(s, self.op("RC-0002", "src/alpha/file", "idkey-0002"))
        t = apply_operation(s, self.op("RC-0002", "tests/alpha", "idkey-0002"))
        self.assertEqual(len(t["active"]), 2)

    def test_path_traversal_and_windows_rejected(self):
        for p in ("../tests", "C:/temp", "src\\file", "src/./x"):
            with self.assertRaises(InvalidEvidence):
                sane_path(p)

    def test_no_expiry_stealing(self):
        s = apply_operation(registry(REPO), self.op("RC-0001", "src/a", "idkey-0001"))
        with self.assertRaises(InvalidEvidence):
            apply_operation(s, self.op("RC-0001", "src/a", "idkey-0002"))

    def test_owner_releases_exact_claim(self):
        s = apply_operation(registry(REPO), self.op("RC-0001", "src/a", "idkey-0001"))
        release = {
            "type": "release",
            "root_id": "RC-0001",
            "claim_id": "idkey-0001",
            "idempotency_key": "release-0001",
            "release_evidence_url": "https://github.com/GBOGEB/ABACUS/actions/runs/123",
        }
        with self.assertRaises(InvalidEvidence):
            apply_operation(s, {**release, "claim_id": "wrong"})
        r = apply_operation(s, release)
        self.assertEqual(r["active"], {})


class Admission(unittest.TestCase):
    def bundle(self):
        return {
            "schema": "abacus.everred.admission.inputs.v1",
            "repository": REPO,
            "candidate_sha": SHA,
            "main_sha": SHA2,
            "target_branch": "main",
            "checks": [
                {
                    "name": "CI",
                    "sha": SHA,
                    "conclusion": "success",
                    "status": "completed",
                }
            ],
            "required_checks": ["CI"],
            "security": {"sha": SHA, "decision": "PASS"},
            "coverage": {"sha": SHA, "decision": "PASS"},
            "workflow_governance": {"sha": SHA, "decision": "PASS"},
            "policy": {
                "source": "effective_branch_rules",
                "repository": REPO,
                "branch": "main",
                "main_sha": SHA2,
                "fetched_at": TIME,
                "protected": True,
                "required_pr": True,
                "strict_checks": True,
                "block_force_push": True,
                "block_deletion": True,
                "require_resolved_conversations": True,
                "min_approvals": 1,
            },
            "reviews": [
                {
                    "login": "someone-else",
                    "state": "APPROVED",
                    "commit_id": SHA,
                    "eligible": True,
                }
            ],
            "pr_author": "owner",
            "unresolved_review_conversations": 0,
        }

    def test_all_green_untrusted_still_hold(self):
        d = evaluate(
            self.bundle(), now=dt.datetime(2026, 10, 14, 8, tzinfo=dt.timezone.utc)
        )
        self.assertEqual(d["decision"], "HOLD")
        self.assertFalse(d["merge_authorized"])

    def test_same_head_eligible_metadata_only(self):
        d = evaluate(
            self.bundle(),
            authenticated=True,
            now=dt.datetime(2026, 10, 14, 8, tzinfo=dt.timezone.utc),
        )
        self.assertEqual(d["decision"], "ELIGIBLE_PENDING_AUTHORIZED_MERGE")

    def test_wrong_head_ci_blocked(self):
        x = self.bundle()
        x["checks"][0]["sha"] = SHA2
        self.assertEqual(evaluate(x, authenticated=True)["decision"], "HOLD")

    def test_review_author_not_eligible(self):
        x = self.bundle()
        x["reviews"][0]["login"] = "owner"
        self.assertNotEqual(
            evaluate(x, authenticated=True)["gates"]["independent_review"], "PASS"
        )

    def test_weak_governance_rejected(self):
        x = self.bundle()
        x["policy"]["block_force_push"] = False
        d = evaluate(
            x,
            authenticated=True,
            now=dt.datetime(2026, 10, 14, 8, tzinfo=dt.timezone.utc),
        )
        self.assertEqual(d["gates"]["branch_protection"], "RED")

    def test_stale_policy_unknown(self):
        x = self.bundle()
        self.assertEqual(
            evaluate(x, authenticated=True)["gates"]["branch_protection"], "UNKNOWN"
        )

    def test_effective_rules_absence_failclosed(self):
        p = effective_policy_from_rules(
            REPO,
            SHA2,
            [
                {
                    "type": "pull_request",
                    "parameters": {"required_approving_review_count": 1},
                }
            ],
            {"protected": False},
            TIME,
        )
        self.assertFalse(p["protected"])
        self.assertFalse(p["strict_checks"])


class Control(unittest.TestCase):
    def test_hash_history_idempotence_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "kpi.jsonl"
            pulse = {"pulse_id": "1234", "value": None}
            self.assertEqual(append_history(p, pulse), "APPENDED")
            self.assertEqual(append_history(p, pulse), "ALREADY_RECORDED")
            self.assertEqual(len(read_history(p)), 1)
            p.write_text(p.read_text().replace("1234", "9999"))
            with self.assertRaises(InvalidEvidence):
                read_history(p)

    def test_recurrence_after_closure_only(self):
        events = [
            {
                "id": "closed-1",
                "kind": "closure",
                "root_id": "RC1",
                "provenance": "manual",
                "evidence": {"state": "CLOSED"},
            },
            {
                "id": "again-1",
                "kind": "recurrence",
                "root_id": "RC1",
                "provenance": "manual",
                "sha": SHA,
            },
        ]
        a = recurrence_alerts(events)
        self.assertEqual(len(a), 1)
        self.assertFalse(a[0]["authenticated"])
        self.assertFalse(a[0]["notified"])

    def test_unknown_kpi_kept_null(self):
        s = {
            "schema": "abacus.everred.snapshot.v3",
            "events_count": 0,
            "coverage_scopes": {},
            "metrics_derived": {},
        }
        p = history_record(s, [])
        self.assertIsNone(p["occurrence_amplification"])


class Replay(unittest.TestCase):
    def test_source_pair_sha_required(self):
        m = {
            "schema": "abacus.everred.replay.v1",
            "repository": REPO,
            "root_id": "RC-0001",
            "main_base_sha": SHA2,
            "consumer_head_sha": SHA,
            "repair_head_sha": SHA,
            "test_profile": "unittest",
        }
        with self.assertRaises(InvalidEvidence):
            check_manifest(m)

    def test_injection_test_path_rejected(self):
        m = {
            "schema": "abacus.everred.replay.v1",
            "repository": REPO,
            "root_id": "RC-0001",
            "main_base_sha": SHA2,
            "consumer_head_sha": SHA,
            "repair_head_sha": "a" * 40,
            "test_profile": "pytest-focused",
            "test_path": "tests/../evil",
        }
        with self.assertRaises(InvalidEvidence):
            check_manifest(m)


if __name__ == "__main__":
    unittest.main()


class BatchAtomic(unittest.TestCase):
    def test_bad_batch_rolls_back_entire_run(self):
        from everred import append_events_batch, read_ledger

        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "e.jsonl"
            e = {
                "schema": "abacus.everred.event.v3",
                "id": "good-note-abc",
                "kind": "note",
                "occurred_at": TIME,
                "repo": REPO,
                "provenance": "manual",
                "evidence": {},
            }
            with self.assertRaises(InvalidEvidence):
                append_events_batch(path, [e, {**e, "id": "x", "schema": "invalid"}])
            self.assertFalse(path.exists())
            self.assertEqual(append_events_batch(path, [e]), 1)
            self.assertEqual(len(read_ledger(path)), 1)


class ExtraNative(unittest.TestCase):
    def test_zip_roundtrip(self):
        f = io.BytesIO()
        with zipfile.ZipFile(f, "w") as z:
            z.writestr("bandit.json", '{"results":[]}')
        self.assertEqual(
            safe_zip_entries(f.getvalue())["bandit.json"], b'{"results":[]}'
        )

    def test_artifact_truncation_rejected(self):
        def transport(req):
            return json.dumps({"total_count": 2, "artifacts": [{"id": 1}]}).encode()

        g = GitHubReadOnly("fake", transport=transport)
        with self.assertRaisesRegex(InvalidEvidence, "truncated"):
            g.artifacts(REPO, 123)

    def test_runtime_rejects_wrong_repo(self):
        x = {
            "schema": "abacus.everred.runtime.v1",
            "repository": "other/repo",
            "source_sha": SHA,
            "run_id": 123,
            "job_id": 456,
            "backend": "LDAB",
        }
        with self.assertRaises(InvalidEvidence):
            runtime_event(x, SCOPE)

    def test_valid_run_job_reader(self):
        run = {
            "id": 123,
            "head_sha": SHA,
            "repository": {"full_name": REPO},
            "status": "completed",
        }
        job = {"id": 456, "run_id": 123, "status": "completed", "conclusion": "success"}

        def transport(req):
            if "/jobs?" in req.full_url:
                return json.dumps({"total_count": 1, "jobs": [job]}).encode()
            return json.dumps(run).encode()

        _, j = GitHubReadOnly("fake", transport=transport).run_and_jobs(REPO, 123, SHA)
        self.assertEqual(j[0]["id"], 456)


class NativeArtifactLinkage(unittest.TestCase):
    def base(self):
        run = {
            "id": 123,
            "head_sha": SHA,
            "repository": {"full_name": REPO},
            "created_at": TIME,
            "status": "completed",
            "conclusion": "success",
            "name": "Bandit",
        }
        jobs = [
            {
                "id": 456,
                "run_id": 123,
                "status": "completed",
                "conclusion": "success",
                "name": "Bandit job",
                "completed_at": TIME,
                "steps": [],
            }
        ]
        artifact = {
            "id": 789,
            "name": "Bandit",
            "expired": False,
            "digest": "sha256:" + "a" * 64,
            "created_at": TIME,
            "workflow_run": {"id": 123, "head_sha": SHA},
        }
        return run, jobs, artifact

    def test_native_bandit_artifact_bound_without_security_credit(self):
        from unittest.mock import patch

        run, jobs, artifact = self.base()

        class Stub:
            def run_and_jobs(self, *_):
                return run, jobs

            def artifacts(self, *_):
                return [artifact]

        plan = [
            {
                "artifact_id": 789,
                "job_id": 456,
                "kind": "bandit",
                "member": "bandit.json",
                "config_digest": "b" * 64,
                "scanner_version": "1.8",
                "rule_profile": "full",
            }
        ]
        with patch(
            "native_ingest._zip_from_github",
            return_value={"bandit.json": b'{"results":[]}'},
        ):
            es = native_ingest.collect_native(REPO, SHA, 123, plan, reader=Stub())
        bandit = [x for x in es if x["kind"] == "security_census"][0]
        self.assertEqual(bandit["evidence"]["raw_findings"], 0)
        self.assertEqual(
            bandit["evidence"]["verification_status"],
            "SCANNER_OBSERVATION_NOT_SECURITY_DISPOSITION",
        )
        self.assertEqual(
            bandit["evidence"]["artifact_receipt"]["upload_job_binding"],
            "DECLARED_NOT_ATTESTED",
        )

    def test_foreign_artifact_sha_rejected(self):
        run, jobs, artifact = self.base()
        artifact["workflow_run"]["head_sha"] = SHA2

        class Stub:
            def run_and_jobs(self, *_):
                return run, jobs

            def artifacts(self, *_):
                return [artifact]

        with self.assertRaises(InvalidEvidence):
            native_ingest.collect_native(
                REPO,
                SHA,
                123,
                [
                    {
                        "artifact_id": 789,
                        "job_id": 456,
                        "kind": "junit",
                        "member": "pytest.xml",
                    }
                ],
                reader=Stub(),
            )
