"""Lane-B wave 11: convergence check, code health check and DAB flake8 census."""

import json
import sys
import types

import pytest

from ._l2_loader import load

cc = load("scripts/check_convergence.py")
ch = load("scripts/code_health_check.py")
fc = load("scripts/dab_flake8_census.py")

DEFAULT_CONFIG = {
    "convergence_calculation": {
        "weights": {
            "file_stability": 0.30,
            "test_stability": 0.25,
            "metric_stability": 0.20,
            "knowledge_growth": 0.15,
            "zero_regressions": 0.10,
        },
        "thresholds": {"converged": 95.0, "stable": 85.0, "developing": 70.0},
    }
}


@pytest.fixture
def ws(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cc, "ROOT", tmp_path)
    monkeypatch.setattr(cc, "REPORTS", tmp_path / "DMAIC_V3_OUTPUT" / "reports")
    return tmp_path


# --------------------------------------------------------------- convergence


def test_load_config_defaults_when_missing(ws, capsys):
    config = cc.load_config()
    assert config == DEFAULT_CONFIG
    assert "not found, using defaults" in capsys.readouterr().out


def test_load_config_reads_yaml(ws):
    (ws / "config").mkdir()
    (ws / "config" / "maturity_config.yaml").write_text(
        "convergence_calculation:\n  thresholds:\n    converged: 50\n",
        encoding="utf-8",
    )
    config = cc.load_config()
    assert config["convergence_calculation"]["thresholds"]["converged"] == 50


def test_calculate_file_hash_ok_and_error(tmp_path):
    target = tmp_path / "f.py"
    target.write_bytes(b"x = 1\n")
    digest = cc.calculate_file_hash(target)
    assert len(digest) == 64
    assert digest == cc.hashlib.sha256(b"x = 1\n").hexdigest()
    assert cc.calculate_file_hash(tmp_path / "absent.py").startswith("ERROR:")


def _make_tree(root):
    (root / "pkg").mkdir()
    (root / "pkg" / "a.py").write_text("a = 1\n", encoding="utf-8")
    (root / "pkg" / "b.py").write_text("b = 2\n", encoding="utf-8")
    (root / "pkg" / "__pycache__").mkdir()
    (root / "pkg" / "__pycache__" / "c.py").write_text("c\n", encoding="utf-8")
    (root / "dir.py").mkdir()  # matches *.py but is not a file


def test_scan_workspace_files_first_run_writes_history(ws):
    _make_tree(ws)
    total, stable = cc.scan_workspace_files()
    assert (total, stable) == (2, 0)
    history = json.loads(
        (ws / "DMAIC_V3_OUTPUT" / ".file_hashes.json").read_text(encoding="utf-8")
    )
    assert len(history) == 1
    assert history[0]["iteration"] == 1
    assert sorted(history[0]["hashes"]) == sorted(
        [str(cc.Path("pkg/a.py")), str(cc.Path("pkg/b.py"))]
    )


def test_scan_workspace_files_counts_stable_against_third_last(ws):
    _make_tree(ws)
    a_key = str(cc.Path("pkg/a.py"))
    b_key = str(cc.Path("pkg/b.py"))
    good = cc.calculate_file_hash(ws / "pkg" / "a.py")
    history = [
        {"hashes": {a_key: good, b_key: "stale"}},
        {"hashes": {}},
        {"hashes": {}},
    ]
    hash_file = ws / "DMAIC_V3_OUTPUT" / ".file_hashes.json"
    hash_file.parent.mkdir(parents=True)
    hash_file.write_text(json.dumps(history), encoding="utf-8")
    assert cc.scan_workspace_files() == (2, 1)
    saved = json.loads(hash_file.read_text(encoding="utf-8"))
    assert len(saved) == 4
    assert saved[-1]["iteration"] == 4


def test_scan_workspace_files_short_history_has_no_stable(ws):
    _make_tree(ws)
    hash_file = ws / "DMAIC_V3_OUTPUT" / ".file_hashes.json"
    hash_file.parent.mkdir(parents=True)
    hash_file.write_text(json.dumps([{"hashes": {}}]), encoding="utf-8")
    assert cc.scan_workspace_files() == (2, 0)


def test_scan_workspace_files_corrupt_history_crashes(ws, capsys):
    """production_defect: a corrupt .file_hashes.json is reported as a warning
    but then re-read without a guard, so scan_workspace_files raises
    JSONDecodeError; this test fails once fixed."""
    _make_tree(ws)
    hash_file = ws / "DMAIC_V3_OUTPUT" / ".file_hashes.json"
    hash_file.parent.mkdir(parents=True)
    hash_file.write_text("{not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        cc.scan_workspace_files()
    assert "Could not load previous hashes" in capsys.readouterr().out


def test_fixed_stability_estimates():
    assert cc.check_test_stability() == (10, 10)
    assert cc.check_metric_stability() == (8, 6)


@pytest.mark.parametrize("count, expected", [(0, (0, 1)), (5, (5, 1)), (20, (20, 2))])
def test_check_knowledge_growth(ws, count, expected):
    kdir = ws / "DMAIC_V3_OUTPUT" / "knowledge"
    kdir.mkdir(parents=True)
    for index in range(count):
        (kdir / f"k{index}.json").write_text("{}", encoding="utf-8")
    assert cc.check_knowledge_growth() == expected


def test_check_knowledge_growth_missing_dir(ws):
    assert cc.check_knowledge_growth() == (0, 0)


def test_calculate_convergence_score_regressions_and_cap():
    full = cc.calculate_convergence_score(100, 100, 100, 250, 0, DEFAULT_CONFIG)
    assert full == 100.0
    regressed = cc.calculate_convergence_score(100, 100, 100, 100, 2, DEFAULT_CONFIG)
    assert regressed == 90.0


@pytest.mark.parametrize(
    "score, level", [(99.0, 3), (95.0, 3), (90.0, 2), (75.0, 1), (10.0, 0)]
)
def test_determine_maturity_level(score, level):
    assert cc.determine_maturity_level(score, DEFAULT_CONFIG) == level


def test_latest_metrics(ws):
    assert cc.latest_metrics() is None
    cc.REPORTS.mkdir(parents=True)
    assert cc.latest_metrics() is None
    (cc.REPORTS / "dmaic_v3_run_001_metrics.json").write_text("{}", encoding="utf-8")
    (cc.REPORTS / "dmaic_v3_run_002_metrics.json").write_text("{}", encoding="utf-8")
    assert cc.latest_metrics().name == "dmaic_v3_run_002_metrics.json"


def test_main_empty_workspace_writes_report(ws, capsys):
    assert cc.main() == 0
    out = capsys.readouterr().out
    reports = sorted(cc.REPORTS.glob("dmaic_v3_convergence_*.json"))
    assert len(reports) == 1
    data = json.loads(reports[0].read_text(encoding="utf-8"))
    assert data["iteration"] == 1
    assert data["total_files"] == 0
    assert data["file_stability_pct"] == 100.0
    assert data["metric_stability_pct"] == 75.0
    assert data["knowledge_growth_pct"] == 0.0
    # 0.30*100 + 0.25*100 + 0.20*75 + 0 + 0.10*100
    assert data["convergence_score"] == 80.0
    assert data["maturity_level"] == 1
    assert data["converged"] is False
    assert "Loaded metrics: none" in out
    assert "Convergence score: 80.0" in out


def test_main_with_files_knowledge_and_zero_counts(ws, monkeypatch, capsys):
    _make_tree(ws)
    out_dir = ws / "DMAIC_V3_OUTPUT"
    (out_dir / "knowledge").mkdir(parents=True)
    for index in range(10):
        (out_dir / "knowledge" / f"k{index}.json").write_text("{}", encoding="utf-8")
    (out_dir / "iteration_1").mkdir()
    (out_dir / "iteration_2").mkdir()
    cc.REPORTS.mkdir(parents=True)
    (cc.REPORTS / "dmaic_v3_run_009_metrics.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(cc, "check_test_stability", lambda: (0, 0))
    monkeypatch.setattr(cc, "check_metric_stability", lambda: (0, 0))
    assert cc.main() == 0
    data = json.loads(
        sorted(cc.REPORTS.glob("dmaic_v3_convergence_*.json"))[0].read_text(
            encoding="utf-8"
        )
    )
    assert data["iteration"] == 2
    assert data["total_files"] == 2
    assert data["file_stability_pct"] == 0.0
    assert data["test_stability_pct"] == 100.0
    assert data["metric_stability_pct"] == 100.0
    assert data["knowledge_growth_pct"] == 10.0
    assert "Loaded metrics: dmaic_v3_run_009_metrics.json" in capsys.readouterr().out


# --------------------------------------------------------------- code health


def _proc(stdout=""):
    return types.SimpleNamespace(stdout=stdout, returncode=0, stderr="")


@pytest.mark.parametrize(
    "stdout, expected",
    [('[{"msg-id": "C0114"}]', [{"msg-id": "C0114"}]), ("", []), ("not json", [])],
)
def test_run_pylint_check_parses_output(monkeypatch, tmp_path, stdout, expected):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return _proc(stdout)

    monkeypatch.setattr(ch.subprocess, "run", fake_run)
    assert ch.run_pylint_check(tmp_path / "x.py") == expected
    cmd, kwargs = calls[0]
    assert cmd[:3] == ["python", "-m", "pylint"]
    assert kwargs["timeout"] == 30


def test_run_pylint_check_swallows_errors(monkeypatch, tmp_path, capsys):
    def boom(cmd, **kwargs):
        raise ch.subprocess.TimeoutExpired(cmd, 30)

    monkeypatch.setattr(ch.subprocess, "run", boom)
    assert ch.run_pylint_check(tmp_path / "x.py") == []
    assert "Error checking" in capsys.readouterr().out


def test_run_syntax_check(tmp_path):
    good = tmp_path / "good.py"
    good.write_text("x = 1\n", encoding="utf-8")
    bad = tmp_path / "bad.py"
    bad.write_text("def f(:\n", encoding="utf-8")
    assert ch.run_syntax_check(good) == (True, None)
    ok, message = ch.run_syntax_check(bad)
    assert ok is False
    assert message.startswith("Line 1:")
    ok, message = ch.run_syntax_check(tmp_path / "absent.py")
    assert ok is False
    assert message


def test_count_lines(tmp_path):
    src = tmp_path / "c.py"
    src.write_text("# head\n\nx = 1\n  # inner\ny = 2\n", encoding="utf-8")
    assert ch.count_lines(src) == {"total": 5, "code": 2, "comments": 2, "blank": 1}
    assert ch.count_lines(tmp_path / "absent.py") == {
        "total": 0,
        "code": 0,
        "comments": 0,
        "blank": 0,
    }


def _health_tree(root, with_bad):
    (root / "DMAIC_V3" / "venv").mkdir(parents=True)
    (root / "DMAIC_V3" / "venv" / "skip.py").write_text("def(:\n", encoding="utf-8")
    (root / "DMAIC_V3" / "ok.py").write_text("x = 1\n", encoding="utf-8")
    (root / "src" / "__pycache__").mkdir(parents=True)
    (root / "src" / "__pycache__" / "skip.py").write_text("(\n", encoding="utf-8")
    (root / "src" / "lint.py").write_text("y = 2\n", encoding="utf-8")
    if with_bad:
        (root / "src" / "bad.py").write_text("def f(:\n", encoding="utf-8")


def _fake_pylint(path):
    return [{"n": i} for i in range(7)] if path.name == "lint.py" else []


def test_code_health_main_passes(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _health_tree(tmp_path, with_bad=False)
    monkeypatch.setattr(ch, "run_pylint_check", _fake_pylint)
    assert ch.main() is None
    out = capsys.readouterr().out
    assert "Found 2 Python files" in out
    assert "7 pylint issues" in out
    assert "OK (1 LOC)" in out
    assert "All files passed syntax check" in out
    report = json.loads(
        (tmp_path / "artifacts/json/code_health_report.json").read_text(
            encoding="utf-8"
        )
    )
    assert report["summary"] == {
        "total_files": 2,
        "total_loc": 2,
        "syntax_errors": 0,
        "pylint_issues": 7,
    }
    lint = [r for r in report["files"] if r["file"].endswith("lint.py")][0]
    assert len(lint["pylint_details"]) == 5


def test_code_health_main_exits_on_syntax_error(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _health_tree(tmp_path, with_bad=True)
    monkeypatch.setattr(ch, "run_pylint_check", _fake_pylint)
    with pytest.raises(SystemExit) as exc:
        ch.main()
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "SYNTAX ERROR: Line 1" in out
    assert "SYNTAX ERRORS FOUND" in out


# --------------------------------------------------------------- flake8 census

STATS = "3     E501 line too long\n1     F401 unused\n  2   E999 SyntaxError\n6\n"


def test_parse_statistics_with_and_without_total():
    assert fc.parse_statistics(STATS) == (6, {"E501": 3, "F401": 1, "E999": 2})
    assert fc.parse_statistics("4 W293 ws\nnoise\n") == (4, {"W293": 4})
    assert fc.parse_statistics("") == (0, {})


def test_git_head(monkeypatch):
    calls = []

    def fake(cmd, text):
        calls.append(cmd)
        return "abc123\n"

    monkeypatch.setattr(fc.subprocess, "check_output", fake)
    assert fc.git_head() == "abc123"
    assert calls == [["git", "rev-parse", "HEAD"]]


def _fake_flake8(monkeypatch, stdout=STATS, code=0):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return types.SimpleNamespace(stdout=stdout, returncode=code)

    monkeypatch.setattr(fc.subprocess, "run", fake_run)
    return calls


def test_run_census_uses_git_head_when_no_sha(monkeypatch):
    calls = _fake_flake8(monkeypatch)
    monkeypatch.setattr(fc, "git_head", lambda: "deadbeef")
    raw, payload = fc.run_census()
    assert raw == STATS
    assert calls[0][0] == "flake8"
    assert payload["exact_sha"] == "deadbeef"
    assert payload["total"] == 6
    assert payload["families"]["E999"] == 2
    assert payload["families"]["F821"] == 0
    assert list(payload["all_families"]) == ["E501", "E999", "F401"]
    assert payload["governance"]["authority_transfer"] is False
    assert payload["command"].startswith("flake8 . --count")


def test_run_census_explicit_sha(monkeypatch):
    _fake_flake8(monkeypatch, code=1)
    monkeypatch.setattr(fc, "git_head", lambda: pytest.fail("git called"))
    _, payload = fc.run_census("feed")
    assert payload["exact_sha"] == "feed"
    assert payload["exit_code"] == 1


@pytest.mark.parametrize("sha, expected", [(None, "PARSE_FIXTURE"), ("cafe", "cafe")])
def test_main_parse_fixture(tmp_path, monkeypatch, capsys, sha, expected):
    fixture = tmp_path / "stats.txt"
    fixture.write_text(STATS, encoding="utf-8")
    json_out = tmp_path / "out" / "c.json"
    text_out = tmp_path / "txt" / "c.txt"
    argv = [
        "dab",
        "--parse-fixture",
        str(fixture),
        "--json-out",
        str(json_out),
        "--text-out",
        str(text_out),
    ]
    if sha:
        argv += ["--exact-sha", sha]
    monkeypatch.setattr(sys, "argv", argv)
    fc.main()
    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["exact_sha"] == expected
    assert payload["total"] == 6
    assert "governance" not in payload
    assert text_out.read_text(encoding="utf-8") == STATS
    assert json.loads(capsys.readouterr().out) == payload


def test_main_live_census(tmp_path, monkeypatch, capsys):
    _fake_flake8(monkeypatch, stdout="1 E722 bare\n1\n")
    monkeypatch.setattr(fc, "git_head", lambda: "0123")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["dab"])
    fc.main()
    payload = json.loads(
        (tmp_path / "reports/dab_flake8_census.json").read_text(encoding="utf-8")
    )
    assert payload["exact_sha"] == "0123"
    assert payload["families"]["E722"] == 1
    assert (tmp_path / "reports/dab_flake8_census.txt").read_text(
        encoding="utf-8"
    ) == "1 E722 bare\n1\n"
    assert json.loads(capsys.readouterr().out)["schema_version"] == "1.1"
