"""Behaviour tests for scripts/t0_deep_diagnostics.py.

The module runs its probes at import time against the current directory, so
each test loads it afresh inside ``tmp_path`` with subprocess and shutil.which
patched; nothing is executed for real.
"""

import hashlib
import json
import types

from tests.coverage_waves.lane_b._l2_loader import load

REL = "scripts/t0_deep_diagnostics.py"


def _fake_run(returncodes, raises=()):
    calls = []

    def fake(cmd, **kwargs):
        calls.append((cmd, kwargs))
        for needle in raises:
            if needle in cmd:
                raise OSError("no such tool")
        for needle, code in returncodes.items():
            if needle in cmd:
                return types.SimpleNamespace(returncode=code)
        return types.SimpleNamespace(returncode=0)

    return fake, calls


def _load(monkeypatch, tmp_path, which=None, returncodes=None, raises=()):
    monkeypatch.chdir(tmp_path)
    fake, calls = _fake_run(returncodes or {}, raises)
    monkeypatch.setattr("subprocess.run", fake)
    monkeypatch.setattr("shutil.which", lambda name: which)
    mod = load(REL, name="abn_t0_deep_diagnostics")
    return mod, calls


def _report(capsys):
    lines = capsys.readouterr().out.strip().splitlines()
    return json.loads(lines[-1])


def test_empty_directory_skips_every_external_probe(monkeypatch, tmp_path, capsys):
    _, calls = _load(monkeypatch, tmp_path)

    report = _report(capsys)
    assert calls == []
    assert report["schema"] == "ops-kpi-v1"
    assert report["phase"] == "T0"
    assert report["authority"] == "operational_non_evidence"
    probes = {p["name"]: p for p in report["probes"]}
    assert list(probes) == [
        "artifact_hash_scan",
        "yaml_parse",
        "playwright_list",
        "dow_contract_dry_run",
    ]
    scan = probes["artifact_hash_scan"]
    assert scan["status"] == "ok"
    assert scan["detail"]["files"] == 0
    assert scan["detail"]["bytes"] == 0
    assert scan["detail"]["sha256"] == hashlib.sha256().hexdigest()
    assert probes["yaml_parse"] == {
        "name": "yaml_parse",
        "status": "skipped",
        "duration_ms": 0,
        "detail": "no yaml",
    }
    assert probes["playwright_list"]["status"] == "skipped"
    assert probes["dow_contract_dry_run"]["detail"] == "validator unavailable"


def test_playwright_config_without_npx_is_skipped(monkeypatch, tmp_path, capsys):
    (tmp_path / "playwright.config.js").write_bytes(b"module.exports = {};\n")

    _, calls = _load(monkeypatch, tmp_path, which=None)

    probes = {p["name"]: p for p in _report(capsys)["probes"]}
    assert probes["playwright_list"]["status"] == "skipped"
    assert calls == []


def test_all_probes_run_and_failures_are_classified(monkeypatch, tmp_path, capsys):
    (tmp_path / "ci.yml").write_bytes(b"a: 1\n")
    (tmp_path / "playwright.config.ts").write_bytes(b"export default {};\n")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "validate_qps_w04_dow_receipt.py").write_bytes(b"print(1)\n")

    _, calls = _load(
        monkeypatch,
        tmp_path,
        which="npx-path",
        returncodes={"validate_qps_w04": 2},
        raises=("playwright",),
    )

    probes = {p["name"]: p for p in _report(capsys)["probes"]}
    assert probes["yaml_parse"]["status"] == "ok"
    assert probes["yaml_parse"]["detail"] is None
    assert probes["playwright_list"]["status"] == "failed"
    assert probes["playwright_list"]["detail"] == {"error": "OSError"}
    assert probes["dow_contract_dry_run"]["status"] == "failed"
    assert probes["dow_contract_dry_run"]["detail"] == {"returncode": 2}
    assert probes["artifact_hash_scan"]["detail"]["files"] == 3
    assert len(calls) == 3
    for _, kwargs in calls:
        assert kwargs["shell"] is True
        assert kwargs["timeout"] == 180
    assert calls[1][0] == "npx playwright test --list"


def test_hash_pack_digests_file_bytes_in_glob_order(monkeypatch, tmp_path, capsys):
    mod, _ = _load(monkeypatch, tmp_path)
    capsys.readouterr()
    (tmp_path / "a.bin").write_bytes(b"alpha")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.bin").write_bytes(b"beta!")

    result = mod.hash_pack()

    assert result["files"] == 2
    assert result["bytes"] == 10
    expected = hashlib.sha256()
    for name in mod.glob.glob("**/*", recursive=True):
        if (tmp_path / name).is_file():
            expected.update((tmp_path / name).read_bytes())
    assert result["sha256"] == expected.hexdigest()


def test_hash_pack_ignores_unreadable_files(monkeypatch, tmp_path, capsys):
    mod, _ = _load(monkeypatch, tmp_path)
    (tmp_path / "locked.bin").write_bytes(b"locked")

    def deny(path, mode="r"):
        raise OSError("denied")

    monkeypatch.setattr(mod, "open", deny, raising=False)

    result = mod.hash_pack()

    assert result["files"] == 1
    assert result["bytes"] == 0
    assert result["sha256"] == hashlib.sha256().hexdigest()


def test_probe_function_success_failure_and_noop(monkeypatch, tmp_path, capsys):
    mod, _ = _load(monkeypatch, tmp_path)

    ok = mod.probe("f", fn=lambda: {"x": 1})
    assert ok["status"] == "ok"
    assert ok["detail"] == {"x": 1}
    assert ok["duration_ms"] >= 0

    def broken():
        raise ValueError("bad")

    bad = mod.probe("g", fn=broken)
    assert bad["status"] == "failed"
    assert bad["detail"] == {"error": "ValueError"}

    noop = mod.probe("h")
    assert noop["status"] == "ok"
    assert noop["detail"] is None

    assert mod.skip("s", "why") == {
        "name": "s",
        "status": "skipped",
        "duration_ms": 0,
        "detail": "why",
    }
