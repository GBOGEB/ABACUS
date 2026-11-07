"""Portable wave-claims kit tests (synthetic data only; ships in the MIP kit).

Exercises the validator, the federation roll-up, the proposer and the CLI
without reading any repository-specific register or claims file, so every
member repo that copies the kit runs the same proof.
"""

import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import wave_claims as wc

RULES = wc.load_naming_rules()
SCHEMA = RULES["claims_schema"]


def doc(repo, owns=(), participates=()):
    return {
        "schema": SCHEMA,
        "repo": repo,
        "owns": list(owns),
        "participates": list(participates),
    }


def claim(n, slug="DECK", **extra):
    base = {"key": f"QPS:W{n:03d}", "name": f"W{n:03d}_{slug}", "status": "ACTIVE"}
    base.update(extra)
    return base


def codes(found):
    return sorted(f["code"] for f in found)


def run(*cmd, cwd):
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)


class Helpers(unittest.TestCase):
    def test_tag_digest_and_lists(self):
        self.assertEqual(wc.tag(" W364_ICD "), "w364-icd")
        self.assertEqual(wc.digest("W364_ICD"), wc.digest("w364-icd"))
        self.assertEqual(wc.as_list(None), [])
        self.assertEqual(wc.as_list("x"), ["x"])
        self.assertEqual(sorted(wc.as_list({"a", "b"})), ["a", "b"])

    def test_key_number(self):
        self.assertEqual(wc.key_number("QPS:W364"), 364)
        self.assertIsNone(wc.key_number("BOOT:Wave-0"))
        self.assertIsNone(wc.key_number("QPS:W3640"))
        self.assertIsNone(wc.key_number("not a key"))

    def test_slug_and_overlap(self):
        self.assertEqual(wc.slug_of("W364_ICD_FAMILY", RULES), "ICD_FAMILY")
        self.assertIsNone(wc.slug_of("bad", RULES))
        self.assertTrue(wc._overlaps("triage/w364", "triage/w364/sub/"))
        self.assertFalse(wc._overlaps("triage/w364", "triage/w3645"))


class Validate(unittest.TestCase):
    def check(self, *owns, participates=(), repo="R", private=False):
        return wc.validate_claims(doc(repo, owns, participates), RULES, repo, private)

    def test_schema_and_repo_identity(self):
        self.assertEqual(codes(wc.validate_claims({}, RULES, "R")), ["C0_SCHEMA"])
        self.assertEqual(codes(wc.validate_claims(None, RULES, "R")), ["C0_SCHEMA"])
        found = wc.validate_claims(doc("OTHER", [claim(364)]), RULES, "R")
        self.assertEqual(codes(found), ["C0_REPO"])

    def test_name_rules(self):
        self.assertIn("C1_KEY", codes(self.check({"key": "W364", "name": "x"})))
        self.assertIn("C2_NAME", codes(self.check(claim(364, slug="x y"))))
        too_long = "A_" * 30 + "B"
        self.assertIn("C2_NAME", codes(self.check(claim(364, slug=too_long))))
        self.assertIn(
            "C3_NAME_NUMBER",
            codes(
                self.check({"key": "QPS:W364", "name": "W365_X", "status": "ACTIVE"})
            ),
        )
        self.assertIn("C4_RESERVED", codes(self.check(claim(364, slug="FINAL"))))
        self.assertIn("C5_STATUS", codes(self.check(claim(364, status="DONE"))))
        boot = {"key": "BOOT:Wave-0", "name": "W000_X", "status": "HOLD"}
        self.assertIn("C2_NAME", codes(self.check(boot)))
        self.assertEqual(
            self.check({"key": "BOOT:Wave-0", "name": "Wave-0", "status": "HOLD"}), []
        )

    def test_alias_rules(self):
        many = [f"a{i}" for i in range(9)]
        self.assertIn("C6_ALIAS", codes(self.check(claim(364, aliases=many))))
        self.assertIn("C6_ALIAS", codes(self.check(claim(364, aliases=["Bad_Alias"]))))
        self.assertIn(
            "C7_ALIAS_NUMBER", codes(self.check(claim(364, aliases=["see-w370"])))
        )
        self.assertEqual(self.check(claim(364, aliases=["w364-plan"])), [])
        self.assertIn(
            "D3_ALIAS_CLASH", codes(self.check(claim(364, aliases=["w364-deck"])))
        )

    def test_private_messages_redact_names(self):
        found = self.check(
            claim(364, slug="x y", aliases=["Secret_Alias"]), private=True
        )
        text = yaml.safe_dump(found).lower()
        self.assertNotIn("secret", text)
        self.assertNotIn("x y", text)

    def test_parent_key_and_duplicates(self):
        self.assertIn("C1_KEY", codes(self.check(claim(364, parent="W363"))))
        self.assertIn(
            "D1_DUP_OWNER", codes(self.check(claim(364), claim(364, slug="OTHER")))
        )

    def test_participation_rules(self):
        found = self.check(
            claim(364),
            participates=[
                {"key": "W113", "role": "receiver"},
                {"key": "QPS:W113", "role": "boss"},
                {"key": "QPS:W364", "role": "reviewer"},
            ],
        )
        self.assertEqual(codes(found), ["C1_KEY", "C8_ROLE", "C8_ROLE"])

    def test_path_overlap_needs_lineage(self):
        outer = claim(364, paths=["triage/w364/"])
        inner = claim(365, slug="SUB", paths=["triage/w364/sub/"], parent="QPS:W364")
        stray = claim(366, slug="STRAY", paths=["triage/w364/x"])
        self.assertEqual(self.check(outer, inner), [])
        self.assertEqual(codes(self.check(outer, inner, stray)), ["D5_PATH_OVERLAP"])


class Rollup(unittest.TestCase):
    def roll(self, sets, observed, lineage=()):
        return wc.rollup(sets, observed, set(lineage), RULES)

    def test_contested_names_aliases_and_slugs(self):
        sets = {
            "A": (doc("A", [claim(113, slug="MESH", aliases=["mesh-x"])]), False),
            "B": (doc("B", [claim(113, slug="DOW"), claim(200, slug="MESH")]), False),
            "C": (
                doc(
                    "C",
                    [claim(364, aliases=["mesh-x"])],
                    [{"key": "QPS:W113", "role": "receiver"}],
                ),
                True,
            ),
        }
        observed = {"QPS:W113": {"A", "B", "C"}, "QPS:W200": {"B"}, "QPS:W364": {"C"}}
        claims, found, census = self.roll(sets, observed)
        self.assertEqual(claims["QPS:W113"]["owner"], "CONTESTED")
        self.assertEqual(claims["QPS:W113"]["participants"], {"C": "receiver"})
        got = {(f["code"], f["key"]) for f in found}
        self.assertIn(("D1_DUP_OWNER", "QPS:W113"), got)
        self.assertIn(("D3_ALIAS_CLASH", "QPS:W364"), got)
        self.assertIn(("D4_SLUG_NO_LINEAGE", "QPS:W200"), got)
        self.assertEqual(census["contested_keys"], 1)
        rec = claims["QPS:W364"]
        self.assertIn("name_sha256", rec)
        self.assertIn("alias_sha256", rec)
        self.assertNotIn("name", rec)

    def test_name_reuse_and_public_record(self):
        sets = {
            "A": (
                doc(
                    "A",
                    [
                        claim(
                            300,
                            slug="X",
                            aliases=["x-plan"],
                            paths=["p/w300/"],
                            parent="QPS:W299",
                        )
                    ],
                ),
                False,
            ),
            "B": (
                doc("B", [{"key": "QPS:W301", "name": "W300_X", "status": "ACTIVE"}]),
                False,
            ),
        }
        claims, found, _ = self.roll(sets, {"QPS:W300": {"A"}, "QPS:W301": {"B"}})
        self.assertIn("D2_NAME_REUSE", codes(found))
        self.assertEqual(claims["QPS:W300"]["aliases"], ["x-plan"])
        self.assertEqual(claims["QPS:W300"]["paths"], ["p/w300/"])
        self.assertEqual(claims["QPS:W300"]["parent"], ["QPS:W299"])

    def test_lineage_numbering_and_overlap_census(self):
        sets = {
            "R": (
                doc(
                    "R",
                    [
                        claim(364, slug="ICD", status="CLOSED"),
                        claim(366, slug="ICD"),
                        claim(50, slug="HOLE"),
                        claim(382, slug="NEW_PLANT"),
                    ],
                    [{"key": "QPS:W900", "role": "consumer"}],
                ),
                False,
            )
        }
        observed = {"QPS:W364": {"R", "Q"}, "QPS:W366": {"R"}, "QPS:W381": {"R"}}
        _, found, census = self.roll(sets, observed, [("QPS:W366", "QPS:W364")])
        got = codes(found)
        self.assertNotIn("D4_SLUG_NO_LINEAGE", got)
        self.assertIn("N1_BACKFILL", got)
        self.assertIn("O1_UNDECLARED_PARTICIPANT", got)
        self.assertIn("O2_ORPHAN_PARTICIPATION", got)
        self.assertEqual(census["next_free"], {"QPS": "W383"})
        self.assertEqual(census["undeclared_participants"], 1)
        self.assertEqual(census["claimed_unobserved"], 2)

    def test_invalid_claims_file_is_reported_not_crashing(self):
        _, found, census = self.roll({"R": ({"schema": "bad"}, False)}, {})
        self.assertEqual(codes(found), ["C0_SCHEMA"])
        self.assertEqual(census["claimed_keys"], 0)


class Propose(unittest.TestCase):
    def test_wave_segment_and_slugs(self):
        self.assertEqual(
            wc._wave_segment("triage/w368/x", 368), ("triage/w368/", "w368")
        )
        self.assertIsNone(wc._wave_segment("triage/shared", 368))
        self.assertEqual(
            wc._slug_from_text("QPS_W368_COOLDOWN_v2", 368, RULES), "COOLDOWN"
        )
        self.assertIsNone(wc._slug_from_text("W368_FINAL_v1", 368, RULES))

    def test_propose_from_register_and_tree(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            run("git", "init", "-q", cwd=repo)
            for rel in [
                "triage/w368/QPS_W368_COOLDOWN_FULL_REBUILD_v0.1.yaml",
                "triage/w368/sub/notes.md",
                "triage/w369/README.md",
                "triage/w372/plant_sync/data.yaml",
            ]:
                (repo / rel).parent.mkdir(parents=True, exist_ok=True)
                (repo / rel).write_text("x\n", encoding="utf-8")
            run("git", "add", ".", cwd=repo)
            run(
                "git",
                "-c",
                "user.name=t",
                "-c",
                "user.email=t@example.invalid",
                "commit",
                "-qm",
                "f",
                cwd=repo,
            )
            register = {
                "waves": [
                    {
                        "key": "QPS:W368",
                        "namespace": "QPS",
                        "id": "W368",
                        "confidence": "exact",
                        "repos": {"R": {"paths": 2, "anchor": "triage/w368"}},
                    },
                    {
                        "key": "QPS:W369",
                        "namespace": "QPS",
                        "id": "W369",
                        "confidence": "exact",
                        "repos": {"R": {"paths": 1, "anchor": "triage/w369"}},
                    },
                    {
                        "key": "QPS:W370",
                        "namespace": "QPS",
                        "id": "W370",
                        "confidence": "exact",
                        "repos": {
                            "R": {"paths": 1, "anchor": "x"},
                            "S": {"paths": 1, "anchor": "y"},
                        },
                    },
                    {
                        "key": "QPS:W371",
                        "namespace": "QPS",
                        "id": "W371",
                        "confidence": "exact",
                        "repos": {
                            "R": {"paths": 1, "anchor": "x"},
                            "S": {"paths": 5, "anchor": "y"},
                        },
                    },
                    {
                        "key": "QPS:W372",
                        "namespace": "QPS",
                        "id": "W372",
                        "confidence": "exact",
                        "repos": {"R": {"paths": 1, "anchor": "triage/w372"}},
                    },
                    {
                        "key": "HYG:W3",
                        "namespace": "HYG",
                        "id": "W3",
                        "confidence": "exact",
                        "repos": {"R": {"paths": 9, "anchor": "g"}},
                    },
                ]
            }
            draft = wc.propose(register, "R", RULES, repo_path=repo)
            names = {c["key"]: c["name"] for c in draft["owns"]}
            self.assertEqual(names["QPS:W368"], "W368_COOLDOWN_FULL_REBUILD")
            self.assertEqual(names["QPS:W372"], "W372_PLANT_SYNC")
            self.assertEqual(draft["_proposal"]["needs_name"], ["QPS:W369"])
            self.assertEqual(draft["_proposal"]["contested_ties"], ["QPS:W370"])
            body = {k: v for k, v in draft.items() if k != "_proposal"}
            self.assertEqual(wc.validate_claims(body, RULES, "R"), [])
            plain = wc.propose(register, "R", RULES)
            self.assertIn("QPS:W368", plain["_proposal"]["needs_name"])


class Cli(unittest.TestCase):
    def test_validate_and_propose_commands(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "claims.yaml"
            path.write_text(
                yaml.safe_dump(doc("GBOGEB/X", [claim(364)])), encoding="utf-8"
            )
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(
                    wc.main(["validate", str(path), "--expected-repo", "GBOGEB/X"]), 0
                )
            self.assertIn("1 owned, 0 errors", out.getvalue())
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = wc.main(
                    ["validate", str(path), "--expected-repo", "GBOGEB/Y", "--private"]
                )
            self.assertEqual(code, 1)
            self.assertIn("C0_REPO", out.getvalue())
            register = Path(d) / "register.yaml"
            register.write_text(yaml.safe_dump({"waves": []}), encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(
                    wc.main(
                        ["propose", "--repo", "GBOGEB/X", "--register", str(register)]
                    ),
                    0,
                )
            self.assertEqual(yaml.safe_load(out.getvalue())["owns"], [])


if __name__ == "__main__":
    unittest.main()
