"""Fail-closed member-claims and federation wave-name controls (synthetic only)."""
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import wave_claims as waves  # noqa: E402

RULES = waves.load_naming_rules()
REPO = "GBOGEB/ABACUS"


def owned(number, slug="ALPHA", aliases=(), parents=()):
    return {
        "key": f"QPS:W{number:03d}",
        "name": f"W{number:03d}_{slug}",
        "status": "ACTIVE",
        "aliases": list(aliases),
        "parent": list(parents),
        "paths": [f"waves/w{number:03d}/"],
    }


def doc(*entries, repo=REPO):
    return {"schema": RULES["claims_schema"], "repo": repo,
            "owns": list(entries), "participates": []}


def errors(payload):
    return waves.validate_claims(payload, RULES, REPO)


class WaveClaimsContractTests(unittest.TestCase):
    def test_expected_repository_is_independent_of_claimed_identity(self):
        result = errors(doc(owned(100), repo="GBOGEB/UNRELATED"))
        self.assertIn("C0_REPO", {r["code"] for r in result})

    def test_alias_cannot_equal_its_own_canonical_name(self):
        result = errors(doc(owned(100, aliases=["w100-alpha"])))
        self.assertIn("D3_ALIAS_CLASH", {r["code"] for r in result})

    def test_duplicate_aliases_within_one_wave_are_rejected(self):
        result = errors(doc(owned(100, aliases=["old-name", "old-name"])))
        self.assertIn("D3_ALIAS_CLASH", {r["code"] for r in result})

    def test_duplicate_aliases_across_owned_waves_are_rejected_locally(self):
        result = errors(doc(owned(100, aliases=["shared"]), owned(101, "BETA", ["shared"])))
        self.assertIn("D3_ALIAS_CLASH", {r["code"] for r in result})

    def test_alias_matching_another_name_is_rejected(self):
        result = errors(doc(owned(100, aliases=["w101-beta"]), owned(101, "BETA")))
        self.assertIn("D3_ALIAS_CLASH", {r["code"] for r in result})

    def test_future_holder_cannot_satisfy_earlier_slug_parent(self):
        records = doc(
            owned(100),
            owned(200, parents=["QPS:W300"]),
            owned(300, parents=["QPS:W100"]),
        )
        observed = {row["key"]: {REPO} for row in records["owns"]}
        _, found, _ = waves.rollup({REPO: (records, False)}, observed, set(), RULES)
        self.assertTrue(any(v["code"] == "D4_SLUG_NO_LINEAGE"
                            and v["key"] == "QPS:W200" for v in found))

    def test_successors_can_carry_slug_from_earlier_parent(self):
        records = doc(
            owned(100),
            owned(200, parents=["QPS:W100"]),
            owned(300, parents=["QPS:W200"]),
        )
        observed = {row["key"]: {REPO} for row in records["owns"]}
        _, found, _ = waves.rollup({REPO: (records, False)}, observed, set(), RULES)
        self.assertFalse(any(v["code"] == "D4_SLUG_NO_LINEAGE" for v in found))

    def test_cli_requires_repo_identity_and_rejects_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "claims.yaml"
            path.write_text(yaml.safe_dump(doc(owned(100), repo="GBOGEB/OTHER")),
                            encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as missing:
                    waves.main(["validate", str(path)])
            self.assertEqual(missing.exception.code, 2)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(
                    waves.main(["validate", str(path), "--expected-repo", REPO]), 1
                )

    def test_private_diagnostics_do_not_expose_alias_text(self):
        result = waves.validate_claims(doc(owned(100, aliases=["w100-alpha"])),
                                       RULES, REPO, private=True)
        self.assertTrue(any(v["code"] == "D3_ALIAS_CLASH" for v in result))
        self.assertFalse(any("w100-alpha" in v["detail"] for v in result))


if __name__ == "__main__":
    unittest.main()
