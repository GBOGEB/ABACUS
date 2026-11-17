"""Lane-B wave 12: qplant SBOM generator/validator/scanner and cross-link validator.

Every pip / pip-audit call is faked on the loaded module; nothing touches the
network or the host interpreter's package list.
"""

import json
import pathlib
import sys
import types

import pytest

from ._l2_loader import load

gen = load("qplant/sbom/generate_sbom.py")
val = load("qplant/sbom/sbom_validation.py")
vs = load("qplant/sbom/vulnerability_scan.py")
xl = load("qplant/validate_cross_links.py")


class _Utf8Path(type(pathlib.Path())):
    """Path whose write_text is UTF-8, so emoji reports work on any locale."""

    def write_text(self, data, encoding=None, errors=None, newline=None):
        return super().write_text(
            data, encoding="utf-8", errors=errors, newline=newline
        )


def _proc(stdout="", returncode=0):
    return types.SimpleNamespace(stdout=stdout, returncode=returncode)


AUDIT_JSON = json.dumps(
    {
        "dependencies": [
            {
                "name": "requests",
                "version": "2.0",
                "vulns": [
                    {
                        "id": "PYSEC-1",
                        "description": "bad",
                        "fix_versions": ["2.1", "2.2"],
                        "aliases": ["CVE-1"],
                    }
                ],
            },
            {"name": "safe", "version": "1.0", "vulns": []},
        ]
    }
)


# --------------------------------------------------------------------------
# generate_sbom
# --------------------------------------------------------------------------


def test_get_python_packages_with_licenses(monkeypatch):
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd[3:])
        if cmd[3] == "list":
            return _proc(
                json.dumps(
                    [
                        {"name": "alpha", "version": "1"},
                        {"name": "beta", "version": "2"},
                        {"name": "gamma", "version": "3"},
                    ]
                )
            )
        name = cmd[-1]
        if name == "alpha":
            return _proc("Name: alpha\nLicense: MIT\nLicense: ignored\n")
        if name == "beta":
            raise OSError("pip show failed")
        return _proc("Name: gamma\n")

    monkeypatch.setattr(gen.subprocess, "run", fake_run)
    pkgs = gen.get_python_packages()
    assert [(p["name"], p["license"]) for p in pkgs] == [
        ("alpha", "MIT"),
        ("beta", "Unknown"),
        ("gamma", "Unknown"),
    ]
    assert pkgs[0]["purl"] == "pkg:pypi/alpha@1"
    assert calls[0] == ["list", "--format=json"]


def test_get_python_packages_pip_failure(monkeypatch):
    def boom(cmd, **kw):
        raise OSError("no pip")

    monkeypatch.setattr(gen.subprocess, "run", boom)
    assert gen.get_python_packages() == []


def test_get_requirements_packages(tmp_path):
    assert gen.get_requirements_packages(str(tmp_path / "missing.txt")) == []
    req = tmp_path / "requirements.txt"
    req.write_text(
        "# comment\n\n-r other.txt\nnumpy==1.26.0\npandas >= 2.0\nrequests\n",
        encoding="utf-8",
    )
    pkgs = gen.get_requirements_packages(str(req))
    assert [(p["name"], p["version"]) for p in pkgs] == [
        ("numpy", "1.26.0"),
        ("pandas", ">= 2.0"),
        ("requests", "*"),
    ]
    assert pkgs[0]["scope"] == "required"
    assert pkgs[2]["purl"] == "pkg:pypi/requests@*"


def test_scan_vulnerabilities_parses_audit(monkeypatch):
    monkeypatch.setattr(gen.subprocess, "run", lambda cmd, **kw: _proc(AUDIT_JSON))
    vulns = gen.scan_vulnerabilities([])
    assert vulns == [
        {
            "package": "requests",
            "version": "2.0",
            "id": "PYSEC-1",
            "description": "bad",
            "fix_versions": ["2.1", "2.2"],
            "severity": "medium",
        }
    ]


def test_scan_vulnerabilities_nonzero_exit(monkeypatch):
    monkeypatch.setattr(
        gen.subprocess, "run", lambda cmd, **kw: _proc(AUDIT_JSON, returncode=1)
    )
    assert gen.scan_vulnerabilities([]) == []


@pytest.mark.parametrize("kind", ["missing", "timeout", "badjson"])
def test_scan_vulnerabilities_tolerates_errors(monkeypatch, kind):
    def fake_run(cmd, **kw):
        if kind == "missing":
            raise FileNotFoundError("pip_audit")
        if kind == "timeout":
            raise gen.subprocess.TimeoutExpired(cmd, 120)
        return _proc("{not json")

    monkeypatch.setattr(gen.subprocess, "run", fake_run)
    assert gen.scan_vulnerabilities([]) == []


def _fake_sources(monkeypatch, vulns):
    installed = [
        {"type": "library", "name": "NumPy", "version": "1", "license": "BSD"},
        {"type": "library", "name": "six", "version": "1.16", "license": "UNKNOWN"},
        {"type": "library", "name": "idna", "version": "3", "license": ""},
        {"type": "library", "name": "certifi", "version": "1", "license": "MPL-2.0"},
    ]
    monkeypatch.setattr(
        gen, "get_python_packages", lambda: [dict(p) for p in installed]
    )
    monkeypatch.setattr(gen, "scan_vulnerabilities", lambda pkgs: list(vulns))


def test_generate_cyclonedx_sbom(monkeypatch, tmp_path, capsys):
    req = tmp_path / "requirements.txt"
    req.write_text("numpy==1.26.0\n", encoding="utf-8")
    vuln = {
        "package": "six",
        "version": "1.16",
        "id": "PYSEC-9",
        "description": "d",
        "fix_versions": ["1.17"],
        "severity": "medium",
    }
    _fake_sources(monkeypatch, [vuln])
    sbom = gen.generate_cyclonedx_sbom("Proj", "9.9", str(req))
    assert sbom["bomFormat"] == "CycloneDX"
    assert sbom["serialNumber"].startswith("urn:uuid:qplant-9.9-")
    assert sbom["metadata"]["component"]["name"] == "Proj"
    names = [(c["name"], c["scope"]) for c in sbom["components"]]
    assert names == [
        ("numpy", "required"),
        ("six", "transitive"),
        ("idna", "transitive"),
        ("certifi", "transitive"),
    ]
    assert sbom["_summary"] == {
        "total": 4,
        "direct": 1,
        "transitive": 3,
        "vulnerabilities": 1,
        "licenses": {"Unknown": 3, "MPL-2.0": 1},
    }
    v = sbom["vulnerabilities"][0]
    assert v["affects"] == [{"ref": "pkg:pypi/six@1.16"}]
    assert v["recommendation"] == "Upgrade to 1.17"
    assert "Direct: 1, Transitive: 3" in capsys.readouterr().out


def _report_sbom(n_direct, vulns):
    comps = [
        {"name": "p" + str(i), "version": "1", "scope": "required"}
        for i in range(n_direct)
    ]
    comps.append({"name": "t", "version": "1", "scope": "transitive"})
    return {
        "_summary": {
            "total": n_direct + 1,
            "direct": n_direct,
            "transitive": 1,
            "vulnerabilities": len(vulns),
            "licenses": {"MIT": 5, "GPL-3.0": 2},
        },
        "metadata": {"component": {"name": "QP", "version": "1.2.3"}},
        "components": comps,
        "vulnerabilities": vulns,
    }


def test_generate_sbom_report_many_direct(monkeypatch, tmp_path):
    monkeypatch.setattr(gen, "Path", _Utf8Path)
    out = tmp_path / "report.md"
    gen.generate_sbom_report(_report_sbom(32, [{"id": "x"}]), str(out))
    text = out.read_text(encoding="utf-8")
    assert "**Project:** QP" in text
    assert "| MIT | 5 | ✅ Low |" in text
    assert "| GPL-3.0 | 2 | ⚠️ Review |" in text
    assert text.index("| MIT |") < text.index("| GPL-3.0 |")
    assert "- p29==1" in text
    assert "- p30==1" not in text
    assert "- ... and 2 more" in text
    assert "See vulnerabilities section" in text
    assert "- **Medium:** 1" in text


def test_generate_sbom_report_minimal(monkeypatch, tmp_path):
    monkeypatch.setattr(gen, "Path", _Utf8Path)
    out = tmp_path / "r.md"
    gen.generate_sbom_report({}, str(out))
    text = out.read_text(encoding="utf-8")
    assert "**Project:** MYRRHA QPLANT" in text
    assert "No known vulnerabilities detected." in text
    assert "and" not in text.split("## Direct Dependencies")[1].split("##")[0]


def test_generate_sbom_main(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(gen, "Path", _Utf8Path)
    _fake_sources(monkeypatch, [])
    req = tmp_path / "requirements.txt"
    req.write_text("numpy==1.26.0\nflask\n", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "generate_sbom",
            "--output",
            "out.json",
            "--report",
            "out.md",
            "--requirements",
            str(req),
        ],
    )
    gen.main()
    sbom = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert sbom["_summary"]["total"] == 5
    rel = tmp_path / "releases" / "v4.4.0"
    assert json.loads((rel / "cyclonedx_sbom.json").read_text(encoding="utf-8")) == sbom
    assert (rel / "sbom_report.md").read_text(encoding="utf-8").startswith("# Software")
    out = capsys.readouterr().out
    assert "Components: 5" in out
    assert "Vulnerabilities: 0" in out


# --------------------------------------------------------------------------
# sbom_validation
# --------------------------------------------------------------------------


def _component(name="pkg", **over):
    comp = {
        "name": name,
        "version": "1.0",
        "purl": "pkg:pypi/" + name + "@1.0",
        "licenses": [{"license": {"name": "MIT"}}],
    }
    comp.update(over)
    return comp


def _sbom(**over):
    doc = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "metadata": {"timestamp": "2026-01-01", "component": {"version": "4.4.0"}},
        "components": [_component("a"), _component("b")],
    }
    doc.update(over)
    return doc


def _write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def test_validate_sbom_clean(tmp_path):
    result = val.validate_sbom(_write_json(tmp_path / "s.json", _sbom()))
    assert result["valid"] is True
    assert result["score"] == 100.0
    assert result["total_components"] == 2
    assert result["issues"] == []
    assert result["warnings"] == []
    assert all(result["compliance"].values())


def test_validate_sbom_missing_file(tmp_path):
    result = val.validate_sbom(str(tmp_path / "none.json"))
    assert result["valid"] is False
    assert result["error"].startswith("SBOM not found:")


def test_validate_sbom_structure_issues(tmp_path):
    result = val.validate_sbom(_write_json(tmp_path / "s.json", {"bomFormat": "SPDX"}))
    assert result["valid"] is False
    assert result["issues"] == [
        "Missing or incorrect bomFormat (expected CycloneDX)",
        "Missing specVersion",
        "Missing metadata section",
        "Missing components section",
    ]
    assert result["warnings"] == [
        "Missing generation timestamp",
        "Missing project version in metadata",
    ]
    assert result["score"] == 40.0


def test_validate_sbom_component_warnings(tmp_path):
    comps = [
        _component("noversion", version=""),
        _component("nopurl", purl=""),
        _component("nolic", licenses=[]),
        _component(
            "gpl",
            licenses=[{"license": {"name": "GPL-3.0"}}, {"license": {}}, {}],
        ),
    ]
    doc = _sbom(components=comps, metadata={})
    result = val.validate_sbom(_write_json(tmp_path / "s.json", doc))
    assert result["valid"] is True
    assert result["warnings"] == [
        "1 components missing version",
        "1 components missing license info",
        "1 components missing PURL identifier",
        "Copyleft licenses found: gpl: GPL-3.0",
        "Missing generation timestamp",
        "Missing project version in metadata",
    ]
    assert result["copyleft_licenses"] == ["gpl: GPL-3.0"]
    assert result["score"] == 70.0
    assert result["compliance"] == {
        "all_versions_present": False,
        "all_licenses_present": False,
        "no_copyleft_conflicts": False,
        "valid_structure": True,
    }


def test_sbom_validation_main_valid(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    path = _write_json(tmp_path / "s.json", _sbom())
    monkeypatch.setattr(sys, "argv", ["sbom_validation", "--sbom", path])
    val.main()
    out = capsys.readouterr().out
    assert "VALID" in out
    assert "Issues:" not in out
    assert "Warnings:" not in out
    saved = json.loads((tmp_path / "sbom_validation_result.json").read_text("utf-8"))
    assert saved["valid"] is True


def test_sbom_validation_main_invalid(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    doc = {
        "components": [_component("x", licenses=[{"license": {"name": "AGPL-3.0"}}])]
    }
    path = _write_json(tmp_path / "s.json", doc)
    monkeypatch.setattr(sys, "argv", ["sbom_validation", "--sbom", path])
    with pytest.raises(SystemExit) as exc:
        val.main()
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "INVALID" in out
    assert "  - Missing specVersion" in out
    assert "Copyleft licenses found: x: AGPL-3.0" in out
    assert "No Copyleft Conflicts" in out


# --------------------------------------------------------------------------
# vulnerability_scan
# --------------------------------------------------------------------------


def test_vuln_scan_parses_audit(monkeypatch):
    monkeypatch.setattr(vs.subprocess, "run", lambda cmd, **kw: _proc(AUDIT_JSON))
    report = vs.scan_python_vulnerabilities()
    assert report["status"] == "completed"
    assert report["summary"]["total_vulnerabilities"] == 1
    assert report["summary"]["medium"] == 1
    assert report["vulnerabilities"][0] == {
        "package": "requests",
        "installed_version": "2.0",
        "vulnerability_id": "PYSEC-1",
        "description": "bad",
        "fix_versions": ["2.1", "2.2"],
        "aliases": ["CVE-1"],
    }


def test_vuln_scan_empty_output(monkeypatch):
    monkeypatch.setattr(vs.subprocess, "run", lambda cmd, **kw: _proc("  \n"))
    report = vs.scan_python_vulnerabilities()
    assert report["status"] == "completed"
    assert report["vulnerabilities"] == []


@pytest.mark.parametrize(
    "kind,status",
    [("missing", "skipped"), ("timeout", "timeout"), ("bad", "parse_error")],
)
def test_vuln_scan_error_statuses(monkeypatch, capsys, kind, status):
    def fake_run(cmd, **kw):
        if kind == "missing":
            raise FileNotFoundError("pip_audit")
        if kind == "timeout":
            raise vs.subprocess.TimeoutExpired(cmd, 120)
        return _proc("{bad")

    monkeypatch.setattr(vs.subprocess, "run", fake_run)
    report = vs.scan_python_vulnerabilities()
    assert report["status"] == status
    assert report["summary"]["total_vulnerabilities"] == 0
    assert ("pip-audit not installed" in capsys.readouterr().out) == (kind == "missing")


def test_vuln_scan_main(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(vs.subprocess, "run", lambda cmd, **kw: _proc(AUDIT_JSON))
    vs.main()
    report = json.loads((tmp_path / "vulnerability_report.json").read_text("utf-8"))
    assert report["summary"]["total_vulnerabilities"] == 1
    copied = tmp_path / "releases" / "v4.4.0" / "vulnerability_report.json"
    assert json.loads(copied.read_text("utf-8")) == report
    assert "Total: 1" in capsys.readouterr().out


# --------------------------------------------------------------------------
# validate_cross_links
# --------------------------------------------------------------------------


def _registry(artifacts, edges):
    return {
        "artifact_index": {k: {"path": v} for k, v in artifacts.items()},
        "dependency_graph": {"edges": [list(e) for e in edges]},
    }


@pytest.fixture
def xroot(monkeypatch, tmp_path):
    monkeypatch.setattr(xl, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(xl, "REGISTRY_PATH", tmp_path / "cross_link_registry.json")
    for name in ("a.md", "b.md", "c.md"):
        (tmp_path / name).write_text("x", encoding="utf-8")
    return tmp_path


def test_cross_links_helpers():
    reg = _registry(
        {"A": "a.md", "B": "b.md", "C": "c.md", "D": "d.md", "E": "e.md"},
        [
            ("A", "B"),
            ("B", "C"),
            ("C", "A"),
            ("A", "X"),
            ("Y", "Z"),
            ("Q", "D"),
            ("D", "C"),
        ],
    )
    valid, broken = xl.validate_edges(reg)
    assert len(valid) == 4
    assert broken == [
        "A → X (missing: target 'X')",
        "Y → Z (missing: source 'Y', target 'Z')",
        "Q → D (missing: source 'Q')",
    ]
    assert xl.find_orphans(reg) == ["E"]
    cycles = xl.detect_cycles(reg)
    assert len(cycles) == 1
    assert cycles[0][0] == cycles[0][-1]
    assert set(cycles[0]) == {"A", "B", "C"}


def test_cross_links_detect_cycles_diamond():
    reg = _registry({}, [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")])
    assert xl.detect_cycles(reg) == []


def test_cross_links_validate_paths(xroot):
    reg = _registry({"A": "a.md", "Q": "missing.md"}, [])
    assert xl.validate_paths(reg) == (["A"], ["Q: missing.md"])


def test_cross_links_main_clean(xroot, capsys):
    reg = _registry({"A": "a.md", "B": "b.md", "C": "c.md"}, [("A", "B"), ("B", "C")])
    xl.REGISTRY_PATH.write_text(json.dumps(reg), encoding="utf-8")
    assert xl.main() == 0
    out = capsys.readouterr().out
    assert "All artifact paths valid" in out
    assert "All edges reference valid artifacts" in out
    assert "No orphans found" in out
    assert "No circular dependencies" in out
    saved = json.loads(xl.REGISTRY_PATH.read_text(encoding="utf-8"))
    lv = saved["link_validation"]
    assert lv["paths_found"] == 3
    assert lv["broken_links"] == []
    assert lv["cycles"] == 0


def test_cross_links_main_with_issues(xroot, capsys):
    reg = _registry(
        {"A": "a.md", "B": "b.md", "M": "gone.md", "O": "c.md"},
        [("A", "B"), ("B", "A"), ("A", "Z"), ("M", "A")],
    )
    xl.REGISTRY_PATH.write_text(json.dumps(reg), encoding="utf-8")
    assert xl.main() == 1
    out = capsys.readouterr().out
    assert "Missing: M: gone.md" in out
    assert "Broken: A → Z" in out
    assert "⚠️  O" in out
    assert "Cycle Detection: 1 cycles found" in out
    assert "3 ISSUE(S)" in out
    lv = json.loads(xl.REGISTRY_PATH.read_text(encoding="utf-8"))["link_validation"]
    assert lv["orphans"] == ["O"]
    assert lv["paths_missing"] == 1
    assert lv["edges_broken"] == 1
