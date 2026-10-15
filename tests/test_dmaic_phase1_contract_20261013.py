"""Phase 1 deterministic classification and progress-state contract tests."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from DMAIC_V3.phases.phase1_define import Phase1Define


@pytest.fixture
def phase(tmp_path: Path):
    config = SimpleNamespace(
        paths=SimpleNamespace(
            workspace_root=tmp_path,
            output_root=tmp_path / "outputs",
        )
    )
    return Phase1Define(config, state_manager=None)


@pytest.mark.parametrize(
    ("name", "category"),
    [
        ("engine.PY", "code"),
        ("control.ts", "code"),
        ("report.md", "docs"),
        ("input.xlsx", "data"),
        ("payload.yaml", "data"),
        ("noextension", "unknown"),
    ],
)
def test_file_type_classification(phase, name, category):
    assert phase.get_file_type(Path(name)) == category


@pytest.mark.parametrize(
    ("raw", "expected_code", "expected_docs"),
    [
        ({"categorized": {"code": 4, "docs": 2}}, 4, 2),
        ({"categorized": {"code": 4}, "code_files": 7}, 7, 0),
        ((True, {"categorized": {"code": 3, "docs": 8}}), 3, 8),
        ({"categorized": None}, 0, 0),
    ],
)
def test_normalize_execute_results(phase, raw, expected_code, expected_docs):
    result = phase._normalize_execute_results(raw)
    assert result["code_files"] == expected_code
    assert result["documentation_files"] == expected_docs
    # Normalization computes zero-based counters from an absent or non-map
    # categorized value; it intentionally preserves the original payload.
    expected_payload = raw[1] if isinstance(raw, tuple) else raw
    assert result["categorized"] == expected_payload.get("categorized")


def test_normalize_preserves_null_category_without_mutating_input(phase):
    raw = {"categorized": None, "extra": {"source": "control"}}
    result = phase._normalize_execute_results(raw)
    assert result["categorized"] is None
    assert result["code_files"] == 0
    assert result["documentation_files"] == 0
    assert result["extra"] == {"source": "control"}
    assert raw == {"categorized": None, "extra": {"source": "control"}}


@pytest.mark.parametrize("raw", [None, [], (True, {}), (False, "no")])
def test_normalize_rejects_unsupported_payload(phase, raw):
    if isinstance(raw, tuple) and raw == (True, {}):
        assert phase._normalize_execute_results(raw)["code_files"] == 0
    else:
        with pytest.raises(TypeError):
            phase._normalize_execute_results(raw)


def test_progress_roundtrip_and_cleanup(phase):
    assert phase.load_scan_progress() is None
    phase.save_scan_progress(2, "last.py", {"categorized": {"code": 2}})
    saved = json.loads(phase.scan_progress_file.read_text(encoding="utf-8"))
    assert saved["chunk_num"] == 2
    assert saved["last_path"] == "last.py"
    assert phase.load_scan_progress()["accumulated_data"] == {
        "categorized": {"code": 2}
    }
    phase.clear_scan_progress()
    assert not phase.scan_progress_file.exists()
    assert phase.load_scan_progress() is None
