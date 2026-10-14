"""Guard the DOW workflow-to-SUT source contract without faking green."""
import json
from pathlib import Path

from scripts.dow_ci_contract_census import (
    EXPECTED_OUTPUTS,
    SOURCES,
    _source_state,
    census,
    main,
)


def test_missing_dow_sources_remain_explicitly_blocking(tmp_path: Path) -> None:
    receipt = census(tmp_path)
    assert receipt["source_census_state"] == "SOURCE_BLOCKED"
    assert set(receipt["blocking_sources"]) == {"phase2", "phase3"}
    assert receipt["merge_admission"] == "HOLD"
    assert receipt["phase2_executed"] is None
    assert receipt["nonempty_artifacts_verified"] is None


def test_present_stubs_are_not_runtime_or_output_proof(tmp_path: Path) -> None:
    for spec in SOURCES.values():
        (tmp_path / spec["path"]).write_text("print('stub')\n", encoding="utf-8")
    receipt = census(tmp_path)
    assert receipt["source_census_state"] == "SOURCES_PRESENT_UNVERIFIED"
    assert not receipt["blocking_sources"]
    assert receipt["phase3_executed"] is None
    assert receipt["metadata_semantics_verified"] is None
    assert receipt["merge_admission"] == "HOLD"


def test_source_parsing_failure_does_not_become_green(tmp_path: Path) -> None:
    (tmp_path / "invalid.py").write_text("def x(\n", encoding="utf-8")
    assert _source_state(tmp_path, "invalid.py")["state"] == "UNPARSEABLE_SOURCE"
    assert _source_state(tmp_path, "../invalid.py")["state"] == "INVALID_PATH"
    assert _source_state(tmp_path, "/tmp/invalid.py")["state"] == "INVALID_PATH"


def test_cli_report_only_and_required_source_exit_code(tmp_path: Path) -> None:
    output = tmp_path / "receipt.json"
    assert main(["--root", str(tmp_path), "--output", str(output)]) == 0
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["source_census_state"] == "SOURCE_BLOCKED"
    assert main(["--root", str(tmp_path), "--require-sources"]) == 2


def test_declared_workflow_inputs_and_outputs_are_retained() -> None:
    assert SOURCES["phase2"]["invocation"][-6:] == [
        "--dow-root", "dow_output", "--alpha", "0.05", "--mode", "csv",
    ]
    assert "dow_output/**/phase2_metadata.json" in EXPECTED_OUTPUTS["phase2"]
    assert SOURCES["phase3"]["invocation"][-2:] == [
        "--phase2-metadata", "<phase2_metadata_path>",
    ]
    assert "phase3_reports/**/*" in EXPECTED_OUTPUTS["upload_patterns"]
