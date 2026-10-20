"""Native contract and adverse-control tests for the read-only peer scanner."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1]/"tools"/"ci"/"dependency_spine_peer_scan.py"
sp = importlib.util.spec_from_file_location("dependency_spine_peer_scan", PATH)
assert sp and sp.loader
mod = importlib.util.module_from_spec(sp)
sp.loader.exec_module(mod)
SHA = "a"*40
REPO = "GBOGEB/CODEX"

class PeerScanTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)/"root"
        (self.root/".github"/"workflows").mkdir(parents=True)
        (self.root/".github"/"dependabot.yml").write_text('''version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: weekly
''',encoding="utf-8")
        (self.root/".github"/"workflows"/"ci.yml").write_text('''name: test
jobs:
  scanner:
    steps:
      # - uses: actions/checkout@v1
      - uses: actions/checkout@v7.0.1
      - uses: ./local
      - uses: docker://alpine:3
''',encoding="utf-8")
        self.out=Path(t.name)/"out"

    def test_count_refs_and_config(self):
        r=mod.observe(self.root,REPO,SHA,observed_sha=SHA)
        self.assertEqual((r["workflow_count"],r["action_reference_count"]), (1,3))
        self.assertEqual(r["dependabot_ecosystems"],[{"ecosystem":"github-actions","directory":"/"}])
        self.assertEqual(len(r["checkout_refs"]),1)

    def test_ignore_nested_workflow(self):
        p=self.root/".github"/"workflows"/"old"
        p.mkdir();(p/"ci.yml").write_text("- uses: actions/checkout@v2\n")
        self.assertEqual(mod.observe(self.root,REPO,SHA,observed_sha=SHA)["workflow_count"],1)

    def test_missing_dependabot_is_not_fail_or_false_coverage(self):
        (self.root/".github"/"dependabot.yml").unlink()
        r=mod.observe(self.root,REPO,SHA,observed_sha=SHA)
        self.assertFalse(r["dependabot_present"])
        self.assertIsNone(r["measurement"]["reference_upgrade_coverage_pct"])

    def test_sha_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError,"EXACT_HEAD_MISMATCH"):
            mod.observe(self.root,REPO,"b"*40,observed_sha=SHA)

    def test_malformed_sha_rejected(self):
        with self.assertRaisesRegex(ValueError,"BAD_EXPECTED_SHA"):
            mod.observe(self.root,REPO,"branch",observed_sha=SHA)

    def test_untrusted_repo_rejected(self):
        with self.assertRaisesRegex(ValueError,"REPOSITORY_NOT_IN_FLEET"):
            mod.observe(self.root,"attacker/repo",SHA,observed_sha=SHA)

    def test_stable_codec(self):
        r=mod.observe(self.root,REPO,SHA,observed_sha=SHA)
        self.assertEqual(mod.canonical(r),mod.canonical(r))

    def test_digest_drift_fails(self):
        data=mod.observe(self.root,REPO,SHA,observed_sha=SHA)
        self.out.mkdir()
        raw=mod.canonical(data)
        (self.out/"PEER_CENSUS.json").write_bytes(raw)
        (self.out/"PEER_SHA256.json").write_bytes(mod.canonical({"schema":"qps.dependency_spine.peer_sha256.v1","repo":REPO,"head_sha":SHA,"qualified_status":"LEXICAL_CENSUS_ONLY","files":{"PEER_CENSUS.json":mod.digest(raw)}}))
        mod.verify(self.out,REPO,SHA)
        (self.out/"PEER_CENSUS.json").write_bytes(raw+b" ")
        with self.assertRaisesRegex(ValueError,"DIGEST_MISMATCH"):
            mod.verify(self.out,REPO,SHA)

    def test_forged_promotion_rejected_even_with_resigned_digest(self):
        r=mod.observe(self.root,REPO,SHA,observed_sha=SHA)
        r["governance"]["remote_dispatch_authorized"]=True
        self.out.mkdir()
        raw=mod.canonical(r)
        (self.out/"PEER_CENSUS.json").write_bytes(raw)
        (self.out/"PEER_SHA256.json").write_bytes(mod.canonical({"schema":"qps.dependency_spine.peer_sha256.v1","repo":REPO,"head_sha":SHA,"qualified_status":"LEXICAL_CENSUS_ONLY","files":{"PEER_CENSUS.json":mod.digest(raw)}}))
        with self.assertRaisesRegex(ValueError,"GOVERNANCE_PROMOTION_FORBIDDEN"):
            mod.verify(self.out,REPO,SHA)

    def test_absent_directory_is_empty_not_fleet_failure(self):
        (self.root/".github"/"workflows"/"ci.yml").unlink()
        self.assertEqual(mod.observe(self.root,REPO,SHA,observed_sha=SHA)["workflow_count"],0)

    def test_wrong_repo_on_verify(self):
        data=mod.observe(self.root,REPO,SHA,observed_sha=SHA)
        self.out.mkdir();raw=mod.canonical(data)
        (self.out/"PEER_CENSUS.json").write_bytes(raw)
        (self.out/"PEER_SHA256.json").write_bytes(mod.canonical({"schema":"qps.dependency_spine.peer_sha256.v1","repo":REPO,"head_sha":SHA,"qualified_status":"LEXICAL_CENSUS_ONLY","files":{"PEER_CENSUS.json":mod.digest(raw)}}))
        with self.assertRaisesRegex(ValueError,"REPO_IDENTITY_MISMATCH"):
            mod.verify(self.out,"GBOGEB/ABACUS",SHA)
