from types import SimpleNamespace

import pytest

from DMAIC_V3.phases.phase1_define import Phase1Define


def _phase(tmp_path):
    phase = object.__new__(Phase1Define)
    phase.file_type_map = {".py": "code", ".md": "docs", ".json": "data"}
    phase.scan_progress_file = tmp_path / "state" / "scan_progress.json"
    return phase


def test_file_type_and_execute_result_normalization(tmp_path):
    phase = _phase(tmp_path)

    assert phase.get_file_type(tmp_path / "x.PY") == "code"
    assert phase.get_file_type(tmp_path / "README.md") == "docs"
    assert phase.get_file_type(tmp_path / "x.bin") == "unknown"

    direct = phase._normalize_execute_results({"categorized": {"code": 2, "docs": 3}})
    tupled = phase._normalize_execute_results((True, {"code_files": 7}))

    assert direct["code_files"] == 2
    assert direct["documentation_files"] == 3
    assert tupled["code_files"] == 7
    assert tupled["documentation_files"] == 0

    with pytest.raises(TypeError):
        phase._normalize_execute_results(["unexpected"])


def test_scan_progress_round_trip_and_clear(tmp_path):
    phase = _phase(tmp_path)
    payload = {"all_files": ["a.py"], "categorized": {"code": 1}}

    phase.save_scan_progress(3, "a.py", payload)
    loaded = phase.load_scan_progress()

    assert loaded["chunk_num"] == 3
    assert loaded["last_path"] == "a.py"
    assert loaded["accumulated_data"] == payload

    phase.clear_scan_progress()
    assert phase.load_scan_progress() is None
