"""Lane A wave 7: local_mcp/agents/analysis_smoke_test_v2.3_OPTIMIZED.py."""

import json

import pytest

from tests.coverage_waves.lane_a._load import load

st = load("local_mcp/agents/analysis_smoke_test_v2.3_OPTIMIZED.py")
Agent = st.MemoryEfficientSmokeTestV23

DOC = "local_mcp/agents/documentation_framework_v2.3_OPTIMIZED.py"
REC = "local_mcp/agents/recursive_framework_v2.3_OPTIMIZED.py"
ORCH = "local_mcp/agent_orchestrator_v3.0.py"


def _write(root, rel, data=b"# stub\n"):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _full_repo(root):
    _write(root, DOC, b"class MemoryEfficientDocumentationFrameworkV23:\n    pass\n")
    _write(root, REC, b"class MemoryEfficientRecursiveFrameworkV23:\n    pass\n")
    for rel in st._EXPECTED_PATHS[2:]:
        _write(root, rel)
    _write(root, "tracking_v2.3/tasks/tasks.json", b'{"tasks": []}')


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    return root


@pytest.fixture
def agent(tmp_path, repo, monkeypatch):
    monkeypatch.chdir(tmp_path)
    a = Agent({"output_dir": str(tmp_path / "out")})
    a._repo_root = repo
    return a


def test_init_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    a = Agent()
    assert a.config == {}
    assert a.version == "v2.3.0"
    assert a.name == "analysis_smoke_test"
    assert (tmp_path / "smoke_test_outputs_v2.3").is_dir()
    assert a.get_results() == []


def test_pass_fail_skip_counters_and_log(agent, capsys):
    assert agent._pass("a") == {"check": "a", "status": "PASS"}
    assert agent._fail("b", "r")["reason"] == "r"
    assert agent._skip("c", "s")["status"] == "SKIP"
    m = agent.performance_metrics
    assert (m["checks_passed"], m["checks_failed"], m["checks_skipped"]) == (1, 1, 1)
    agent._log_dmaic("P", "x")
    agent._log_dmaic("P", "y", "z" * 200)
    assert agent.dmaic_log[0]["result"] == "OK"
    assert len(agent.dmaic_log[1]["result"]) == 120
    assert "[P] x" in capsys.readouterr().out


def test_define_lists_checks(agent):
    d = agent.dmaic_define()
    assert "agent_importability" in d["checks"]
    assert d["constraints"]["version"] == "v2.3.0"
    assert agent.performance_metrics["dmaic_phases_completed"] == 1


def test_measure_empty_repo_reports_all_missing(agent):
    inv = agent.dmaic_measure()
    assert inv["agents_found"] == []
    assert inv["paths_present"] == []
    assert inv["paths_missing"] == st._EXPECTED_PATHS


def test_measure_full_repo(agent, repo):
    _full_repo(repo)
    inv = agent.dmaic_measure()
    assert inv["agents_found"] == ["documentation_framework", "recursive_framework"]
    assert inv["paths_missing"] == []


def test_analyze_full_repo_all_pass(agent, repo):
    _full_repo(repo)
    analysis = agent.dmaic_analyze(agent.dmaic_measure())
    statuses = {c["check"]: c["status"] for c in analysis["check_results"]}
    assert set(statuses.values()) == {"PASS"}
    assert statuses["tracking_db:valid_json"] == "PASS"
    assert analysis["total"] == 2 + len(st._EXPECTED_PATHS) + 2
    assert analysis["pass_rate"] == 1.0
    assert analysis["failed"] == 0


def test_analyze_empty_repo_fails_and_skips(agent):
    analysis = agent.dmaic_analyze(agent.dmaic_measure())
    by = {c["check"]: c for c in analysis["check_results"]}
    assert by["import:documentation_framework"]["reason"].startswith("File not found")
    assert by["orchestrator:instantiation"]["status"] == "FAIL"
    assert by["tracking_db:valid_json"]["status"] == "SKIP"
    assert analysis["passed"] == 0
    assert analysis["skipped"] == 1
    assert analysis["pass_rate"] == 0.0


def test_analyze_missing_class_exec_error_and_bad_json(agent, repo):
    _write(repo, DOC, b"X = 1\n")
    _write(repo, REC, b"raise RuntimeError('boom at import')\n")
    _write(repo, "tracking_v2.3/tasks/tasks.json", b"{not json")
    analysis = agent.dmaic_analyze(agent.dmaic_measure())
    by = {c["check"]: c for c in analysis["check_results"]}
    doc = by["import:documentation_framework"]
    assert "MemoryEfficientDocumentationFrameworkV23" in doc["reason"]
    assert by["import:recursive_framework"]["reason"] == "boom at import"
    assert by["tracking_db:valid_json"]["reason"].startswith("Invalid JSON")


def test_analyze_zero_total_branch(agent, monkeypatch):
    monkeypatch.setattr(st, "_EXPECTED_AGENTS", [])
    monkeypatch.setattr(st, "_EXPECTED_PATHS", [])
    analysis = agent.dmaic_analyze({"paths_present": []})
    # orchestrator + tracking checks always run, so total is 2.
    assert analysis["total"] == 2


def test_improve_generates_hints_per_kind(agent):
    analysis = {
        "check_results": [
            {"check": "import:foo", "status": "FAIL", "reason": "r1"},
            {"check": "path:a/b:c", "status": "FAIL", "reason": "r2"},
            {"check": "orchestrator:instantiation", "status": "FAIL"},
            {"check": "tracking_db:valid_json", "status": "FAIL", "reason": "r4"},
            {"check": "ok", "status": "PASS"},
        ]
    }
    res = agent.dmaic_improve(analysis)
    hints = [h["hint"] for h in res["hints"]]
    assert res["hint_count"] == 4
    assert hints[0] == "Implement agent stub at local_mcp/agents/foo_v2.3_OPTIMIZED.py"
    assert hints[1] == "Create missing artifact: a/b:c"
    assert "agent_orchestrator_v3.0.py" in hints[2]
    assert hints[3] == "Investigate manually"
    assert res["hints"][2]["reason"] == ""


def test_improve_empty_analysis(agent):
    assert agent.dmaic_improve({}) == {"hints": [], "hint_count": 0}


def test_control_gate_pass_and_fail(agent):
    # dict(...) rather than a literal: CI's bandit 1.8.6 reports B105 for
    # dict keys that look like "pass"-words.
    analysis = dict(pass_rate=0.8, passed=8, failed=2, total=10)
    c = agent.dmaic_control(analysis, {"hint_count": 2})
    assert c["gate_status"] == "PASS"
    assert c["gate_threshold"] == 0.8
    assert c["summary"]["remediation_hints"] == 2
    assert c["summary"]["checks_skipped"] == 0
    agent.config.update(pass_rate_threshold=0.9)
    assert agent.dmaic_control(analysis, {})["gate_status"] == "FAIL"
    assert agent.dmaic_control({}, {})["pass_rate"] == 0.0


def test_run_full_repo_success_and_saves(agent, repo, tmp_path):
    _full_repo(repo)
    result = agent.run()
    assert result["status"] == "success"
    assert result["dmaic_results"]["control"]["gate_status"] == "PASS"
    assert agent.performance_metrics["dmaic_phases_completed"] == 5
    assert agent.get_results() == [result]
    saved = tmp_path / "out" / ("smoke_test_results_" + agent.timestamp + ".json")
    assert json.loads(saved.read_text(encoding="utf-8"))["status"] == "success"


def test_run_empty_repo_failure(agent):
    result = agent.run()
    assert result["status"] == "failure"
    assert result["dmaic_results"]["improve"]["hint_count"] > 0


def test_run_exception_returns_error(agent, monkeypatch, capsys):
    def broken():
        raise RuntimeError("measure broke")

    monkeypatch.setattr(agent, "dmaic_measure", broken)
    result = agent.run()
    assert result["status"] == "error"
    assert result["error"] == "measure broke"
    assert result["performance_metrics"]["errors_handled"] == 1
    assert "ERROR: measure broke" in capsys.readouterr().out
    assert agent.get_results() == []


def test_save_results_failure_is_reported(agent, tmp_path, capsys):
    agent.output_dir = tmp_path / "missing_dir" / "nested"
    agent._save_results({"a": 1})
    assert "Warning: Could not save results" in capsys.readouterr().out


def test_main_pass_and_fail(tmp_path, repo, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    fake_file = repo / "local_mcp" / "agents" / "smoke.py"
    monkeypatch.setattr(st, "__file__", str(fake_file))
    assert st.main() == 1
    assert "Gate Status : FAIL" in capsys.readouterr().out
    _full_repo(repo)
    assert st.main() == 0
    assert "Gate Status : PASS" in capsys.readouterr().out


def test_main_error_result_returns_one(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    def broken(self):
        return {"status": "error"}

    monkeypatch.setattr(Agent, "run", broken)
    assert st.main() == 1
    assert "Gate Status : UNKNOWN" in capsys.readouterr().out
