"""Lane-B wave 12: qplant AI validation (code/doc quality, config validator, migrate)."""

import copy
import json
import sys

import pytest
import yaml

from ._l2_loader import load

cq = load("qplant/ai_validation/code_quality.py")
cv = load("qplant/ai_validation/config_validator.py")
dq = load("qplant/ai_validation/doc_quality.py")
mig = load("qplant/config_service/migrate.py")


# --------------------------------------------------------------------------
# code_quality
# --------------------------------------------------------------------------

CLEAN_SRC = (
    '"""Clean module."""\n\n\ndef add(a, b):\n    """Add."""\n    return a + b\n'
)


def _messy_source():
    risky = [
        "pass" + "word = 'x'",
        "api_" + "key = 'x'",
        "sec" + "ret = 'x'",
        "subprocess.call(cmd, shell=True)",
        "# eval(commented)",
        "LONG = '" + "x" * 130 + "'",
    ]
    body = [
        "import pickle",
        "import time",
        "",
        "",
        "def process(items):",
        "    out = []",
        "    for i in range(len(items)):",
        "        out.append(items[i])",
        "    time.sleep(0)",
        "    return out",
        "",
        "",
        "async def fetch():",
        '    """Fetch."""',
        "    return eval('1')",
        "",
        "",
        "class Thing:",
        "    def __init__(self):",
        "        self.x = exec('y = 1')",
        "",
        "    def _private(self):",
        "        return pickle.loads(b'')",
        "",
        "",
    ]
    return "\n".join(body + risky) + "\n"


def _complex_func(name, ifs):
    lines = ["def " + name + "(x, a, b, c):", '    """Doc."""']
    for i in range(ifs):
        lines.append("    if x == " + str(i) + ":")
        lines.append("        x += 1")
    lines += [
        "    while a and b and c:",
        "        break",
        "    try:",
        "        pass",
        "    except ValueError:",
        "        pass",
        "    return x",
    ]
    return "\n".join(lines) + "\n"


def test_code_quality_messy_file_reports_all_categories(tmp_path):
    src = tmp_path / "messy.py"
    src.write_text(_messy_source(), encoding="utf-8")
    report = cq.CodeQualityAnalyser().analyse_file(str(src))
    assert report.functions == 4
    assert report.classes == 1
    assert report.max_complexity == 2
    msgs = {(i.category, i.message) for i in report.issues}
    cats = {i.category for i in report.issues}
    assert cats == {"documentation", "security", "performance", "style"}
    assert ("documentation", "Missing module-level docstring") in msgs
    assert ("documentation", "Missing docstring for process") in msgs
    assert ("documentation", "Missing docstring for __init__") in msgs
    assert not any("_private" in m for _, m in msgs)
    sec = sorted(i.message for i in report.issues if i.category == "security")
    assert any("eval()" in m for m in sec)
    assert any("exec()" in m for m in sec)
    assert any("pickle" in m for m in sec)
    assert any("Shell=True" in m for m in sec)
    assert any("password" in m for m in sec)
    assert any("API key" in m for m in sec)
    assert any("secret" in m for m in sec)
    # commented eval line is ignored
    eval_lines = [
        i.line
        for i in report.issues
        if i.category == "security" and "eval" in i.message
    ]
    assert len(eval_lines) == 1
    perf = {i.message for i in report.issues if i.category == "performance"}
    assert len(perf) == 3
    assert any("Line too long (139" in i.message for i in report.issues)
    assert report.score == 0.0


def test_code_quality_clean_file_capped_score(tmp_path):
    src = tmp_path / "clean.py"
    src.write_text(CLEAN_SRC, encoding="utf-8")
    report = cq.CodeQualityAnalyser().analyse_file(str(src))
    assert report.issues == []
    assert report.doc_coverage == 1.0
    assert report.avg_complexity == 1.0
    assert report.score == 10.0


def test_code_quality_complexity_thresholds(tmp_path):
    src = tmp_path / "cx.py"
    src.write_text(
        '"""M."""\n\n' + _complex_func("big", 13) + "\n" + _complex_func("mid", 6),
        encoding="utf-8",
    )
    report = cq.CodeQualityAnalyser().analyse_file(str(src))
    cx = {i.severity: i.message for i in report.issues if i.category == "complexity"}
    assert cx["error"] == "High complexity (18) in big"
    assert cx["warning"] == "Moderate complexity (11) in mid"
    assert report.max_complexity == 18
    assert report.avg_complexity == 14.5


def test_code_quality_module_without_functions(tmp_path):
    src = tmp_path / "consts.py"
    src.write_text('"""Constants."""\nX = 1\n', encoding="utf-8")
    report = cq.CodeQualityAnalyser().analyse_file(str(src))
    assert report.avg_complexity == 0.0
    assert report.max_complexity == 0
    assert report.score == 10.0


def test_code_quality_syntax_error(tmp_path):
    src = tmp_path / "broken.py"
    src.write_text("def f(:\n    pass\n", encoding="utf-8")
    report = cq.CodeQualityAnalyser().analyse_file(str(src))
    assert report.score == 0
    assert report.issues[0].category == "syntax"
    assert report.issues[0].line == 1
    assert report.issues[0].message.startswith("Syntax error:")


@pytest.mark.parametrize("name", ["missing.py", "notes.txt"])
def test_code_quality_skips_missing_or_non_python(tmp_path, name):
    if name.endswith(".txt"):
        (tmp_path / name).write_text("eval(1)", encoding="utf-8")
    report = cq.CodeQualityAnalyser().analyse_file(str(tmp_path / name))
    assert report.lines == 0
    assert report.issues == []
    assert report.score == 10.0


def test_code_quality_directory_summary(tmp_path):
    (tmp_path / "clean.py").write_text(CLEAN_SRC, encoding="utf-8")
    (tmp_path / "messy.py").write_text(_messy_source(), encoding="utf-8")
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "x.py").write_text("eval(1)\n", encoding="utf-8")
    result = cq.CodeQualityAnalyser().analyse_directory(str(tmp_path))
    summary = result["summary"]
    assert summary["files_analysed"] == 2
    assert summary["average_score"] == 5.0
    assert summary["by_severity"]["critical"] == 4
    assert summary["by_category"]["security"] == 7
    clean = result["files"][str(tmp_path / "clean.py")]
    assert clean["doc_coverage"] == 100.0
    assert clean["issues"] == []
    messy = result["files"][str(tmp_path / "messy.py")]
    assert messy["issue_count"] == len(messy["issues"])
    assert {"line", "severity", "category", "message", "suggestion"} <= set(
        messy["issues"][0]
    )


def test_code_quality_empty_directory(tmp_path):
    result = cq.CodeQualityAnalyser().analyse_directory(str(tmp_path))
    assert result["summary"]["files_analysed"] == 0
    assert result["summary"]["average_score"] == 0
    assert result["files"] == {}


def test_code_quality_score_ignores_unknown_severity():
    report = cq.FileReport(path="x.py", doc_coverage=0.5)
    for sev in ["critical", "error", "warning", "info", "bogus"]:
        report.issues.append(cq.QualityIssue("x.py", 1, sev, "c", "m"))
    assert cq.CodeQualityAnalyser()._calculate_score(report) == pytest.approx(6.4)


# --------------------------------------------------------------------------
# config_validator
# --------------------------------------------------------------------------


def _config():
    return {
        "version": "4.2.0",
        "system": {},
        "flow_parameters": {"wcs_hp": {"design_flow_gs": 350}},
        "pressure_parameters": {
            "wcs_hp_outlet": {"min_barg": 1, "nominal_barg": 2, "max_barg": 3}
        },
        "compressor_specifications": {
            "hp_compressors": {"count": 3},
            "fsd575": {
                "motor_power_kW": 315,
                "per_unit_flow_gs": 120,
                "efficiency_percent": [70, 75],
            },
            "three_skid_totals": {"max_total_flow_gs": 360},
        },
        "financial": {
            "electricity_cost_eur_kwh": 0.15,
            "project_lifetime_years": 20,
            "operating_hours_year": 8000,
        },
        "compliance": {},
    }


def _validate(cfg):
    v = cv.ConfigValidator()
    v.load_dict(cfg)
    return v.validate_all()


def _by_path(report, path, check=None):
    return [
        r
        for r in report["results"]
        if r["path"] == path and (check is None or r["check"] == check)
    ]


def test_config_validator_all_pass_with_suggestions():
    report = _validate(_config())
    assert report["valid"] is True
    assert report["score"] == 100.0
    assert report["summary"] == {"pass": report["total_checks"]}
    assert report["total_checks"] == 7 + 5 + 3 + 3
    cats = [s["category"] for s in report["suggestions"]]
    assert cats == ["efficiency", "maintenance"]
    assert "72.5%" in report["suggestions"][0]["message"]


def test_config_validator_loads_from_yaml(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(_config()), encoding="utf-8")
    v = cv.ConfigValidator(str(path))
    assert v.config["version"] == "4.2.0"
    assert v._get_value("financial.project_lifetime_years") == 20
    assert v._get_value("financial.nope") is None
    assert v._get_value("version.deeper") is None


def test_config_validator_range_and_type_failures():
    cfg = _config()
    cfg["compressor_specifications"]["fsd575"]["motor_power_kW"] = 5000
    cfg["financial"]["project_lifetime_years"] = "long"
    cfg["financial"]["electricity_cost_eur_kwh"] = 0.5
    del cfg["flow_parameters"]["wcs_hp"]
    report = _validate(cfg)
    assert report["valid"] is False
    out = _by_path(report, "compressor_specifications.fsd575.motor_power_kW")[0]
    assert out["level"] == "error"
    assert out["suggested_value"] == 315
    assert "outside range [100, 1000]" in out["message"]
    typ = _by_path(report, "financial.project_lifetime_years", "type")[0]
    assert typ["message"] == "Expected int, got str"
    info = _by_path(report, "financial.electricity_cost_eur_kwh", "range")[0]
    assert info["level"] == "info"
    assert info["confidence"] == 0.5
    miss = _by_path(report, "flow_parameters.wcs_hp.design_flow_gs", "range")[0]
    assert miss["level"] == "warning"


def test_config_validator_non_numeric_electricity_cost_crashes():
    """production_defect: validate_all raises TypeError when
    financial.electricity_cost_eur_kwh is a string, because _validate_semantics
    compares it to floats instead of relying on the range check's type error;
    this test fails once fixed."""
    cfg = _config()
    cfg["financial"]["electricity_cost_eur_kwh"] = "cheap"
    with pytest.raises(TypeError, match="not supported between"):
        _validate(cfg)


def test_config_validator_dependency_failures():
    cfg = _config()
    cfg["compressor_specifications"]["three_skid_totals"]["max_total_flow_gs"] = 100
    cfg["pressure_parameters"]["wcs_hp_outlet"]["max_barg"] = 2
    report = _validate(cfg)
    dep = {r["path"]: r for r in report["results"] if r["check"] == "dependency"}
    assert dep["compressor_flow_consistency"]["level"] == "error"
    assert dep["compressor_flow_consistency"]["current_value"] == [3, 120, 100]
    assert dep["flow_capacity_adequacy"]["level"] == "error"
    assert dep["pressure_range_valid"]["message"].startswith("Dependency check failed")


def test_config_validator_dependency_missing_and_exception():
    cfg = _config()
    cfg["compressor_specifications"]["fsd575"]["per_unit_flow_gs"] = "lots"
    del cfg["pressure_parameters"]["wcs_hp_outlet"]
    report = _validate(cfg)
    dep = [r for r in report["results"] if r["check"] == "dependency"]
    err = [r for r in dep if r["path"] == "compressor_flow_consistency"][0]
    assert err["level"] == "warning"
    assert err["message"].startswith("Dependency check error:")
    missing = [r for r in dep if "missing values" in r["message"]][0]
    assert "pressure_range_valid" in missing["message"]
    assert missing["level"] == "warning"


@pytest.mark.parametrize(
    "version,count,elec,expected",
    [
        ("4.x.0", 2, 0.9, {"version": "error", "count": "warning", "elec": None}),
        ("", 0, None, {"version": "error", "count": None, "elec": None}),
        ("1.2", 5, 0.05, {"version": "pass", "count": "pass", "elec": "pass"}),
    ],
)
def test_config_validator_semantics(version, count, elec, expected):
    cfg = _config()
    cfg["version"] = version
    cfg["compressor_specifications"]["hp_compressors"]["count"] = count
    cfg["financial"]["electricity_cost_eur_kwh"] = elec
    v = cv.ConfigValidator()
    v.load_dict(cfg)
    sem = {r.path: r.level for r in v._validate_semantics()}
    assert sem["version"] == expected["version"]
    assert (
        sem.get("compressor_specifications.hp_compressors.count") == expected["count"]
    )
    assert sem.get("financial.electricity_cost_eur_kwh") == expected["elec"]


def test_config_validator_no_suggestions_and_empty_score():
    cfg = _config()
    cfg["compressor_specifications"]["fsd575"]["efficiency_percent"] = [90, 95]
    cfg["financial"]["operating_hours_year"] = 4000
    v = cv.ConfigValidator()
    v.load_dict(cfg)
    assert v._generate_suggestions() == []
    cfg["compressor_specifications"]["fsd575"]["efficiency_percent"] = 85.0
    assert v._generate_suggestions() == []
    assert v._calculate_score([]) == 0.0


def test_config_validator_empty_config_is_invalid():
    report = _validate({})
    assert report["valid"] is False
    assert report["summary"]["error"] == 8
    assert report["summary"]["warning"] == 8
    assert report["score"] == 0.0
    assert report["suggestions"] == []


def test_config_validation_result_to_dict():
    r = cv.ValidationResult("p", "pass", "c", "m", current_value=1)
    assert r.to_dict() == {
        "path": "p",
        "level": "pass",
        "check": "c",
        "message": "m",
        "current_value": 1,
        "suggested_value": None,
        "confidence": 0.8,
    }


# --------------------------------------------------------------------------
# doc_quality
# --------------------------------------------------------------------------

LONG_PARA = " ".join(["word"] * 105)

MARKDOWN = "\n".join(
    [
        "# Overview",
        "",
        "Short intro. It is fine.",
        "",
        "## Usage",
        "",
        LONG_PARA,
        "",
        "",
        "## Testing notes",
        "#",
        "```",
        "code",
        "```",
        "See [docs](http://example.invalid) and [empty]( ).",
        "![](img.png) ![alt](b.png)",
        "",
        "| a | b |",
        "| - | - |",
        "| 1 | 2 |",
        "trailing paragraph",
    ]
)

HTML = (
    "<html><h1>One</h1><h2>Two</h2>\n<pre>x</pre><code>y</code>\n"
    '<a href="x">l</a><img src="a.png">\n<img alt="b" src="b.png">'
    "<table></table></html>"
)


def test_doc_quality_markdown(tmp_path):
    md = tmp_path / "README.md"
    md.write_text(MARKDOWN, encoding="utf-8")
    report = dq.DocQualityAnalyser().analyse_file(str(md))
    assert report.format == "markdown"
    assert report.headers == 4
    assert report.code_blocks == 1
    assert report.links == 3
    assert report.images == 2
    assert report.tables == 1
    assert report.completeness_score == pytest.approx(0.3)
    by_msg = {i.message: i for i in report.issues}
    assert by_msg["Empty header"].line == 11
    assert by_msg["Long paragraph (105 words)"].line == 7
    assert by_msg["Empty link target for 'empty'"].severity == "error"
    assert by_msg["Image missing alt text"].line == 16
    assert len(report.issues) == 4
    assert 0 <= report.overall_score <= 10


def test_doc_quality_html(tmp_path):
    page = tmp_path / "page.htm"
    page.write_text(HTML, encoding="utf-8")
    report = dq.DocQualityAnalyser().analyse_file(str(page))
    assert report.format == "html"
    assert (report.headers, report.code_blocks, report.links) == (2, 2, 1)
    assert (report.images, report.tables) == (2, 1)
    assert report.completeness_score == pytest.approx(0.4)
    assert [i.line for i in report.issues] == [3]


def test_doc_quality_html_without_headers(tmp_path):
    page = tmp_path / "bare.html"
    page.write_text("<p>Hi there.</p>", encoding="utf-8")
    report = dq.DocQualityAnalyser().analyse_file(str(page))
    assert report.completeness_score == 0.0


@pytest.mark.parametrize(
    "name,fmt", [("a.rst", "restructuredtext"), ("a.txt", "unknown")]
)
def test_doc_quality_other_formats(tmp_path, name, fmt):
    f = tmp_path / name
    f.write_text("# Title\n\nSome text here.", encoding="utf-8")
    report = dq.DocQualityAnalyser().analyse_file(str(f))
    assert report.format == fmt
    assert report.headers == 0
    assert report.words == 5


def test_doc_quality_missing_file(tmp_path):
    report = dq.DocQualityAnalyser().analyse_file(str(tmp_path / "nope.md"))
    assert report.format == "unknown"
    assert report.lines == 0


def test_doc_quality_empty_sections_list(tmp_path):
    md = tmp_path / "x.markdown"
    md.write_text("# Anything\n", encoding="utf-8")
    analyser = dq.DocQualityAnalyser()
    analyser.EXPECTED_SECTIONS_MD = []
    assert analyser.analyse_file(str(md)).completeness_score == 1.0


def test_doc_quality_readability_and_syllables():
    a = dq.DocQualityAnalyser()
    assert a._calculate_readability("") == 0.0
    assert a._calculate_readability("### ``` |") == 0.0
    assert a._calculate_readability("The cat sat. The dog ran.") == 100
    hard = "Internationalization considerations notwithstanding, organizational"
    assert a._calculate_readability(hard) == 0
    assert a._count_syllables("cat") == 1
    assert a._count_syllables("make") == 1
    assert a._count_syllables("banana,") == 3
    assert a._count_syllables("rhythm") == 1


@pytest.mark.parametrize(
    "readability,headers,code,severities,expected",
    [
        (70, 3, 1, [], 9.0),
        (50, 0, 0, ["error", "warning", "info"], 5.7),
        (10, 0, 0, ["error"] * 9, 0),
        (90, 5, 2, [], 9.0),
    ],
)
def test_doc_quality_overall_score(readability, headers, code, severities, expected):
    report = dq.DocReport(
        path="p",
        format="markdown",
        headers=headers,
        code_blocks=code,
        readability_score=readability,
        completeness_score=0.5,
    )
    report.issues = [dq.DocIssue("p", 1, s, "c", "m") for s in severities]
    assert dq.DocQualityAnalyser()._calculate_overall(report) == pytest.approx(expected)


def test_doc_quality_directory(tmp_path):
    (tmp_path / "README.md").write_text(MARKDOWN, encoding="utf-8")
    (tmp_path / "page.html").write_text(HTML, encoding="utf-8")
    nm = tmp_path / "node_modules"
    nm.mkdir()
    (nm / "x.md").write_text("# x", encoding="utf-8")
    pc = tmp_path / "__pycache__"
    pc.mkdir()
    (pc / "y.md").write_text("# y", encoding="utf-8")
    result = dq.DocQualityAnalyser().analyse_directory(str(tmp_path))
    assert result["summary"]["files_analysed"] == 2
    assert result["summary"]["total_issues"] == 5
    files = result["files"]
    assert files[str(tmp_path / "page.html")]["format"] == "html"
    md = files[str(tmp_path / "README.md")]
    assert md["issue_count"] == 4
    assert set(md["issues"][0]) == {"line", "severity", "category", "message"}


def test_doc_quality_directory_empty_and_custom_pattern(tmp_path):
    a = dq.DocQualityAnalyser()
    empty = a.analyse_directory(str(tmp_path))
    assert empty["summary"]["average_score"] == 0
    assert empty["summary"]["average_readability"] == 0
    (tmp_path / "a.rst").write_text("Hello world.", encoding="utf-8")
    res = a.analyse_directory(str(tmp_path), patterns=["*.rst"])
    assert res["summary"]["files_analysed"] == 1


# --------------------------------------------------------------------------
# config_service/migrate
# --------------------------------------------------------------------------


def _migrate_config():
    cfg = copy.deepcopy(_config())
    cfg["version"] = "4.1.0"
    return cfg


def _write_cfg(tmp_path, cfg):
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return path


def test_migrate_check_missing_file(tmp_path):
    report = mig.ConfigMigration(str(tmp_path / "none.yaml")).check()
    assert report["config_exists"] is False
    assert report["checks"] == [
        {"check": "file_exists", "status": "FAIL", "detail": "Config file not found"}
    ]
    assert "overall" not in report


def test_migrate_check_pass(tmp_path):
    path = _write_cfg(tmp_path, _migrate_config())
    (tmp_path / "config.prod.yaml").write_text("x: 1\n", encoding="utf-8")
    report = mig.ConfigMigration(str(path)).check()
    assert report["overall"] == "PASS"
    statuses = {c["check"]: c["status"] for c in report["checks"]}
    assert statuses["version_format"] == "PASS"
    assert statuses["section_financial"] == "PASS"
    assert statuses["env_overlay_prod"] == "PASS"
    assert statuses["env_overlay_dev"] == "INFO"


def test_migrate_check_needs_migration(tmp_path):
    path = _write_cfg(tmp_path, {"version": "4.x", "system": {}})
    report = mig.ConfigMigration(str(path)).check()
    assert report["overall"] == "NEEDS_MIGRATION"
    statuses = {c["check"]: c["status"] for c in report["checks"]}
    assert statuses["version_format"] == "FAIL"
    assert statuses["section_system"] == "PASS"
    assert statuses["section_compliance"] == "FAIL"
    assert "Add missing section: financial" in report["migrations_needed"]
    assert any(
        m.startswith("Fix compressor count: 0") for m in report["migrations_needed"]
    )


def test_migrate_execute_and_rollback(tmp_path):
    cfg = _migrate_config()
    del cfg["version"]
    path = _write_cfg(tmp_path, cfg)
    (tmp_path / "config.dr.yaml").write_text("keep: true\n", encoding="utf-8")
    m = mig.ConfigMigration(str(path))
    result = m.execute(target_version="9.9.9")
    steps = [s["step"] for s in result["steps"]]
    assert steps == [
        "backup",
        "version_update",
        "create_overlay_dev",
        "create_overlay_staging",
        "create_overlay_prod",
        "save_config",
    ]
    assert "unknown" in result["steps"][1]["detail"]
    saved = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert saved["version"] == "9.9.9"
    dev = yaml.safe_load((tmp_path / "config.dev.yaml").read_text(encoding="utf-8"))
    assert dev["financial"]["electricity_cost_eur_kwh"] == 0.10
    assert (tmp_path / "config.dr.yaml").read_text(encoding="utf-8") == "keep: true\n"
    backups = list((tmp_path / "backups").glob("config_*.yaml"))
    assert len(backups) == 1

    rb = m.rollback()
    assert rb["status"] == "OK"
    assert rb["restored_from"] == str(backups[0])
    assert "version" not in yaml.safe_load(path.read_text(encoding="utf-8"))


def test_migrate_rollback_without_backups(tmp_path):
    m = mig.ConfigMigration(str(tmp_path / "config.yaml"))
    assert m.rollback() == {"status": "FAIL", "detail": "No backups found"}
    (tmp_path / "backups").mkdir()
    assert m.rollback() == {"status": "FAIL", "detail": "No backup files found"}


def test_migrate_overlay_unknown_env():
    m = mig.ConfigMigration("config.yaml")
    assert m._generate_env_overlay("qa") == {"description": "qa overlay"}
    assert m._generate_env_overlay("staging")["description"].startswith("Staging")


@pytest.mark.parametrize("flag", ["--check", "--execute", "--rollback", None])
def test_migrate_main(tmp_path, monkeypatch, capsys, flag):
    path = _write_cfg(tmp_path, _migrate_config())
    argv = ["migrate", "--config", str(path), "--version", "5.0.0"]
    if flag:
        argv.append(flag)
    monkeypatch.setattr(sys, "argv", argv)
    mig.main()
    out = capsys.readouterr().out
    if flag is None:
        assert "QPLANT Config Migration Tool" in out
        return
    data = json.loads(out)
    if flag == "--check":
        assert data["overall"] == "PASS"
    elif flag == "--execute":
        assert data["target_version"] == "5.0.0"
    else:
        assert data == {"status": "FAIL", "detail": "No backups found"}
