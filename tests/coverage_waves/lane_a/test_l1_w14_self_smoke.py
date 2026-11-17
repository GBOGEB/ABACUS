"""Lane A wave 14: DMAIC_V3.self_smoke probes and receipt with ROOT redirected."""

import hashlib

import pytest

from DMAIC_V3 import self_smoke as ss

GOOD_SSOT = (
    "one_logical_fact_one_authority: true\n"
    "reverse_mutation_from_binary_to_authority: false\n"
)


def _fake_git(*args):
    return "tree" if args[-1].endswith("{tree}") else "commit"


def _layout(root, ssot=GOOD_SSOT, contract=True):
    if ssot is not None:
        (root / "ssot").mkdir()
        (root / "ssot" / "manifest.yaml").write_bytes(ssot.encode("utf-8"))
    if contract:
        a = root / "qps_contract_canonicalization" / "src"
        b = root / "qps_slide_reviewer" / "lib"
        a.mkdir(parents=True)
        b.mkdir(parents=True)
        (a / "schema.ts").write_bytes(b"x")
        (b / "qps-contract-clarification-schema.ts").write_bytes(b"y")


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "ROOT", tmp_path)
    monkeypatch.setattr(ss, "_git", _fake_git)
    return tmp_path


def test_sha256_matches_hashlib(tmp_path):
    p = tmp_path / "f.bin"
    data = b"abc" * 1000
    p.write_bytes(data)
    assert ss._sha256(p) == hashlib.sha256(data).hexdigest()


def test_git_uses_check_output(monkeypatch):
    seen = {}

    def fake(cmd, cwd, text):
        seen["cmd"] = cmd
        seen["cwd"] = cwd
        return "  abc123\n"

    monkeypatch.setattr("subprocess.check_output", fake)
    assert ss._git("rev-parse", "HEAD") == "abc123"
    assert seen["cmd"] == ["git", "rev-parse", "HEAD"]
    assert seen["cwd"] == ss.ROOT


def test_all_probes_pass(root):
    _layout(root)
    ss.run_self_smoke()  # warm-up: first imports may print captured noise
    out = ss.run_self_smoke()
    assert out["success"] is True
    assert out["passed"] == out["total"] == 7
    assert out["commit_sha"] == "commit" and out["tree_sha"] == "tree"
    stages = {s["name"]: s for s in out["stages"]}
    expected = hashlib.sha256(GOOD_SSOT.encode("utf-8")).hexdigest()
    assert stages["ssot_authority"]["detail"] == {"sha256": expected}
    assert len(stages["schema_surfaces"]["detail"]["surfaces"]) == 2
    assert stages["configuration"]["detail"] == {"config_type": "DMAICConfig"}
    assert stages["import_and_version"]["detail"]["product_version"]
    assert len(out["deterministic_sha256"]) == 64
    assert ss.run_self_smoke()["deterministic_sha256"] == out["deterministic_sha256"]


def test_missing_surfaces_fail(root):
    out = ss.run_self_smoke()
    stages = {s["name"]: s for s in out["stages"]}
    assert out["success"] is False
    assert stages["ssot_authority"]["status"] == "FAIL"
    assert stages["ssot_authority"]["error"].startswith("FileNotFoundError")
    assert stages["schema_surfaces"]["status"] == "FAIL"
    assert "schema surfaces missing" in stages["schema_surfaces"]["error"]
    assert out["passed"] == 5


def test_ssot_missing_invariant(root):
    _layout(root, ssot="one_logical_fact_one_authority: true\n", contract=False)
    with pytest.raises(RuntimeError, match="invariants missing"):
        ss._probe_ssot()


def test_captured_stdout_recorded(root, monkeypatch):
    _layout(root)

    def noisy():
        print("hello from probe")
        return {"engine_version": "x", "product_version": "y"}

    monkeypatch.setattr(ss, "_probe_import", noisy)
    out = ss.run_self_smoke()
    first = out["stages"][0]
    assert first["status"] == "PASS"
    assert first["captured_stdout"] == "hello from probe"
