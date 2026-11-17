"""Gap tests for tools/ci/dependency_spine_peer_scan.py: git, build, verify, main."""

import json
import types

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

dsp = load("tools/ci/dependency_spine_peer_scan.py", name="abn_w7_dep_spine_peer")

SHA = "b" * 40
REPO = "GBOGEB/ABACUS"


def _fake_run(stdout, returncode=0):
    def run(cmd, cwd, capture_output, text, check):
        return types.SimpleNamespace(stdout=stdout, returncode=returncode)

    return run


def test_git_head_valid_invalid_and_failed(monkeypatch, tmp_path):
    monkeypatch.setattr(dsp.subprocess, "run", _fake_run(SHA.upper() + "\n"))
    assert dsp.git_head(tmp_path) == SHA
    monkeypatch.setattr(dsp.subprocess, "run", _fake_run("short\n"))
    assert dsp.git_head(tmp_path) == ""
    monkeypatch.setattr(dsp.subprocess, "run", _fake_run(SHA, returncode=128))
    assert dsp.git_head(tmp_path) == ""


def test_parse_config_skips_comments():
    text = "# - package-ecosystem: npm\n- package-ecosystem: pip\n  directory: /\n"
    assert dsp.parse_config(text) == [{"ecosystem": "pip", "directory": "/"}]


def _repo(tmp_path):
    root = tmp_path / "repo"
    wf = root / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_text(
        "steps:\n  - uses: actions/checkout@abc\n  - uses: ./local\n",
        encoding="utf-8",
    )
    (root / ".github" / "dependabot.yml").write_text(
        "- package-ecosystem: github-actions\n  directory: /\n", encoding="utf-8"
    )
    return root


def _built(monkeypatch, tmp_path):
    root = _repo(tmp_path)
    monkeypatch.setattr(dsp, "git_head", lambda r: SHA)
    out = tmp_path / "out"
    obs = dsp.build(out, root, REPO, SHA)
    return out, obs


def test_build_then_verify_roundtrip(monkeypatch, tmp_path):
    out, obs = _built(monkeypatch, tmp_path)
    assert obs["workflow_count"] == 1
    assert obs["action_reference_count"] == 2
    manifest = json.loads((out / "PEER_SHA256.json").read_text(encoding="utf-8"))
    data = (out / "PEER_CENSUS.json").read_bytes()
    assert manifest["files"] == {"PEER_CENSUS.json": dsp.digest(data)}
    assert manifest["qualified_status"] == "LEXICAL_CENSUS_ONLY"
    dsp.verify(out, REPO, SHA)


def _rewrite(out, census_edit=None, manifest_edit=None):
    census = json.loads((out / "PEER_CENSUS.json").read_text(encoding="utf-8"))
    if census_edit:
        census_edit(census)
    data = dsp.canonical(census)
    (out / "PEER_CENSUS.json").write_bytes(data)
    manifest = json.loads((out / "PEER_SHA256.json").read_text(encoding="utf-8"))
    manifest["files"] = {"PEER_CENSUS.json": dsp.digest(data)}
    if manifest_edit:
        manifest_edit(manifest)
    (out / "PEER_SHA256.json").write_bytes(dsp.canonical(manifest))


@pytest.mark.parametrize(
    "census_edit, manifest_edit, message",
    [
        (None, lambda m: m.update(schema="other"), "MANIFEST_SCHEMA_MISMATCH"),
        (
            None,
            lambda m: m.update(files={"PEER_CENSUS.json": "0"}),
            "DIGEST_MISMATCH",
        ),
        (lambda c: c.update(head_sha="c" * 40), None, "HEAD_IDENTITY_MISMATCH"),
        (lambda c: c.update(repo="GBOGEB/CODEX"), None, "REPO_IDENTITY_MISMATCH"),
        (
            lambda c: c["governance"].update(merge_admission="GO"),
            None,
            "GOVERNANCE_PROMOTION_FORBIDDEN",
        ),
        (
            lambda c: c.update(runtime_proof="UPGRADED"),
            None,
            "RUNTIME_PROMOTION_FORBIDDEN",
        ),
        (
            None,
            lambda m: m.update(qualified_status="ADMITTED"),
            "QUALIFICATION_PROMOTION_FORBIDDEN",
        ),
    ],
)
def test_verify_rejects_tampering(
    monkeypatch, tmp_path, census_edit, manifest_edit, message
):
    out, _ = _built(monkeypatch, tmp_path)
    _rewrite(out, census_edit, manifest_edit)
    with pytest.raises(ValueError, match=message):
        dsp.verify(out, REPO, SHA)


def test_main_prints_pass_summary(monkeypatch, tmp_path, capsys):
    root = _repo(tmp_path)
    monkeypatch.setattr(dsp, "git_head", lambda r: SHA)
    out = tmp_path / "cli_out"
    argv = ["prog", "--repo", REPO, "--expected-sha", SHA]
    argv += ["--root", str(root), "--out", str(out)]
    monkeypatch.setattr("sys.argv", argv)
    assert dsp.main() == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "PASS_READONLY_LEXICAL"
    assert summary["workflow_count"] == 1
    assert summary["action_reference_count"] == 2
    assert summary["dependabot_present"] is True
