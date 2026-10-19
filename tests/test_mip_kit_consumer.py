"""ABACUS consumer tests for the canonical MIP kit and its LDAB attach step.

``tests/test_mip_kit.py`` (copied from CODEX) covers the manifest and the
surface config. These tests drive the kit emitter and verifier end to end on
synthetic fixtures (no dependency on a clean checkout) and pin the ABACUS-only
``ldab_telemetry`` block that ``scripts/mip_ldab_n2_attach.py`` adds.
"""

from __future__ import annotations

import datetime
import importlib.util
import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SHA = "a" * 40
LANE = "repo_self_assess_debug_ldab"
NESTED = "integration/codespace_jyperter"


def _load(name: str, relpath: str):
    # The kit emitter imports ``datetime.UTC`` (Python 3.11+); ABACUS also
    # collects tests on 3.10, so alias it only while the module executes.
    shim = not hasattr(datetime, "UTC")
    if shim:
        datetime.UTC = datetime.timezone.utc  # noqa: UP017 (3.10 has no UTC)
    try:
        spec = importlib.util.spec_from_file_location(name, ROOT / relpath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        if shim:
            del datetime.UTC
    return module


kit = _load("consumer_mip_kit_manifest", "scripts/mip_kit_manifest.py")
emitter = _load("consumer_mip_repo_self_index", "scripts/mip_repo_self_index.py")
verifier = _load("consumer_mip_verify_self_index", "scripts/mip_verify_self_index.py")
attach = _load("consumer_mip_ldab_n2_attach", "scripts/mip_ldab_n2_attach.py")
# The verifier binds its default config path at import; tests pass their own.
_LOAD_SURFACE = verifier.load_surface


def _script(path: Path, payload: dict) -> Path:
    """A fake emitter/diagnostic: writes ``payload`` to ``--output``."""
    path.write_text(
        textwrap.dedent(
            f"""
            import json, sys
            out = sys.argv[sys.argv.index("--output") + 1]
            open(out, "w", encoding="utf-8").write(json.dumps({payload!r}))
            """
        ),
        encoding="utf-8",
    )
    return path


def _health(sha: str = SHA) -> dict:
    return {
        "verification": "PASS",
        "exact_sha": sha,
        "execution_context": "transient_controlled_fixture",
        "return_state": "IMPROVED",
        "delta": -1,
        "source_checkout_unchanged": True,
        "raw_receipt_retention": "transient_runner_only",
        "promotion_authority": False,
    }


def _root_receipt(sha: str = SHA) -> dict:
    return {
        "repo": {"sha": sha, "root": "/x", "branch": "b"},
        "generated_at": "now",
        "census": {"file_count": 3},
        "assessments": {
            LANE: {"status": "green"},
            "repo_self_assess_runners_mcp": {"status": "green"},
            "repo_self_assess_codz_health_selfheal": {
                "status": "green",
                "evidence": _health(sha),
            },
            "repo_self_produce": {"status": "green"},
        },
    }


def _nested_receipt(sha: str = SHA, debug: str = "green") -> dict:
    paths = ["tests/test_smoke_federation.py"]
    return {
        "surface": {"path": NESTED, "parent_sha": sha, "parent_branch": "b"},
        "census": {"file_count": 1},
        "assessments": {
            LANE: {
                "status": debug,
                "signals": 1,
                "sample_paths": paths,
                "all_candidate_paths": paths,
            }
        },
    }


def _diagnostic(sha: str = SHA, verification: str = "PASS") -> dict:
    return {
        "repository": "GBOGEB/ABACUS",
        "diagnostic": "nested_debug_ldab",
        "parent_sha": sha,
        "source_contract": f"{NESTED}/tests/test_smoke_federation.py",
        "source_contract_sha256": "b" * 64,
        "verification": verification,
        "checks": {"contract": verification == "PASS"},
        "failed_checks": [] if verification == "PASS" else ["contract"],
        "raw_receipt_retention": "transient_runner_only",
    }


# --- kit emitter -------------------------------------------------------------


def test_emitter_classify_lanes_from_synthetic_tree():
    files = [
        Path(".github/workflows/ci.yml"),
        Path("Dockerfile"),
        Path("scripts/debug_probe.py"),
        Path("scripts/self_heal.py"),
        Path(".codex/skills/demo/SKILL.md"),
        Path(".codex/skills/demo/agents/openai.yaml"),
        Path(".codex/skills/demo/scripts/validate_receipt.py"),
        Path(".codex/skills/demo/references/receipt-contract.md"),
    ]
    green = emitter.classify(files, {**_health(None), "delta": -1})
    assert green[LANE]["status"] == "green"
    assert green["repo_self_assess_runners_mcp"]["docker_count"] == 1
    assert green["repo_self_produce"]["complete_skill_paths"] == [".codex/skills/demo"]
    health = green["repo_self_assess_codz_health_selfheal"]
    assert health["status"] == "amber"  # exact_sha None never matches HEAD
    assert health["evidence"]["verification"] == "PASS"

    empty = emitter.classify([], None)
    assert {lane["status"] for lane in empty.values()} == {"red"}
    partial = emitter.classify([Path("tools/skill_notes.txt")], None)
    assert partial["repo_self_produce"]["status"] == "amber"


def test_emitter_health_green_when_probe_binds_head(monkeypatch):
    monkeypatch.setattr(emitter, "run_git", lambda args: SHA)
    result = emitter.classify([], _health(SHA))
    assert result["repo_self_assess_codz_health_selfheal"]["status"] == "green"


def test_emitter_probe_outcomes(tmp_path: Path):
    assert emitter.run_health_selfheal_probe(tmp_path / "absent.py") is None
    ok = _script(tmp_path / "ok.py", {"verification": "PASS"})
    assert emitter.run_health_selfheal_probe(ok) == {"verification": "PASS"}
    failing = tmp_path / "fail.py"
    failing.write_text("raise SystemExit(3)\n", encoding="utf-8")
    assert emitter.run_health_selfheal_probe(failing)["failed_checks"] == [
        "probe_execution"
    ]
    garbled = tmp_path / "garbled.py"
    garbled.write_text(
        "import sys\nopen(sys.argv[2], 'w').write('{')\n", encoding="utf-8"
    )
    assert emitter.run_health_selfheal_probe(garbled)["failed_checks"] == [
        "probe_receipt_parse"
    ]


def test_emitter_main_on_minimal_tree(tmp_path: Path, monkeypatch, capsys):
    (tmp_path / "notes.md").write_text("TODO: debug later\n", encoding="utf-8")
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "trace.json").write_text("{}", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "x.pyc").write_bytes(b"\0")
    monkeypatch.setattr(emitter, "ROOT", tmp_path)
    monkeypatch.setattr(emitter, "load_surface_config", lambda: {"health_probe": None})
    out = tmp_path / "out" / "receipt.json"
    monkeypatch.setattr(sys, "argv", ["emitter", "--output", str(out)])
    assert emitter.main() == 0
    receipt = json.loads(out.read_text(encoding="utf-8"))
    assert receipt["census"]["file_count"] == 2
    assert receipt["assessments"][LANE]["status"] == "green"
    assert "Wrote out/receipt.json" in capsys.readouterr().out

    outside = tmp_path.parent / f"{tmp_path.name}-outside.json"
    monkeypatch.setattr(sys, "argv", ["emitter", "--output", str(outside)])
    assert emitter.main() == 0
    assert f"Wrote {outside.name}" in capsys.readouterr().out
    outside.unlink()


# --- kit verifier ------------------------------------------------------------


def test_verifier_pair_repeatability_and_sha(tmp_path: Path):
    fake = _script(tmp_path / "emit.py", _root_receipt())
    receipt, norm = verifier.verify_pair(
        fake, tmp_path / "1.json", tmp_path / "2.json", SHA, "repo", "sha"
    )
    assert receipt["repo"]["sha"] == SHA
    assert "generated_at" not in norm and "root" not in norm["repo"]
    with pytest.raises(SystemExit, match="SHA mismatch"):
        verifier.verify_pair(
            fake, tmp_path / "3.json", tmp_path / "4.json", "c" * 40, "repo", "sha"
        )
    drifting = tmp_path / "drift.py"
    drifting.write_text(
        "import json, sys, uuid\n"
        f"json.dump({{'repo': {{'sha': '{SHA}'}}, 'x': uuid.uuid4().hex}},"
        " open(sys.argv[2], 'w'))\n",
        encoding="utf-8",
    )
    with pytest.raises(SystemExit, match="not repeatable"):
        verifier.verify_pair(
            drifting, tmp_path / "5.json", tmp_path / "6.json", SHA, "repo", "sha"
        )


def test_verifier_health_validation():
    receipt = _root_receipt()
    result = verifier.validate_health_selfheal(
        receipt, verifier.status_map(receipt), SHA
    )
    assert result["verification"] == "PASS" and result["delta"] == -1
    receipt["assessments"]["repo_self_assess_codz_health_selfheal"]["evidence"][
        "delta"
    ] = True
    with pytest.raises(SystemExit, match="delta"):
        verifier.validate_health_selfheal(receipt, verifier.status_map(receipt), SHA)


def test_verifier_nested_surfaces(tmp_path: Path):
    emit = _script(tmp_path / "nested.py", _nested_receipt())
    diag = _script(tmp_path / "diag.py", _diagnostic())
    rows, diags = verifier.verify_nested_surfaces(
        [{"path": NESTED, "emitter": str(emit), "diagnostic": str(diag)}],
        tmp_path,
        SHA,
    )
    assert rows[0]["path"] == NESTED and rows[0]["assessments"][LANE] == "GREEN"
    assert diags[0]["passed_checks"] == ["contract"]
    rows, diags = verifier.verify_nested_surfaces(
        [{"path": NESTED, "emitter": str(emit)}], tmp_path, SHA
    )
    assert len(rows) == 1 and diags == []

    with pytest.raises(SystemExit, match="emitter is missing"):
        verifier.verify_nested_surfaces(
            [{"path": NESTED, "emitter": str(tmp_path / "absent.py")}], tmp_path, SHA
        )
    cases = [
        (_nested_receipt(), _diagnostic(sha="c" * 40), "diagnostic SHA mismatch"),
        (_nested_receipt(), _diagnostic(verification="FAIL"), "diagnostic failed"),
        (_nested_receipt(debug="red"), _diagnostic(), "not GREEN"),
    ]
    for index, (nested, diagnostic, message) in enumerate(cases):
        emit = _script(tmp_path / f"n{index}.py", nested)
        diag = _script(tmp_path / f"d{index}.py", diagnostic)
        with pytest.raises(SystemExit, match=message):
            verifier.verify_nested_surfaces(
                [{"path": NESTED, "emitter": str(emit), "diagnostic": str(diag)}],
                tmp_path,
                SHA,
            )


def test_verifier_lane_maturity_and_kit_identity():
    scores = verifier.lane_maturity(
        {lane: "GREEN" for lane in verifier.LANES},
        health_executed=True,
        skill_executed=True,
        diagnostic_executed=False,
    )
    assert scores[verifier.INDEX_LANE] == 2
    assert scores[verifier.HEALTH_LANE] == 2
    assert scores[verifier.DEBUG_LANE] == 1
    assert scores[verifier.RUNNERS_LANE] == 1
    identity = verifier.kit_identity()
    canonical = json.loads(kit.MANIFEST.read_text(encoding="utf-8"))
    assert identity["kit_digest_sha256"] == canonical["kit_digest_sha256"]


def test_verifier_rejects_incomplete_skill_package(tmp_path: Path, monkeypatch):
    skill = ROOT / ".codex" / "skills" / "mip-repo-self-index"
    with pytest.raises(SystemExit, match="root_self_produce_green"):
        verifier.validate_shareable_skill(skill, {}, tmp_path, SHA, {})
    monkeypatch.setattr(verifier, "ROOT", tmp_path)
    with pytest.raises(SystemExit, match="entrypoint_exists"):
        verifier.validate_shareable_skill(tmp_path, {}, tmp_path, SHA, {})


def _run_verifier_main(tmp_path: Path, monkeypatch, surface: dict) -> dict:
    config = tmp_path / "mip_surface.json"
    config.write_text(json.dumps(surface), encoding="utf-8")
    monkeypatch.setattr(verifier, "SURFACE_CONFIG", config)
    monkeypatch.setattr(verifier, "load_surface", lambda: _LOAD_SURFACE(config))
    monkeypatch.setattr(
        verifier, "ROOT_EMITTER", _script(tmp_path / "root.py", _root_receipt())
    )
    monkeypatch.setattr(verifier, "git", lambda *args: SHA)
    monkeypatch.setenv("EXPECTED_SHA", SHA)
    monkeypatch.setenv("GITHUB_REPOSITORY", "GBOGEB/ABACUS")
    summary = tmp_path / "out" / "summary.json"
    monkeypatch.setattr(sys, "argv", ["verify", "--summary", str(summary)])
    assert verifier.main() == 0
    return json.loads(summary.read_text(encoding="utf-8"))


def test_verifier_main_end_to_end_with_abacus_surface(tmp_path: Path, monkeypatch):
    emit = _script(tmp_path / "nested.py", _nested_receipt())
    diag = _script(tmp_path / "diag.py", _diagnostic())
    surface = json.loads((ROOT / "MIP" / "mip_surface.json").read_text("utf-8"))
    surface["nested_surfaces"] = [
        {"path": NESTED, "emitter": str(emit), "diagnostic": str(diag)}
    ]
    summary = _run_verifier_main(tmp_path, monkeypatch, surface)
    assert summary["verification"] == "PASS"
    assert summary["health_selfheal"]["verification"] == "PASS"
    assert summary["shareable_skill"]["validated_head_sha"] == SHA
    assert summary["nested_surface"]["path"] == NESTED
    assert summary["nested_diagnostic"]["diagnostic"] == "nested_debug_ldab"
    assert summary["required_green"] == sorted(surface["required_green"])
    # index 2 + executed debug 2 + heuristic runners 1 + health 2 + skill 2
    assert summary["maturity_score"] == 9


def test_verifier_main_ratchets_and_sha_guard(tmp_path: Path, monkeypatch):
    base = {"program": "MIP", "required_green": ["repo_self_produce"]}
    with pytest.raises(SystemExit, match="no shareable skill"):
        _run_verifier_main(tmp_path, monkeypatch, base)
    receipt = _root_receipt()
    receipt["assessments"]["repo_self_assess_runners_mcp"]["status"] = "amber"
    monkeypatch.setattr(
        verifier, "ROOT_EMITTER", _script(tmp_path / "amber.py", receipt)
    )
    config = tmp_path / "amber.json"
    config.write_text(
        json.dumps(
            {"program": "MIP", "required_green": ["repo_self_assess_runners_mcp"]}
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(verifier, "load_surface", lambda: _LOAD_SURFACE(config))
    monkeypatch.setattr(sys, "argv", ["verify", "--summary", str(tmp_path / "s.json")])
    with pytest.raises(SystemExit, match="not GREEN"):
        verifier.main()
    monkeypatch.setenv("EXPECTED_SHA", "c" * 40)
    with pytest.raises(SystemExit, match="checkout SHA mismatch"):
        verifier.main()


# --- ABACUS LDAB attach step ------------------------------------------------


def _minimal_tree(tmp_path: Path, count: int) -> Path:
    tree = tmp_path / "tree"
    for index in range(count):
        target = tree / "debug" / f"probe_{index:02d}.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")
    return tree


def test_attach_root_inventory_is_complete_beyond_kit_sample(tmp_path, monkeypatch):
    monkeypatch.setattr(emitter, "ROOT", _minimal_tree(tmp_path, 25))
    root = attach.root_debug_receipt(emitter, SHA)
    lane = root["assessments"][LANE]
    assert lane["signals"] == 25
    assert len(lane["sample_paths"]) == 20
    assert lane["all_candidate_paths"][:20] == lane["sample_paths"]
    assert emitter.sample([Path("a"), Path("b")], limit=1) == ["a"]


def test_attach_fails_closed_on_inventory_mismatch(tmp_path, monkeypatch):
    monkeypatch.setattr(emitter, "ROOT", _minimal_tree(tmp_path, 3))
    real_classify = emitter.classify
    calls = []

    def classify(files, probe):
        calls.append(1)
        result = real_classify(files, probe)
        if len(calls) == 2:
            result[LANE]["sample_paths"] = result[LANE]["sample_paths"][:1]
        return result

    monkeypatch.setattr(emitter, "classify", classify)
    with pytest.raises(SystemExit, match="inventory does not match"):
        attach.root_debug_receipt(emitter, SHA)


def test_attach_main_adds_ldab_block(tmp_path: Path, monkeypatch, capsys):
    emit = _script(tmp_path / "nested.py", _nested_receipt())
    diag = _script(tmp_path / "diag.py", _diagnostic())
    surface = {
        "program": "MIP",
        "nested_surfaces": [
            {"path": NESTED, "emitter": str(emit), "diagnostic": str(diag)}
        ],
    }
    config = tmp_path / "surface.json"
    config.write_text(json.dumps(surface), encoding="utf-8")
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "verification": "PASS",
                "head_sha": SHA,
                "root_self_index": {"assessments": {LANE: "GREEN"}},
            }
        ),
        encoding="utf-8",
    )
    tree = _minimal_tree(tmp_path, 2)
    real_load = attach._load

    def load(name, path):
        module = (
            _load("attach_emitter", "scripts/mip_repo_self_index.py")
            if path.name == "mip_repo_self_index.py"
            else real_load(name, path)
        )
        if path.name == "mip_repo_self_index.py":
            module.ROOT = tree
        return module

    monkeypatch.setattr(attach, "_load", load)
    monkeypatch.setattr(attach, "_git_head", lambda: SHA)
    monkeypatch.setattr(attach, "SURFACE_CONFIG", config)
    monkeypatch.setenv("GITHUB_REPOSITORY", "GBOGEB/ABACUS")
    assert attach.main(["--summary", str(summary_path)]) == 0
    ldab = json.loads(summary_path.read_text(encoding="utf-8"))["ldab_telemetry"]
    assert ldab["schema"] == "mip.ldab.telemetry.v1"
    assert ldab["source_sha"] == SHA
    assert ldab["source_census"]["root"]["inventory_complete"] is True
    assert ldab["diagnostic_execution"]["state"] == "EXECUTED_PASS"
    assert ldab["merge_admission"] == "HOLD"
    assert "OBSERVED" in capsys.readouterr().out


def test_attach_rejects_wrong_head_or_status(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(attach, "_git_head", lambda: SHA)
    with pytest.raises(SystemExit, match="not a PASS"):
        attach.attach({"verification": "PASS", "head_sha": "c" * 40}, {}, tmp_path)
    tree = _minimal_tree(tmp_path, 1)
    real_load = attach._load

    def load(name, path):
        if path.name == "mip_repo_self_index.py":
            module = _load("attach_emitter_2", "scripts/mip_repo_self_index.py")
            module.ROOT = tree
            return module
        return real_load(name, path)

    monkeypatch.setattr(attach, "_load", load)
    summary = {
        "verification": "PASS",
        "head_sha": SHA,
        "root_self_index": {"assessments": {LANE: "RED"}},
    }
    with pytest.raises(SystemExit, match="status differs"):
        attach.attach(summary, {}, tmp_path)
    assert attach.nested_inputs({"nested_surfaces": []}, tmp_path) == (None, None)


def test_attach_reads_real_head():
    head = subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
    ).strip()
    assert attach._git_head() == head
