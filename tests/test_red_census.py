"""Offline tests for scripts/red_census.py (no network; inline saved REST fixtures)."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("red_census", ROOT / "scripts" / "red_census.py")
rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rc)

REPO = "GBOGEB/ABACUS"
HEAD = "h" * 40


def _run(i, conclusion, sha, created, event="push", branch="main"):
    return {
        "id": i,
        "conclusion": conclusion,
        "head_sha": sha,
        "created_at": created,
        "event": event,
        "head_branch": branch,
    }


def _runs_key(wf_id):
    return rc.request_key(
        f"/repos/{REPO}/actions/workflows/{wf_id}/runs",
        {"branch": "main", "status": "completed", "exclude_pull_requests": "true", "per_page": 10, "page": 1},
    )


def _commit_key(path):
    return rc.request_key(f"/repos/{REPO}/commits", {"path": path, "sha": "main", "per_page": 1, "page": 1})


def _commit(sha, date):
    return [{"sha": sha, "commit": {"committer": {"date": date}}}]


def fixture(workflow_total=None):
    """Saved REST responses for one repo with one workflow per class."""
    wfs = [
        (1, "everred.yml"),
        (2, "g2r.yml"),
        (3, "flaky.yml"),
        (4, "green.yml"),
        (5, "never.yml"),
        (6, "dow-integration-ci-cd.yml"),  # GHOST: deleted in #1375, still listed active
        (7, "dow-integration.yml"),  # its green successor
        (8, "stale.yml"),
        (11, "startup.yml"),  # only zero-job failures (GitHub "Internal server error" at startup)
        (12, "green-noise.yml"),  # green history + newest zero-job failure: must not be GREEN_TO_RED
    ]
    workflows = [
        {"id": i, "name": n, "path": f".github/workflows/{n}", "state": "active"} for i, n in wfs
    ]
    workflows.append({"id": 9, "name": "disabled", "path": ".github/workflows/off.yml", "state": "disabled_manually"})
    workflows.append({"id": 10, "name": "Copilot", "path": "dynamic/copilot-swe-agent/copilot", "state": "active"})
    r = {}
    r[rc.request_key(f"/repos/{REPO}")] = {"default_branch": "main"}
    r[rc.request_key(f"/repos/{REPO}/commits/main")] = {"sha": HEAD}
    r[rc.request_key(f"/repos/{REPO}/actions/workflows", {"per_page": 100, "page": 1})] = {
        "total_count": workflow_total if workflow_total is not None else len(workflows),
        "workflows": workflows,
    }
    r[rc.request_key(f"/repos/{REPO}/contents/.github/workflows", {"ref": HEAD})] = [
        {"path": f".github/workflows/{n}"} for _, n in wfs if n != "dow-integration-ci-cd.yml"
    ] + [{"path": ".github/workflows/off.yml"}]

    def day(d):
        return f"2026-11-{d:02d}T05:17:00Z"

    r[_runs_key(1)] = {"total_count": 3, "workflow_runs": [
        _run(13, "failure", "c3", day(3)), _run(12, "cancelled", "c2", day(2)), _run(11, "failure", "c1", day(1))]}
    # newest first (PR run excluded): R(a4) R(a3) G G -> GREEN_TO_RED, first red = a3
    r[_runs_key(2)] = {"total_count": 4, "workflow_runs": [
        _run(21, "success", "a1", day(1)), _run(22, "success", "a2", day(2)),
        _run(23, "failure", "a3", day(3)), _run(24, "failure", "a4", day(4)),
        _run(25, "failure", "pr", day(5), event="pull_request")]}
    r[_runs_key(3)] = {"total_count": 4, "workflow_runs": [
        _run(31, "failure", "f1", day(1)), _run(32, "success", "f2", day(2)),
        _run(33, "failure", "f3", day(3)), _run(34, "success", "f4", day(4))]}
    r[_runs_key(4)] = {"total_count": 2, "workflow_runs": [
        _run(41, "failure", "g1", day(1)), _run(42, "success", "g2", day(2))]}
    r[_runs_key(5)] = {"total_count": 1, "workflow_runs": [_run(51, "skipped", "n1", day(1))]}
    r[_runs_key(7)] = {"total_count": 10, "workflow_runs": [
        _run(70 + k, "success", f"d{k}", day(k)) for k in range(1, 11)]}
    r[_runs_key(8)] = {"total_count": 1, "workflow_runs": [_run(81, "success", "s1", day(1))]}
    r[_runs_key(11)] = {"total_count": 2, "workflow_runs": [
        _run(111, "failure", "z1", day(8)), _run(112, "startup_failure", "z2", day(7))]}
    r[_runs_key(12)] = {"total_count": 3, "workflow_runs": [
        _run(121, "failure", "n9", day(9)), _run(122, "success", "n8", day(8)), _run(123, "success", "n7", day(7))]}
    zero_jobs = {111, 121}
    for key, body in list(r.items()):
        if "/runs?" not in key:
            continue
        for run in body["workflow_runs"]:
            if run["conclusion"] in ("failure", "timed_out"):
                r[rc.request_key(f"/repos/{REPO}/actions/runs/{run['id']}/jobs",
                                 {"filter": "all", "per_page": 1, "page": 1})] = {
                    "total_count": 0 if run["id"] in zero_jobs else 1, "jobs": []}
    for i, n in wfs:
        if n == "dow-integration-ci-cd.yml":
            continue
        r[_commit_key(f".github/workflows/{n}")] = _commit(f"file{i}", "2026-10-01T00:00:00Z")
    r[_commit_key(".github/workflows/stale.yml")] = _commit("file8", "2026-11-05T00:00:00Z")
    return r


class ClassifyTests(unittest.TestCase):
    def test_classes(self):
        self.assertEqual(rc.classify([]), ("NO_MAIN_RUNS", None))
        self.assertEqual(rc.classify(["cancelled", "skipped"]), ("NO_MAIN_RUNS", None))
        self.assertEqual(rc.classify(["failure", "timed_out"])[0], "EVERRED")
        self.assertEqual(rc.classify(["success", "success"])[0], "GREEN")
        self.assertEqual(rc.classify(["failure", "failure", "success"]), ("GREEN_TO_RED", 1))
        self.assertEqual(rc.classify(["success", "failure"])[0], "GREEN")  # recovered
        self.assertEqual(rc.classify(["failure", "success", "failure"])[0], "FLAKY")
        self.assertEqual(rc.classify(["timed_out", "cancelled", "success"]), ("GREEN_TO_RED", 0))
        self.assertEqual(rc.classify(["STARTUP_FAILURE", "success"]), ("GREEN", None))
        self.assertEqual(rc.classify(["STARTUP_FAILURE", "cancelled"]), ("STARTUP_FAILURE", None))


class CensusTests(unittest.TestCase):
    def setUp(self):
        self.report = rc.build_report(rc.OfflineClient(fixture()), [REPO])
        self.rows = {w["path"].rsplit("/", 1)[-1]: w for w in self.report["repos"][0]["workflows"]}

    def test_each_class(self):
        cls = {k: v["class"] for k, v in self.rows.items()}
        self.assertEqual(cls["everred.yml"], "EVERRED")
        self.assertEqual(cls["g2r.yml"], "GREEN_TO_RED")
        self.assertEqual(cls["flaky.yml"], "FLAKY")
        self.assertEqual(cls["green.yml"], "GREEN")
        self.assertEqual(cls["never.yml"], "NO_MAIN_RUNS")
        self.assertEqual(cls["dow-integration.yml"], "GREEN")
        self.assertNotIn("off.yml", cls)  # disabled
        self.assertEqual(self.report["repos"][0]["skipped_non_file_workflows"], 1)

    def test_first_red_sha_ignores_pr_runs(self):
        g2r = self.rows["g2r.yml"]
        self.assertEqual(g2r["first_red_sha"], "a3")
        self.assertEqual(g2r["first_red_run_id"], 23)
        self.assertEqual(g2r["last_run_sha"], "a4")
        self.assertEqual(len(g2r["window"]), 4)

    def test_ghost_is_separate_from_red(self):
        ghost = self.rows["dow-integration-ci-cd.yml"]
        self.assertEqual(ghost["class"], "GHOST")
        self.assertEqual(ghost["window"], [])
        counts = self.report["repos"][0]["counts"]
        self.assertEqual(counts["GHOST"], 1)
        self.assertEqual(counts["EVERRED"], 1)
        self.assertEqual(counts["GREEN_TO_RED"], 1)

    def test_zero_job_failures_are_startup_failures_not_red(self):
        st = self.rows["startup.yml"]
        self.assertEqual(st["class"], "STARTUP_FAILURE")
        self.assertEqual(st["startup_failures"], 2)
        self.assertEqual([w["effective"] for w in st["window"]], ["STARTUP_FAILURE", "STARTUP_FAILURE"])
        noise = self.rows["green-noise.yml"]
        self.assertEqual(noise["class"], "GREEN")
        self.assertIn("STARTUP_FAILURES", noise["flags"])
        self.assertIsNone(noise["first_red_sha"])
        rb = self.report["repos"][0]
        self.assertEqual(rb["counts"]["STARTUP_FAILURE"], 1)
        self.assertEqual(rb["startup_failure_runs"], 3)
        self.assertEqual(rb["counts"]["EVERRED"] + rb["counts"]["GREEN_TO_RED"], 2)

    def test_stale_flag(self):
        self.assertEqual(self.rows["stale.yml"]["flags"], ["STALE"])
        self.assertEqual(self.rows["green.yml"]["flags"], [])
        self.assertEqual(self.report["repos"][0]["stale_count"], 1)

    def test_not_partial_when_complete(self):
        self.assertFalse(self.report["partial"])

    def test_partial_when_total_exceeds_fetched(self):
        fx = fixture(workflow_total=150)
        # page 1 returned < per_page, so the loop stops; API total says 150.
        rep = rc.build_report(rc.OfflineClient(fx), [REPO])
        self.assertTrue(rep["partial"])
        self.assertTrue(rep["repos"][0]["partial"])
        self.assertIn("PARTIAL", rc.markdown_summary(rep))

    def test_pagination_uses_explicit_page_loop(self):
        fx = fixture()
        key1 = rc.request_key(f"/repos/{REPO}/actions/workflows", {"per_page": 100, "page": 1})
        page1 = fx.pop(key1)
        filler = [{"id": 1000 + k, "name": f"x{k}", "path": f".github/workflows/x{k}.yml", "state": "disabled_manually"}
                  for k in range(100)]
        fx[key1] = {"total_count": 100 + len(page1["workflows"]), "workflows": filler}
        fx[rc.request_key(f"/repos/{REPO}/actions/workflows", {"per_page": 100, "page": 2})] = {
            "total_count": 100 + len(page1["workflows"]), "workflows": page1["workflows"]}
        rep = rc.build_report(rc.OfflineClient(fx), [REPO])
        self.assertFalse(rep["partial"])
        self.assertEqual(rep["repos"][0]["workflows_fetched"], 100 + len(page1["workflows"]))
        self.assertEqual(rep["repos"][0]["counts"]["GHOST"], 1)

    def test_deterministic_output(self):
        a = rc.dumps(rc.build_report(rc.OfflineClient(fixture()), [REPO]))
        b = rc.dumps(rc.build_report(rc.OfflineClient(fixture()), [REPO]))
        self.assertEqual(a, b)
        self.assertNotIn("observed_at", a)
        self.assertNotIn("generated_at", a)

    def test_cli_from_json(self):
        with tempfile.TemporaryDirectory() as d:
            fx = Path(d, "fx.json")
            fx.write_text(json.dumps(fixture()))
            out, md = Path(d, "out.json"), Path(d, "summary.md")
            self.assertEqual(rc.main([REPO, "--from-json", str(fx), "--out", str(out), "--summary", str(md)]), 0)
            data = json.loads(out.read_text())
            self.assertEqual(data["schema"], "red.census.v1")
            self.assertIn("GHOST", md.read_text())


class LedgerTests(unittest.TestCase):
    def _ledger(self, d):
        path = Path(d, "bd.jsonl")
        rc.append_row(path, {"family": "F4", "title": "BD-17", "repo": REPO, "state": "HOLD", "evidence": ["x"],
                             "workflows": [".github/workflows/ci.yml#lint-and-static-analysis/Run mypy",
                                           ".github/workflows/bridge-ci.yml"]})
        rc.append_row(path, {"family": "F4", "title": "BD-21", "repo": REPO, "state": "BURNED", "evidence": ["#2663"],
                             "workflows": [".github/workflows/ci.yml#test-bridge-integration/Install dependencies"]})
        return path

    def test_good_chain_verifies(self):
        with tempfile.TemporaryDirectory() as d:
            rows = rc.load_ledger(self._ledger(d))
            self.assertEqual(rc.verify_ledger(rows), [])
            self.assertEqual(rows[0]["prev_hash"], rc.GENESIS)
            self.assertEqual(rows[1]["prev_hash"], rows[0]["row_hash"])

    def test_root_id_is_3p_rule(self):
        members = [".github/workflows/b.yml", ".github/workflows/a.yml"]
        expected = rc.sha256_hex(json.dumps(
            {"members": sorted(f"{REPO}:{m}" for m in members), "scope": "GBOGEB", "type": "ci-root"},
            sort_keys=True, separators=(",", ":")))
        self.assertEqual(rc.compute_root_id(REPO, members), expected)
        self.assertEqual(rc.compute_root_id(REPO, list(reversed(members))), expected)

    def test_tampered_row_detected(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._ledger(d)
            lines = path.read_text().splitlines()
            row = json.loads(lines[0])
            row["state"] = "BURNED"
            lines[0] = json.dumps(row)
            path.write_text("\n".join(lines) + "\n")
            errs = rc.verify_ledger(rc.load_ledger(path))
            self.assertTrue(any("row_hash mismatch" in e for e in errs), errs)

    def test_broken_chain_detected(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._ledger(d)
            lines = path.read_text().splitlines()
            path.write_text(lines[1] + "\n")  # drop first row
            errs = rc.verify_ledger(rc.load_ledger(path))
            self.assertTrue(any("chain broken" in e for e in errs), errs)
            self.assertEqual(rc.main(["--verify-ledger", str(path)]), 1)

    def test_duplicate_member_detected(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._ledger(d)
            # whole-file ci.yml overlaps the step-scoped members of both rows
            with self.assertRaises(ValueError):
                rc.append_row(path, {"family": "F4", "title": "dup", "repo": REPO, "state": "HOLD",
                                     "evidence": [], "workflows": [".github/workflows/ci.yml"]})
            # forge a raw row with a different root_id sharing a member
            rows = rc.load_ledger(path)
            forged = {"family": "F4", "title": "forged", "repo": REPO, "state": "HOLD", "evidence": [],
                      "workflows": [".github/workflows/bridge-ci.yml", ".github/workflows/z.yml"]}
            forged["root_id"] = rc.compute_root_id(REPO, forged["workflows"])
            forged["prev_hash"] = rows[-1]["row_hash"]
            forged["row_hash"] = rc.compute_row_hash(forged)
            errs = rc.verify_ledger(rows + [forged])
            self.assertTrue(any("different root_id" in e for e in errs), errs)

    def test_state_transition_same_root_allowed(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._ledger(d)
            rc.append_row(path, {"family": "F4", "title": "BD-17", "repo": REPO, "state": "BURNED", "evidence": ["y"],
                                 "workflows": [".github/workflows/bridge-ci.yml",
                                               ".github/workflows/ci.yml#lint-and-static-analysis/Run mypy"]})
            rows = rc.load_ledger(path)
            self.assertEqual(rc.verify_ledger(rows), [])
            self.assertEqual(rows[0]["root_id"], rows[2]["root_id"])
            self.assertEqual(rc.latest_rows(rows)[rows[0]["root_id"]]["state"], "BURNED")

    def test_same_file_different_repo_does_not_overlap(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d, "bd.jsonl")
            for repo in (REPO, "GBOGEB/CODEX"):
                rc.append_row(path, {"family": "F", "title": repo, "repo": repo, "state": "HOLD", "evidence": [],
                                     "workflows": [".github/workflows/ci.yml"]})
            self.assertEqual(rc.verify_ledger(rc.load_ledger(path)), [])

    def test_seed_ledger_verifies(self):
        seed = ROOT / "ledger" / "bd_ledger.jsonl"
        if seed.exists():
            self.assertEqual(rc.verify_ledger(rc.load_ledger(seed)), [])


if __name__ == "__main__":
    unittest.main()
