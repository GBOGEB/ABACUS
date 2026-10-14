import pathlib
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from coordination import REF, ZERO, GitCASStore
from everred import InvalidEvidence
from replay import Preview

REPO = "GBOGEB/ABACUS"


def git(path, *args, check=True):
    p = subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True)
    if check and p.returncode:
        raise AssertionError(p.stderr)
    return p.stdout.strip()


class GitIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = pathlib.Path(self.tmp.name)
        self.remote = self.home / "remote.git"
        self.work = self.home / "work"
        self.other = self.home / "other"
        subprocess.run(["git", "init", "--bare", "-q", str(self.remote)], check=True)
        subprocess.run(
            ["git", "clone", "-q", str(self.remote), str(self.work)], check=True
        )
        git(self.work, "config", "user.name", "EVERRED Fixture")
        git(self.work, "config", "user.email", "fixture@example.invalid")
        (self.work / "README").write_text("baseline\n")
        git(self.work, "add", "README")
        git(self.work, "commit", "-qm", "baseline")
        self.base = git(self.work, "rev-parse", "HEAD")
        git(self.work, "push", "-q", "origin", "HEAD:refs/heads/main")

    def tearDown(self):
        self.tmp.cleanup()

    def test_atomic_git_ref_lease(self):
        store = GitCASStore(self.work)
        op = {
            "type": "claim",
            "root_id": "ABACUS-RC-2026-0001",
            "paths": ["src/test"],
            "idempotency_key": "sample-key-01",
            "principal": "workerA",
            "expected_source_sha": self.base,
            "authority_reference": "https://github.com/GBOGEB/ABACUS/issues/1860",
        }
        plan = store.transact(REPO, op)
        self.assertEqual(plan["status"], "PROPOSED_NOT_WRITTEN")
        receipt = store.transact(REPO, op, apply=True)
        self.assertEqual(
            receipt["status"], "COORDINATION_COMMITTED_NOT_SOURCE_AUTHORIZATION"
        )
        old, registry = store.read(REPO)
        self.assertEqual(registry["generation"], 1)
        self.assertIn(op["root_id"], registry["active"])
        with self.assertRaises(InvalidEvidence):
            store.transact(REPO, op, apply=True)
        # Stale expected ref CAS is rejected at Git receive-pack, not only in memory.
        fake = store.commit(ZERO, {**registry, "generation": 2})
        out = store.git(
            "push",
            "--force-with-lease=" + REF + ":",
            "origin",
            f"{fake}:{REF}",
            ok=False,
        )
        self.assertNotEqual(out.returncode, 0)

    def test_replay_mergetree_disjoint(self):
        git(self.work, "checkout", "-qb", "consumer", self.base)
        (self.work / "consumer.txt").write_text("consumer\n")
        git(self.work, "add", ".")
        git(self.work, "commit", "-qm", "consumer")
        consumer = git(self.work, "rev-parse", "HEAD")
        git(self.work, "checkout", "-qb", "repair", self.base)
        (self.work / "repair.txt").write_text("repair\n")
        git(self.work, "add", ".")
        git(self.work, "commit", "-qm", "repair")
        repair = git(self.work, "rev-parse", "HEAD")
        manifest = {
            "schema": "abacus.everred.replay.v1",
            "repository": REPO,
            "root_id": "ABACUS-RC-2026-0001",
            "main_base_sha": self.base,
            "consumer_head_sha": consumer,
            "repair_head_sha": repair,
            "test_profile": "unittest",
        }
        p = Preview(self.work).plan(manifest)
        self.assertEqual(p["status"], "MERGE_PREVIEW_ONLY")
        self.assertEqual(p["native_consumer_ci"], "UNKNOWN")
        self.assertEqual(git(self.work, "rev-parse", "refs/heads/consumer"), consumer)
        self.assertEqual(git(self.work, "rev-parse", "refs/heads/repair"), repair)

    def test_replay_conflicts_fail_closed(self):
        git(self.work, "checkout", "-qb", "consumer", self.base)
        (self.work / "README").write_text("consumer\n")
        git(self.work, "add", ".")
        git(self.work, "commit", "-qm", "consumer")
        consumer = git(self.work, "rev-parse", "HEAD")
        git(self.work, "checkout", "-qb", "repair", self.base)
        (self.work / "README").write_text("repair\n")
        git(self.work, "add", ".")
        git(self.work, "commit", "-qm", "repair")
        repair = git(self.work, "rev-parse", "HEAD")
        m = {
            "schema": "abacus.everred.replay.v1",
            "repository": REPO,
            "root_id": "ABACUS-RC-2026-0001",
            "main_base_sha": self.base,
            "consumer_head_sha": consumer,
            "repair_head_sha": repair,
            "test_profile": "unittest",
        }
        p = Preview(self.work).plan(m)
        self.assertEqual(p["status"], "CONFLICT")
        self.assertIsNone(p["integration_tree_sha"])


if __name__ == "__main__":
    unittest.main()


@contextmanager
def git_fixture():
    f = GitIntegration("test_replay_mergetree_disjoint")
    f.setUp()
    try:
        yield f
    finally:
        f.tearDown()


class ReplayExecution(unittest.TestCase):
    def test_no_tests_must_not_report_preview_pass(self):
        with git_fixture() as f:
            # Build distinct input commits and no tests in the temporary checkout.
            git(f.work, "checkout", "-qb", "feature1", f.base)
            (f.work / "one.txt").write_text("one")
            git(f.work, "add", ".")
            git(f.work, "commit", "-qm", "one")
            consumer = git(f.work, "rev-parse", "HEAD")
            git(f.work, "checkout", "-qb", "feature2", f.base)
            (f.work / "two.txt").write_text("two")
            git(f.work, "add", ".")
            git(f.work, "commit", "-qm", "two")
            repair = git(f.work, "rev-parse", "HEAD")
            m = {
                "schema": "abacus.everred.replay.v1",
                "repository": REPO,
                "root_id": "ABACUS-RC-2026-0001",
                "main_base_sha": f.base,
                "consumer_head_sha": consumer,
                "repair_head_sha": repair,
                "test_profile": "unittest",
            }
            r = Preview(f.work).execute(m)
            self.assertEqual(r["status"], "ISOLATED_PREVIEW_NO_TESTS")
            self.assertFalse(r["merge_authorized"])
