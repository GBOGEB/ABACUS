from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "repo_health" / "measure_source_generated_split.py"
spec = importlib.util.spec_from_file_location("measure_source_generated_split", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader and spec.name
sys.modules[spec.name] = module
spec.loader.exec_module(module)
assert sys.modules[spec.name] is module


def write(path: Path, text: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_classifier_separates_source_generated_binary_and_controls(tmp_path: Path) -> None:
    write(tmp_path / "src" / "model.py")
    write(tmp_path / "build" / "report.json")
    write(tmp_path / "governance" / "receipt.yaml")
    write(tmp_path / ".github" / "workflows" / "ci.yml")
    write(tmp_path / "dashboard_metrics.json")
    write(tmp_path / "tests" / "fixtures" / "case.yaml")
    (tmp_path / "release.xlsx").write_bytes(b"fake-binary")

    result = module.measure(tmp_path)

    counts = result["file_count_by_category"]
    assert counts["source_or_config"] == 1
    assert counts["generated_or_output"] == 1
    assert counts["governance_control"] == 1
    assert counts["ci_or_repository_control"] == 1
    assert counts["dashboard_or_metrics"] == 1
    assert counts["fixture_or_sample"] == 1
    assert counts["binary_or_office_artifact"] == 1


def test_measurement_preserves_zero_child_credit_boundary(tmp_path: Path) -> None:
    write(tmp_path / "src" / "model.py")
    result = module.measure(tmp_path)

    assert result["credit_boundary"] == {
        "qps_engineering_closure_credit": 0,
        "qps_negotiation_credit": 0,
        "child_compliance_credit": 0,
    }


def test_skip_dirs_are_not_counted(tmp_path: Path) -> None:
    write(tmp_path / ".git" / "objects" / "ignored")
    write(tmp_path / ".pytest_cache" / "ignored")
    write(tmp_path / "src" / "kept.py")

    result = module.measure(tmp_path)

    assert result["total_files"] == 1
    assert result["file_count_by_category"] == {"source_or_config": 1}
