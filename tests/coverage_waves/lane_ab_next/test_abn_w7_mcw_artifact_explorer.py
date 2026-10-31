"""Gap tests for tools/mcw_artifact_explorer.py (git head, unmounted input, CLI)."""

import json
import sys
from types import SimpleNamespace

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("tools/mcw_artifact_explorer.py", name="abn_w7_mcw_artifact_explorer")

SHA = "c" * 40
STYLE = {
    "version": "0.2",
    "palette": {
        "tokens": {
            "define": "#562873",
            "measure": "#984A9C",
            "analyze": "#034694",
            "improve": "#B5622A",
            "control": "#1D7A5F",
            "critical": "#B42318",
        }
    },
}


def _catalog():
    return {
        "schema": mod.SCHEMA,
        "triggers": [{"event": "PR", "stage": "TYPE_QA", "action": "Cold checks"}],
        "artifacts": [
            {
                "id": "ssot-json",
                "title": "SSOT source",
                "format": "json",
                "role": "repository_source",
                "path": "ssot.json",
            },
            {
                "id": "frozen-docx",
                "title": "Frozen input",
                "format": "docx",
                "role": "controlled_input",
                "path": "inputs/frozen.docx",
            },
        ],
    }


def test_git_head_runs_rev_parse(monkeypatch, tmp_path):
    calls = []

    def fake_run(cmd, capture_output, text, check):
        calls.append(cmd)
        return SimpleNamespace(stdout=SHA + "\n")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    assert mod.git_head(tmp_path) == SHA
    assert calls == [["git", "-C", str(tmp_path), "rev-parse", "HEAD"]]


def test_classify_controlled_input_not_mounted(tmp_path):
    node = dict(format="docx", role="controlled_input", path="inputs/missing.docx")
    result = mod.classify(tmp_path.resolve(), node)
    assert result == {
        "state": "CONTROLLED_INPUT_NOT_MOUNTED",
        "sha256": None,
        "bytes": None,
        "source_path": "inputs/missing.docx",
    }


def _cli(tmp_path, *extra):
    root = tmp_path / "root"
    root.mkdir()
    (root / "ssot.json").write_bytes(b'{"source": true}')
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps(_catalog()))
    style = tmp_path / "style.json"
    style.write_text(json.dumps(STYLE))
    html_out = tmp_path / "site" / "index.html"
    receipt = tmp_path / "receipts" / "r.json"
    argv = [
        "mcw",
        "--root",
        str(root),
        "--catalog",
        str(catalog),
        "--style",
        str(style),
        "--html",
        str(html_out),
        "--receipt",
        str(receipt),
        *extra,
    ]
    return argv, html_out, receipt


def test_main_uses_git_head_and_style_status(monkeypatch, tmp_path, capsys):
    status = tmp_path / "status.json"
    status.write_text(
        json.dumps(
            {
                "valid": True,
                "awake": {
                    "awake_score": 0.5,
                    "probes": [
                        {"id": "b-probe", "awake": False},
                        {"id": "a-probe", "awake": False},
                        {"id": "ok-probe", "awake": True},
                    ],
                },
            }
        )
    )
    argv, html_out, receipt = _cli(tmp_path, "--style-status", str(status))
    monkeypatch.setattr(mod, "git_head", lambda root: SHA)
    monkeypatch.setattr(sys, "argv", argv)
    assert mod.main() is None
    report = json.loads(receipt.read_text())
    assert report["source_sha"] == SHA
    assert report["missing_style_probes"] == ["a-probe", "b-probe"]
    assert report["style_awake_score"] == 0.5
    states = report["states"]
    assert states["CONTROLLED_INPUT_NOT_MOUNTED"] == 1
    page = html_out.read_text(encoding="utf-8")
    assert report["html_sha256"] == mod.digest(page.encode())
    assert "SSOT source" in page
    printed = json.loads(capsys.readouterr().out)
    assert printed == {
        "artifacts": 2,
        "html_sha256": report["html_sha256"],
        "merge_admission": "HOLD",
    }


def test_main_with_explicit_sha_skips_git(monkeypatch, tmp_path):
    argv, html_out, receipt = _cli(tmp_path, "--sha", SHA)

    def no_git(root):
        raise AssertionError("git must not run when --sha is given")

    monkeypatch.setattr(mod, "git_head", no_git)
    monkeypatch.setattr(sys, "argv", argv)
    mod.main()
    report = json.loads(receipt.read_text())
    assert "missing_style_probes" not in report
    assert report["catalog_file_sha256"] == mod.digest(
        (tmp_path / "catalog.json").read_bytes()
    )


def test_main_rejects_invalid_style_status(monkeypatch, tmp_path):
    status = tmp_path / "status.json"
    status.write_text(json.dumps({"valid": False}))
    argv, html_out, receipt = _cli(
        tmp_path, "--sha", SHA, "--style-status", str(status)
    )
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(ValueError, match="invalid style contract receipt"):
        mod.main()
    assert not html_out.exists()
