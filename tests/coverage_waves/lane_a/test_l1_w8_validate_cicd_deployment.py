"""Behaviour tests for ABACUS-v032/validate_cicd_deployment.py.

All docker / docker-compose calls are replaced with fakes; nothing external runs.
"""

import json
import types

import pytest

from tests.coverage_waves.lane_a._load import load

vc = load("ABACUS-v032/validate_cicd_deployment.py")

ENGINE = "execute_full_dmaic_phases_0_to_9_v033.py"
GOOD_DOCKERFILE = "\n".join(
    [
        "# ABACUS v033 CANONICAL ALIGNED | SPRINT TESTED | DOW TESTED",
        "EXPOSE 8000",
        "CMD python " + ENGINE,
    ]
)
GOOD_COMPOSE = "\n".join(
    [
        "services:",
        "  abacus-v033:",
        "    environment: [CANONICAL=1]",
        "    command: python " + ENGINE,
        "    ports: ['8000:8000', '8080:8080']",
        "  prometheus:",
        "    ports: ['9090:9090']",
        "  grafana:",
        '    ports: ["3000:3000"]',
        "networks:",
        "  abacus-network: {}",
    ]
)
GOOD_CI = "\n".join(
    [
        "name: v033 CANONICAL ALIGNED",
        "run: pytest test_sprint_readiness.py test_dow_phases.py",
        "run: docker build .",
        "run: bandit -r .",
    ]
)
GOOD_CD = "\n".join(
    [
        "name: v033 CANONICAL ALIGNED",
        "uses: docker/build-push-action",
        "deploy staging then production",
        "Health check",
    ]
)
GOOD_SPRINT = {
    "version": "v033",
    "sprint_tested": True,
    "dow_tested": True,
    "canonical_aligned": True,
    "phases": ["Phase 8", "Phase 9"],
    "abacus_engines": {"v033": ENGINE},
}
DOCS = [
    "CANONICAL_ALIGNMENT_v032_v033.md",
    "ALIGNMENT_SUMMARY.md",
    "DEPLOYMENT_EXECUTION_SUMMARY.md",
]


def _validator(base):
    v = vc.CICDValidator()
    v.base_dir = base
    return v


def _write_all(base):
    (base / "Dockerfile").write_text(GOOD_DOCKERFILE, encoding="utf-8")
    (base / "docker-compose.yml").write_text(GOOD_COMPOSE, encoding="utf-8")
    wf = base / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_text(GOOD_CI, encoding="utf-8")
    (wf / "cd.yml").write_text(GOOD_CD, encoding="utf-8")
    (base / "sprint_config.json").write_text(json.dumps(GOOD_SPRINT), encoding="utf-8")
    for doc in DOCS:
        (base / doc).write_text("x", encoding="utf-8")


def _fake_run(returncode=0, stderr="", exc=None, calls=None):
    def fake(cmd, **kwargs):
        if calls is not None:
            calls.append((cmd, kwargs))
        if exc is not None:
            raise exc
        return types.SimpleNamespace(returncode=returncode, stderr=stderr, stdout="")

    return fake


def test_init_defaults():
    v = vc.CICDValidator()
    assert v.base_dir.name == "ABACUS-v032"
    assert v.results["overall"] == "PENDING"
    assert set(v.results) == {
        "docker",
        "cicd",
        "config",
        "alignment",
        "ports",
        "overall",
    }


def test_docker_config_missing_dockerfile(tmp_path):
    v = _validator(tmp_path)
    assert v.validate_docker_config() is False
    assert v.results["docker"]["dockerfile"] == "MISSING"


def test_docker_config_missing_compose(tmp_path):
    (tmp_path / "Dockerfile").write_text(GOOD_DOCKERFILE, encoding="utf-8")
    v = _validator(tmp_path)
    assert v.validate_docker_config() is False
    assert v.results["docker"]["compose"] == "MISSING"
    assert v.results["docker"]["v033_version"] is True


def test_docker_config_all_good(tmp_path):
    _write_all(tmp_path)
    v = _validator(tmp_path)
    assert v.validate_docker_config() is True
    assert v.results["docker"]["networks"] is True
    assert v.results["docker"]["ports_exposed"] is True


def test_docker_config_failing_checks(tmp_path):
    (tmp_path / "Dockerfile").write_text("FROM python", encoding="utf-8")
    (tmp_path / "docker-compose.yml").write_text("services: {}", encoding="utf-8")
    v = _validator(tmp_path)
    assert v.validate_docker_config() is False
    assert v.results["docker"]["dow_tested"] is False
    assert v.results["docker"]["grafana"] is False


def test_workflows_dir_missing(tmp_path):
    v = _validator(tmp_path)
    assert v.validate_cicd_workflows() is False
    assert v.results["cicd"]["workflows_dir"] == "MISSING"


def test_workflows_ci_missing(tmp_path):
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    v = _validator(tmp_path)
    assert v.validate_cicd_workflows() is False
    assert v.results["cicd"]["ci"] == "MISSING"


def test_workflows_cd_missing(tmp_path):
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_text("safety check", encoding="utf-8")
    v = _validator(tmp_path)
    assert v.validate_cicd_workflows() is False
    assert v.results["cicd"]["cd"] == "MISSING"
    assert v.results["cicd"]["ci_security_scan"] is True
    assert v.results["cicd"]["ci_v033_version"] is False


def test_workflows_all_good(tmp_path):
    _write_all(tmp_path)
    v = _validator(tmp_path)
    assert v.validate_cicd_workflows() is True
    assert v.results["cicd"]["cd_health_check"] is True
    assert v.results["cicd"]["ci_docker_build"] is True


def test_workflows_cd_checks_fail(tmp_path):
    _write_all(tmp_path)
    (tmp_path / ".github" / "workflows" / "cd.yml").write_text("x", encoding="utf-8")
    v = _validator(tmp_path)
    assert v.validate_cicd_workflows() is False
    assert v.results["cicd"]["cd_docker_push"] is False


def test_sprint_config_missing(tmp_path):
    v = _validator(tmp_path)
    assert v.validate_sprint_config() is False
    assert v.results["config"]["sprint_config"] == "MISSING"


def test_sprint_config_good(tmp_path):
    _write_all(tmp_path)
    v = _validator(tmp_path)
    assert v.validate_sprint_config() is True
    assert all(v.results["config"].values())


def test_sprint_config_bad(tmp_path):
    (tmp_path / "sprint_config.json").write_text(
        json.dumps({"version": "v032", "phases": ["Phase 1"]}), encoding="utf-8"
    )
    v = _validator(tmp_path)
    assert v.validate_sprint_config() is False
    assert v.results["config"]["version_v033"] is False
    assert v.results["config"]["phase_9_present"] is False
    assert v.results["config"]["v033_engine"] is False


def test_canonical_alignment_partial_and_full(tmp_path):
    v = _validator(tmp_path)
    (tmp_path / DOCS[0]).write_text("x", encoding="utf-8")
    assert v.validate_canonical_alignment() is False
    assert v.results["alignment"][DOCS[0]] == "PRESENT"
    assert v.results["alignment"][DOCS[1]] == "MISSING"
    for doc in DOCS:
        (tmp_path / doc).write_text("x", encoding="utf-8")
    v2 = _validator(tmp_path)
    assert v2.validate_canonical_alignment() is True


def test_ports_all_configured(tmp_path):
    _write_all(tmp_path)
    v = _validator(tmp_path)
    assert v.validate_ports() is True
    assert v.results["ports"] == {
        "8000": "CONFIGURED",
        "8080": "CONFIGURED",
        "9090": "CONFIGURED",
        "3000": "CONFIGURED",
    }


def test_ports_some_missing(tmp_path):
    (tmp_path / "docker-compose.yml").write_text("8000:8000", encoding="utf-8")
    v = _validator(tmp_path)
    assert v.validate_ports() is False
    assert v.results["ports"]["8000"] == "CONFIGURED"
    assert v.results["ports"]["3000"] == "MISSING"


def test_ports_without_compose_raises(tmp_path):
    v = _validator(tmp_path)
    with pytest.raises(FileNotFoundError):
        v.validate_ports()


def test_docker_build_success(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("subprocess.run", _fake_run(0, calls=calls))
    v = _validator(tmp_path)
    assert v.test_docker_build() is True
    assert v.results["docker"]["build_test"] == "VALID"
    cmd, kwargs = calls[0]
    assert cmd[:2] == ["docker", "build"]
    assert kwargs["cwd"] == tmp_path


def test_docker_build_dry_run_in_stderr(tmp_path, monkeypatch):
    monkeypatch.setattr("subprocess.run", _fake_run(1, "unknown flag: --DRY-RUN"))
    v = _validator(tmp_path)
    assert v.test_docker_build() is True


def test_docker_build_failure(tmp_path, monkeypatch):
    monkeypatch.setattr("subprocess.run", _fake_run(2, "boom"))
    v = _validator(tmp_path)
    assert v.test_docker_build() is False
    assert v.results["docker"]["build_test"] == "FAILED"


def test_docker_build_timeout(tmp_path, monkeypatch):
    exc = vc.subprocess.TimeoutExpired(cmd="docker", timeout=60)
    monkeypatch.setattr("subprocess.run", _fake_run(exc=exc))
    v = _validator(tmp_path)
    assert v.test_docker_build() is False
    assert v.results["docker"]["build_test"] == "TIMEOUT"


def test_docker_build_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr("subprocess.run", _fake_run(exc=FileNotFoundError("docker")))
    v = _validator(tmp_path)
    assert v.test_docker_build() is True
    assert v.results["docker"]["build_test"] == "DOCKER_NOT_FOUND"


def test_compose_config_success(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("subprocess.run", _fake_run(0, calls=calls))
    v = _validator(tmp_path)
    assert v.test_docker_compose_config() is True
    assert v.results["docker"]["compose_test"] == "VALID"
    assert calls[0][0] == ["docker-compose", "config"]


def test_compose_config_failure(tmp_path, monkeypatch):
    monkeypatch.setattr("subprocess.run", _fake_run(1, "bad yaml"))
    v = _validator(tmp_path)
    assert v.test_docker_compose_config() is False
    assert v.results["docker"]["compose_test"] == "FAILED"


def test_compose_config_timeout(tmp_path, monkeypatch):
    exc = vc.subprocess.TimeoutExpired(cmd="docker-compose", timeout=30)
    monkeypatch.setattr("subprocess.run", _fake_run(exc=exc))
    v = _validator(tmp_path)
    assert v.test_docker_compose_config() is False
    assert v.results["docker"]["compose_test"] == "TIMEOUT"


def test_compose_config_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr("subprocess.run", _fake_run(exc=FileNotFoundError("dc")))
    v = _validator(tmp_path)
    assert v.test_docker_compose_config() is True
    assert v.results["docker"]["compose_test"] == "DOCKER_COMPOSE_NOT_FOUND"


def test_generate_report_all_passed(tmp_path, capsys):
    v = _validator(tmp_path)
    v.results["docker"] = {"a": True, "build_test": "VALID"}
    v.results["alignment"] = {"doc": "PRESENT"}
    v.results["ports"] = {"8000": "CONFIGURED"}
    out = v.generate_report()
    assert out is v.results
    assert out["overall"] == "✅ ALL CHECKS PASSED"
    text = capsys.readouterr().out
    assert "DOCKER: 2/2 checks passed" in text
    assert "ALIGNMENT: 1/1 checks passed" in text


def test_generate_report_partial(tmp_path):
    v = _validator(tmp_path)
    v.results["docker"] = {"a": True, "b": False}
    assert "PARTIAL SUCCESS" in v.generate_report()["overall"]


def test_generate_report_failed(tmp_path):
    v = _validator(tmp_path)
    v.results["docker"] = {"a": False, "b": False}
    assert "VALIDATION FAILED" in v.generate_report()["overall"]


def test_save_report_writes_json(tmp_path):
    v = _validator(tmp_path)
    v.results["overall"] = "X"
    v.save_report()
    data = json.loads((tmp_path / "CICD_VALIDATION_REPORT.json").read_text())
    assert data["overall"] == "X"


def test_run_all_validations_success(tmp_path, monkeypatch):
    _write_all(tmp_path)
    monkeypatch.setattr("subprocess.run", _fake_run(0))
    v = _validator(tmp_path)
    assert v.run_all_validations() is True
    assert "ALL CHECKS PASSED" in v.results["overall"]
    saved = json.loads((tmp_path / "CICD_VALIDATION_REPORT.json").read_text())
    assert saved["docker"]["build_test"] == "VALID"


def test_run_all_validations_errors_are_caught(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("subprocess.run", _fake_run(exc=FileNotFoundError("docker")))
    v = _validator(tmp_path)
    assert v.run_all_validations() is False
    assert "Error in Port Configuration" in capsys.readouterr().out
    assert (tmp_path / "CICD_VALIDATION_REPORT.json").exists()


@pytest.mark.parametrize("ok,code", [(True, 0), (False, 1)])
def test_main_exit_code(monkeypatch, ok, code):
    monkeypatch.setattr(vc.CICDValidator, "run_all_validations", lambda self: ok)
    with pytest.raises(SystemExit) as exc:
        vc.main()
    assert exc.value.code == code
