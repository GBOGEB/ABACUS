"""Lane-B wave 11: census tuple check, DMAIC contract, docs links, review package."""

import hashlib
import importlib.util
import json
import logging
import sys
import types

import pytest

from ._l2_loader import REPO_ROOT, load

fake_dmaic = types.ModuleType("dmaic")
fake_contract = types.ModuleType("dmaic.contract")
fake_contract.validate_contract = lambda payload: []
fake_dmaic.contract = fake_contract

_saved_path = list(sys.path)
try:
    dc = load(
        "scripts/validate_dmaic_contract.py",
        deps={"dmaic": fake_dmaic, "dmaic.contract": fake_contract},
    )
finally:
    sys.path[:] = _saved_path
dl = load("scripts/validate_docs_links.py")
rp = load("scripts/validate_review_package.py")

CENSUS_SCRIPT = (
    REPO_ROOT / "scripts/deterministic_census_authority_and_contract_check.py"
)
TUPLE_REL = "triage/census/roundtrip/TRIAGE_W62_IMMUTABLE_TUPLE.json"


# ---------------------------------------------------- census authority check


def _tuple(**overrides):
    obj = {
        "schema": "triage.tuple/v1",
        "tuple_id": "W62-T1",
        "child_repo": "GBOGEB/ABACUS",
        "authority": "CHILD_ENGINEERING_AUTHORITY",
        "operation": "CENSUS_DOV_PROOF",
        "disposition_enum": ["ACCEPT", "REJECT", "DEFER"],
    }
    obj.update(overrides)
    return obj


def _run_census(root):
    """Execute the module-level script with __file__ pointing under ``root``.

    The stand-in basename differs from the real one so coverage keeps
    attributing executed lines to the real script (co_filename).
    """
    spec = importlib.util.spec_from_file_location("l2_w11_det_census", CENSUS_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(root / "scripts" / "census_stand_in.py")
    spec.loader.exec_module(module)
    return module


def _write_tuple(root, obj):
    path = root / TUPLE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")


def test_census_check_passes_and_prints_digest(tmp_path, capsys):
    obj = _tuple()
    _write_tuple(tmp_path, obj)
    module = _run_census(tmp_path)
    assert module.ROOT == tmp_path
    canon = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    lines = capsys.readouterr().out.splitlines()
    assert lines == [
        "method=deterministic_census_authority_and_contract_check/v1",
        "tuple_id=W62-T1",
        "canonical_sha256=" + hashlib.sha256(canon).hexdigest(),
        "authority_overlap=false",
        "engineering_mutation=false",
        "status=PASS",
        "recommendation=ACCEPT",
    ]


def test_census_check_missing_tuple(tmp_path):
    with pytest.raises(SystemExit, match="FAIL missing tuple"):
        _run_census(tmp_path)


def _without(*keys):
    obj = _tuple()
    for key in keys:
        obj.pop(key)
    return obj


@pytest.mark.parametrize(
    "obj, message",
    [
        (_without("schema", "child_repo"), "FAIL missing fields: child_repo,schema"),
        (_tuple(authority="PARENT"), "FAIL authority mismatch"),
        (_tuple(operation="OTHER"), "FAIL operation mismatch"),
        (_tuple(disposition_enum=["ACCEPT"]), "FAIL disposition enum mismatch"),
    ],
)
def test_census_check_rejections(tmp_path, capsys, obj, message):
    _write_tuple(tmp_path, obj)
    with pytest.raises(SystemExit) as exc:
        _run_census(tmp_path)
    assert exc.value.code == message
    assert capsys.readouterr().out == ""


# ---------------------------------------------------- DMAIC contract


def _contract_cli(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["validate_dmaic_contract", *args])
    return dc.main()


@pytest.fixture
def contract_root(tmp_path, monkeypatch):
    monkeypatch.setattr(dc, "ROOT_DIR", tmp_path)
    return tmp_path


def test_contract_uses_injected_validator():
    assert dc.validate_contract is fake_contract.validate_contract


@pytest.mark.parametrize("extra, code", [((), 1), (("--allow-empty",), 0)])
def test_contract_missing_target(contract_root, monkeypatch, caplog, extra, code):
    caplog.set_level(logging.WARNING, logger=dc.LOGGER.name)
    assert _contract_cli(monkeypatch, *extra) == code
    assert "Target does not exist" in caplog.text
    assert str(contract_root / "DMAIC_CANONICAL_OUTPUT") in caplog.text


@pytest.mark.parametrize("extra, code", [((), 1), (("--allow-empty",), 0)])
def test_contract_empty_target(contract_root, monkeypatch, caplog, extra, code):
    caplog.set_level(logging.WARNING, logger=dc.LOGGER.name)
    (contract_root / "out").mkdir()
    assert _contract_cli(monkeypatch, "--target", "out", *extra) == code
    assert "No JSON files found" in caplog.text


def test_contract_absolute_target_passes(tmp_path, monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger=dc.LOGGER.name)
    seen = []
    monkeypatch.setattr(dc, "validate_contract", lambda p: seen.append(p) or [])
    target = tmp_path / "abs"
    target.mkdir()
    (target / "a.json").write_text('{"k": 1}', encoding="utf-8")
    (target / "b.json").write_text('{"k": 2}', encoding="utf-8")
    assert _contract_cli(monkeypatch, "--target", str(target)) == 0
    assert seen == [{"k": 1}, {"k": 2}]
    assert "Contract validation passed for 2 artifact(s)" in caplog.text


def test_contract_reports_invalid_json_and_errors(contract_root, monkeypatch, caplog):
    caplog.set_level(logging.ERROR, logger=dc.LOGGER.name)
    target = contract_root / "DMAIC_CANONICAL_OUTPUT"
    target.mkdir()
    (target / "a_bad.json").write_text("{nope", encoding="utf-8")
    (target / "b_fail.json").write_text('{"phase": "x"}', encoding="utf-8")
    (target / "c_ok.json").write_text('{"phase": "ok"}', encoding="utf-8")
    monkeypatch.setattr(
        dc,
        "validate_contract",
        lambda p: [] if p["phase"] == "ok" else ["missing run_id", "bad phase"],
    )
    assert _contract_cli(monkeypatch) == 1
    text = caplog.text
    assert "Contract validation errors detected" in text
    assert "a_bad.json" in text
    assert "invalid JSON" in text
    assert "* missing run_id" in text
    assert "* bad phase" in text
    assert "c_ok.json" not in text


# ---------------------------------------------------- docs links


@pytest.fixture
def docs_root(tmp_path, monkeypatch):
    monkeypatch.setattr(dl, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(dl, "DOCS_DIR", tmp_path / "docs")
    return tmp_path


@pytest.mark.parametrize(
    "link, external",
    [
        ("http://x", True),
        ("https://x", True),
        ("mailto:a@b", True),
        ("#anchor", True),
        ("data:image/png", True),
        ("/abs", True),
        ("${base}/x", True),
        ("  https://padded", True),
        ("page.md", False),
    ],
)
def test_is_external(link, external):
    assert dl._is_external(link) is external


@pytest.mark.parametrize(
    "link, dynamic",
    [
        ("", True),
        ("   ", True),
        ("'+url+'", True),
        ('a"+b', True),
        ("x`y", True),
        ("'quoted", True),
        ('"quoted', True),
        ("page.md", False),
    ],
)
def test_is_dynamic(link, dynamic):
    assert dl._is_dynamic(link) is dynamic


def test_normalize_target(tmp_path):
    base = tmp_path / "docs" / "a.md"
    assert dl._normalize_target(base, "my%20page.md#sec") == (
        (tmp_path / "docs" / "my page.md").resolve()
    )
    absolute = tmp_path / "abs.md"
    assert dl._normalize_target(base, str(absolute)) == absolute


def test_collect_links_md_and_html(tmp_path):
    md = tmp_path / "a.md"
    md.write_text("[one](x.md) and [two](y.md#z)", encoding="utf-8")
    html = tmp_path / "b.HTML"
    html.write_text("<a href='p.html'></a><img SRC=\"i.png\">", encoding="utf-8")
    assert dl._collect_links(md) == ["x.md", "y.md#z"]
    assert dl._collect_links(html) == ["p.html", "i.png"]


def test_docs_links_missing_dir(docs_root, caplog):
    caplog.set_level(logging.WARNING, logger=dl.LOGGER.name)
    assert dl.main() == 0
    assert "docs directory not found" in caplog.text


def _docs_tree(root):
    docs = root / "docs"
    (docs / "sub").mkdir(parents=True)
    (docs / "folder.md").mkdir()  # globbed but not a file
    (docs / "sub" / "target page.md").write_text("# t\n", encoding="utf-8")
    (docs / "index.md").write_text(
        "[ext](https://e.x) [anc](#a) [ok](sub/target%20page.md#h) [dyn]('+u+')",
        encoding="utf-8",
    )
    (docs / "sub" / "page.html").write_text(
        "<a href=\"target page.md\"></a><a href='${x}'></a>", encoding="utf-8"
    )
    return docs


def test_docs_links_pass(docs_root, caplog):
    caplog.set_level(logging.INFO, logger=dl.LOGGER.name)
    _docs_tree(docs_root)
    assert dl.main() == 0
    assert "Docs link validation passed" in caplog.text


def test_docs_links_reports_broken(docs_root, caplog):
    caplog.set_level(logging.ERROR, logger=dl.LOGGER.name)
    docs = _docs_tree(docs_root)
    (docs / "broken.md").write_text("[gone](missing.md)", encoding="utf-8")
    assert dl.main() == 1
    assert "Broken docs links detected" in caplog.text
    assert "missing.md" in caplog.text
    assert str(dl.Path("docs") / "broken.md") in caplog.text


# ---------------------------------------------------- review package

EXTERNAL_ID = "tender-supplier-a-intent"
WORKFLOW_TEXT = (
    "paths:\n  - scripts/validate_review_package.py\n  - docs/**\n"
    "  - ssot/**\n  - governance/**\n"
)


def _external_artifact(**overrides):
    artifact = dict(rp.REQUIRED_EXTERNALIZED_ARTIFACTS[EXTERNAL_ID])
    artifact.update(id=EXTERNAL_ID, domain="tender_review_package")
    artifact.update(overrides)
    return artifact


def _manifest_artifacts():
    domains = sorted(rp.REQUIRED_DOMAINS - {"tender_review_package"})
    artifacts = [
        {"id": f"art-{index}", "domain": domain, "path": rp.REQUIRED_DOCS[0]}
        for index, domain in enumerate(domains)
    ]
    return artifacts + [_external_artifact()]


def _package_files():
    return {
        "ssot/ssot_items.yaml": {
            "ssot_items": [
                {
                    "id": item_id,
                    "name": "n",
                    "source": "s",
                    "owner": "o",
                    "status": "active",
                    "linked_artifacts": ["a"],
                }
                for item_id in sorted(rp.REQUIRED_SSOT_IDS)
            ]
        },
        "ssot/contractual_gap_register.yaml": {
            "contractual_gaps": [
                {
                    "id": gap_id,
                    "title": "t",
                    "related_question": "Q3",
                    "ssot_id": "SSOT-Q3",
                    "severity": "high",
                    "status": "open",
                    "owner": "o",
                    "resolution_path": "r",
                    "review_gate": "Contract Review",
                }
                for gap_id in sorted(rp.REQUIRED_GAP_IDS)
            ]
        },
        "ssot/review_artifact_manifest.yaml": {"artifacts": _manifest_artifacts()},
        "governance/review_gate_policy.yaml": {
            "review_gates": {
                f"g{index}": {"name": name}
                for index, name in enumerate(sorted(rp.REQUIRED_REVIEW_GATES))
            }
        },
        "governance/pr_review_control.yaml": {
            "pr_control": {
                "required_reviewers": 2,
                "require_ssot_traceability": True,
                "require_rtm_reference": True,
                "require_management_review": False,
            }
        },
    }


def _write_package(root, overrides=None, workflow=WORKFLOW_TEXT):
    files = _package_files()
    files.update(overrides or {})
    for rel, data in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        text = data if isinstance(data, str) else json.dumps(data)
        path.write_text(text, encoding="utf-8")
    for rel in rp.REQUIRED_DOCS:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# doc\n", encoding="utf-8")
    wf = root / ".github/workflows/review-artifact-validation.yml"
    wf.parent.mkdir(parents=True, exist_ok=True)
    wf.write_text(workflow, encoding="utf-8")


@pytest.fixture
def pkg_root(tmp_path, monkeypatch):
    monkeypatch.setattr(rp, "REPO_ROOT", tmp_path)
    return tmp_path


def test_review_package_valid(pkg_root, capsys):
    _write_package(pkg_root)
    assert rp.validate_review_package() == []
    assert rp.main() == 0
    assert "validation passed" in capsys.readouterr().out


def test_review_package_missing_files_short_circuit(pkg_root, capsys):
    errors = rp.validate_review_package()
    assert len(errors) == len(rp.REQUIRED_DOCS) + 6
    assert errors[0] == "Missing required file: docs/Q3_Q4_Q5/README.md"
    assert rp.main() == 1
    out = capsys.readouterr().out
    assert "validation failed" in out
    assert "- Missing required file: ssot/ssot_items.yaml" in out


def test_read_yaml_non_mapping_is_empty(tmp_path):
    path = tmp_path / "list.yaml"
    path.write_text("- a\n- b\n", encoding="utf-8")
    assert rp._read_yaml(path) == {}


def test_review_package_empty_registers(pkg_root):
    _write_package(
        pkg_root,
        {
            "ssot/ssot_items.yaml": "[]",
            "ssot/contractual_gap_register.yaml": "{}",
            "ssot/review_artifact_manifest.yaml": "{}",
            "governance/review_gate_policy.yaml": "{}",
            "governance/pr_review_control.yaml": "{}",
        },
        workflow="name: x\n",
    )
    errors = rp.validate_review_package()
    assert "Missing SSOT registry item: SSOT-CG" in errors
    assert "Missing contractual gap: CG-08" in errors
    assert "PR control is missing require_rtm_reference" in errors
    assert "Missing review gate: Publish Approval" in errors
    assert f"Manifest is missing externalized artifact: {EXTERNAL_ID}" in errors
    assert "Manifest is missing domain: ssot_registry" in errors
    assert "Review artifact workflow is missing docs/**" in errors
    assert len(errors) == 4 + 8 + 4 + 4 + 1 + 5 + 4


def test_review_package_incomplete_items(pkg_root):
    files = _package_files()
    ssot = files["ssot/ssot_items.yaml"]["ssot_items"]
    ssot[0] = {"id": ssot[0]["id"], "name": "n"}
    ssot.append("not-a-mapping")
    ssot.append({"id": "SSOT-EXTRA"})
    gaps = files["ssot/contractual_gap_register.yaml"]["contractual_gaps"]
    gaps[0] = {"id": "CG-01", "title": "t"}
    gaps.append(7)
    gaps.append({"id": "CG-99"})
    gates = files["governance/review_gate_policy.yaml"]["review_gates"]
    gates["bad"] = "x"
    gates["unnamed"] = {"name": ""}
    _write_package(pkg_root, files)
    errors = rp.validate_review_package()
    assert errors == [
        "SSOT-CG is missing source",
        "SSOT-CG is missing owner",
        "SSOT-CG is missing status",
        "SSOT-CG is missing linked_artifacts",
        "CG-01 is missing related_question",
        "CG-01 is missing ssot_id",
        "CG-01 is missing severity",
        "CG-01 is missing status",
        "CG-01 is missing owner",
        "CG-01 is missing resolution_path",
        "CG-01 is missing review_gate",
    ]


def test_review_package_manifest_problems(pkg_root):
    artifacts = [
        "scalar",
        {"domain": "ssot_registry", "path": "docs/missing.md"},
        {"id": "no-domain", "path": rp.REQUIRED_DOCS[1]},
        {"id": "no-path", "domain": "governance_controls"},
        {"id": "rogue", "domain": "ci_cd_scaffolding", "state": "externalized_private"},
        _external_artifact(sha256="0" * 64, external_repo=""),
    ]
    _write_package(
        pkg_root, {"ssot/review_artifact_manifest.yaml": {"artifacts": artifacts}}
    )
    errors = rp.validate_review_package()
    assert errors == [
        "Manifest artifact entries must be mappings",
        "artifact is missing id",
        "no-domain is missing domain",
        "no-path is missing path",
        "rogue is missing external_repo",
        "rogue is missing original_path",
        "rogue is missing provenance_path",
        "rogue is missing sha256",
        "rogue is not an approved externalized artifact",
        f"{EXTERNAL_ID} is missing external_repo",
        f"{EXTERNAL_ID} has unexpected external_repo",
        f"{EXTERNAL_ID} has unexpected sha256",
        "Manifest is missing domain: contractual_gap_register",
        "Missing required file: docs/missing.md",
    ]
