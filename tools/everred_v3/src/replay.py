"""Immutable consumer/repair replay: preview != native consumer exact-head proof.

Uses merge-tree and isolated detached worktrees. Never pushes, rebases or merges.
Only execute trusted checked-out code on an authorized isolated runner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import tempfile

from everred import InvalidEvidence, stable_json, valid_sha


def check_manifest(m):
    if not isinstance(m, dict) or m.get("schema") != "abacus.everred.replay.v1":
        raise InvalidEvidence("invalid replay manifest")
    for k in ("main_base_sha", "consumer_head_sha", "repair_head_sha"):
        if not valid_sha(m.get(k)):
            raise InvalidEvidence(f"missing immutable {k}")
    if (
        len(
            set(m[k] for k in ("main_base_sha", "consumer_head_sha", "repair_head_sha"))
        )
        < 3
    ):
        raise InvalidEvidence("replay snapshots must be distinct")
    if not isinstance(m.get("repository"), str) or "/" not in m["repository"]:
        raise InvalidEvidence("repository identity missing")
    if not isinstance(m.get("root_id"), str) or len(m["root_id"]) < 5:
        raise InvalidEvidence("root identity missing")
    if m.get("test_profile") not in ("unittest", "pytest-focused"):
        raise InvalidEvidence("unsupported test profile")
    if m["test_profile"] == "pytest-focused":
        t = m.get("test_path")
        if (
            not isinstance(t, str)
            or t.startswith("/")
            or any(x in ("..", "", ".") for x in t.split("/"))
            or not t.startswith("tests/")
        ):
            raise InvalidEvidence("unsafe test path")
    return m


class Preview:
    def __init__(self, checkout):
        self.checkout = str(pathlib.Path(checkout).resolve())

    def git(self, *args, ok=True):
        p = subprocess.run(
            ["git", "-C", self.checkout, *args],
            capture_output=True,
            text=True,
            timeout=90,
        )
        if ok and p.returncode:
            raise InvalidEvidence(f"git {args[0]}: {p.stderr[:320]}")
        return p

    def plan(self, m):
        m = check_manifest(m)
        base, consumer, repair = (
            m[k] for k in ("main_base_sha", "consumer_head_sha", "repair_head_sha")
        )
        for ref in (base, consumer, repair):
            self.git("cat-file", "-e", f"{ref}^{{commit}}")
        # Both inputs must descend from the exact declared common base.
        for ref in (consumer, repair):
            if self.git("merge-base", "--is-ancestor", base, ref, ok=False).returncode:
                raise InvalidEvidence("declared base not ancestral to input")
        out = self.git(
            "merge-tree",
            "--write-tree",
            f"--merge-base={base}",
            consumer,
            repair,
            ok=False,
        )
        if out.returncode or not out.stdout.strip():
            return {
                "schema": "abacus.everred.replay.receipt.v1",
                "repository": m["repository"],
                "root_id": m["root_id"],
                "main_base_sha": base,
                "consumer_head_sha": consumer,
                "repair_head_sha": repair,
                "integration_tree_sha": None,
                "status": "CONFLICT",
                "detail": out.stderr[:300] or out.stdout[:300],
                "native_consumer_ci": "UNKNOWN",
                "merge_authorized": False,
            }
        tree = out.stdout.strip().splitlines()[0]
        if not valid_sha(tree):
            raise InvalidEvidence("invalid merged tree object")
        return {
            "schema": "abacus.everred.replay.receipt.v1",
            "repository": m["repository"],
            "root_id": m["root_id"],
            "main_base_sha": base,
            "consumer_head_sha": consumer,
            "repair_head_sha": repair,
            "integration_tree_sha": tree,
            "status": "MERGE_PREVIEW_ONLY",
            "test_profile": m["test_profile"],
            "manifest_sha256": hashlib.sha256(stable_json(m).encode()).hexdigest(),
            "native_consumer_ci": "UNKNOWN",
            "merge_authorized": False,
        }

    def execute(self, m):
        plan = self.plan(m)
        if plan["status"] != "MERGE_PREVIEW_ONLY":
            return plan
        # A tree object is immutable; a temporary commit materializes it for worktree checkout.
        temp_commit = self.git(
            "commit-tree",
            plan["integration_tree_sha"],
            "-p",
            m["consumer_head_sha"],
            "-m",
            "EVERRED ephemeral replay - never push",
        ).stdout.strip()
        tmp = tempfile.mkdtemp(prefix="everred-replay-")
        try:
            self.git("worktree", "add", "--detach", tmp, temp_commit)
            if not pathlib.Path(tmp, "tests").is_dir():
                plan["status"] = "ISOLATED_PREVIEW_NO_TESTS"
                return plan
            cmd = (
                ["python3", "-m", "unittest", "discover", "-s", "tests", "-q"]
                if m["test_profile"] == "unittest"
                else ["python3", "-m", "pytest", "-q", m["test_path"]]
            )
            try:
                result = subprocess.run(
                    cmd,
                    cwd=tmp,
                    capture_output=True,
                    text=True,
                    timeout=180,
                    env={
                        "PATH": "/usr/local/bin:/usr/bin:/bin",
                        "HOME": tmp,
                        "PYTHONDONTWRITEBYTECODE": "1",
                    },
                )
                output = result.stdout + result.stderr
                no_tests = (
                    "Ran 0 tests" in output
                    or "no tests ran" in output
                    or "collected 0 items" in output
                )
                plan["status"] = (
                    "ISOLATED_PREVIEW_NO_TESTS"
                    if no_tests
                    else (
                        "ISOLATED_PREVIEW_PASS"
                        if result.returncode == 0
                        else "ISOLATED_PREVIEW_RED"
                    )
                )
                plan["test_returncode"] = result.returncode
                plan["test_output_sha256"] = hashlib.sha256(
                    (result.stdout + result.stderr).encode()
                ).hexdigest()
                plan["test_output_tail"] = (result.stdout + result.stderr)[-1200:]
            except subprocess.TimeoutExpired:
                plan["status"] = "ISOLATED_PREVIEW_TIMEOUT"
            return plan
        finally:
            self.git("worktree", "remove", "--force", tmp, ok=False)
            shutil.rmtree(tmp, ignore_errors=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--checkout", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument(
        "--execute-isolated",
        action="store_true",
        help="explicit opt-in to execute trusted code",
    )
    p.add_argument("--output")
    a = p.parse_args()
    m = json.loads(pathlib.Path(a.manifest).read_text())
    agent = Preview(a.checkout)
    result = agent.execute(m) if a.execute_isolated else agent.plan(m)
    result["provenance"] = "LOCAL_PREVIEW_NOT_NATIVE_CI"
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if a.output:
        pathlib.Path(a.output).write_text(rendered)
    print(rendered)


if __name__ == "__main__":
    main()
