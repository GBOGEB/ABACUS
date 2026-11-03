"""Gap tests for scripts/ci/ariana_dow_evidence.py.

Loaded by path (a site-packages ``scripts`` package can shadow the repo's
namespace package locally). Covers the fail-closed validation branches of the
local DOW/KEB contract, the JUnit suites structure guard and the CLI ``main``.
"""

import json
import sys

import pytest
import yaml

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("scripts/ci/ariana_dow_evidence.py", name="abn_w7_ariana_dow_evidence")

GOOD_SHA = "c" * 40


def _dock():
    return {
        "repo": "GBOGEB/ABACUS",
        "authority": {"must_not": ["promote_QPS_engineering_truth"]},
    }


def _receiver():
    return {
        "consumer": "GBOGEB/ABACUS",
        "producer": {"repo": "GBOGEB/CODEX"},
        "namespace_invariant": {
            "status_keys": ["ACCEPT"],
            "action_monikers": ["run"],
            "intersection_must_be_empty": True,
        },
        "3pc_consumption": {
            "authority": {"must_not": ["promote_QPS_engineering_truth"]}
        },
    }


def _write_contract(root, dock, receiver):
    for rel in (mod.SOURCE_PATH, mod.BRIDGE_PATH, *mod.TEST_PATHS):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"# stub\n")
    for rel, data in ((mod.DOCK_PATH, dock), (mod.RECEIVER_PATH, receiver)):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(data), encoding="utf-8")


def test_exact_checkout_rejects_non_hex_sha(tmp_path):
    with pytest.raises(ValueError, match="40-character"):
        mod.exact_checkout(tmp_path, "ABC")


def test_validate_local_contract_happy_path(tmp_path):
    _write_contract(tmp_path, _dock(), _receiver())
    result = mod.validate_local_contract(tmp_path)
    assert result["runtime_owner"] == "GBOGEB/ABACUS"
    assert result["semantic_owner"] == "GBOGEB/CODEX"
    assert result["namespace_status_key_count"] == 1
    assert len(result["local_sources_sha256"]) == 4


def _mutate(path, value):
    def apply(dock, receiver):
        target = dock if path[0] == "dock" else receiver
        keys = path[1:]
        if not keys:
            return value if path[0] == "dock" else dock, (
                value if path[0] == "receiver" else receiver
            )
        node = target
        for key in keys[:-1]:
            node = node[key]
        node[keys[-1]] = value
        return dock, receiver

    return apply


@pytest.mark.parametrize(
    "path,value,message",
    [
        (("dock",), ["not", "a", "dict"], "invalid DOW/KEB YAML"),
        (("dock", "repo"), "other/repo", "ABACUS runtime ownership"),
        (("receiver", "consumer"), "other/repo", "DOW receiver ownership"),
        (("receiver", "producer", "repo"), "other/repo", "KEB producer"),
        (("dock", "authority", "must_not"), [], "QPS engineering authority"),
    ],
)
def test_validate_local_contract_fail_closed(tmp_path, path, value, message):
    dock, receiver = _mutate(path, value)(_dock(), _receiver())
    _write_contract(tmp_path, dock, receiver)
    with pytest.raises(ValueError, match=message):
        mod.validate_local_contract(tmp_path)


def test_read_junit_rejects_non_testsuite_children(tmp_path):
    path = tmp_path / "junit.xml"
    path.write_bytes(b"<testsuites><bogus/></testsuites>")
    with pytest.raises(ValueError, match="suites structure"):
        mod.read_junit(path)
    empty = tmp_path / "empty.xml"
    empty.write_bytes(b"<testsuites></testsuites>")
    with pytest.raises(ValueError, match="suites structure"):
        mod.read_junit(empty)


def _run_main(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", ["ariana_dow_evidence.py"] + argv)
    return mod.main()


def test_main_preflight_prints_contract(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(mod, "exact_checkout", lambda root, sha: sha)
    monkeypatch.setattr(mod, "validate_local_contract", lambda root: {"ok": 1})
    rc = _run_main(
        monkeypatch,
        ["--repo-root", str(tmp_path), "--source-sha", GOOD_SHA, "--preflight"],
    )
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out == {"contract": {"ok": 1}, "preflight": "PASS", "source_sha": GOOD_SHA}


def test_main_receipt_requires_all_paths(monkeypatch, tmp_path, capsys):
    with pytest.raises(SystemExit) as info:
        _run_main(monkeypatch, ["--repo-root", str(tmp_path), "--source-sha", "x"])
    assert info.value.code == 2
    assert "--junit, --coverage, and --out" in capsys.readouterr().err


def _receipt_args(tmp_path, *extra):
    return [
        "--repo-root",
        str(tmp_path),
        "--source-sha",
        GOOD_SHA,
        "--junit",
        str(tmp_path / "j.xml"),
        "--coverage",
        str(tmp_path / "c.json"),
        "--out",
        str(tmp_path / "out" / "receipt.json"),
        *extra,
    ]


@pytest.mark.parametrize(
    "disposition,strict,expected",
    [
        ("LOCAL_TESTED_FEDERATION_HOLD", True, 0),
        ("EVIDENCE_WITHHELD", True, 1),
        ("EVIDENCE_WITHHELD", False, 0),
    ],
)
def test_main_receipt_writes_and_applies_strict(
    monkeypatch, tmp_path, capsys, disposition, strict, expected
):
    seen = []

    def fake_build(root, sha, junit, coverage):
        seen.append((sha, junit.name, coverage.name))
        return {"disposition": disposition}

    monkeypatch.setattr(mod, "build_receipt", fake_build)
    extra = ["--strict"] if strict else []
    rc = _run_main(monkeypatch, _receipt_args(tmp_path, *extra))
    assert rc == expected
    assert seen == [(GOOD_SHA, "j.xml", "c.json")]
    out_file = tmp_path / "out" / "receipt.json"
    assert json.loads(out_file.read_text(encoding="utf-8")) == {
        "disposition": disposition
    }
    assert "ARIANA_DOW_RECEIPT=" + disposition in capsys.readouterr().out


def test_main_fail_closed_on_value_error(monkeypatch, tmp_path, capsys):
    def boom(root, sha, junit, coverage):
        raise ValueError("stale checkout")

    monkeypatch.setattr(mod, "build_receipt", boom)
    rc = _run_main(monkeypatch, _receipt_args(tmp_path))
    assert rc == 2
    assert "ARIANA_DOW_FAIL_CLOSED: stale checkout" in capsys.readouterr().err
