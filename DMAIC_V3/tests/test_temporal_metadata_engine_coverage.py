import hashlib
import json
import sqlite3
from pathlib import Path

from DMAIC_V3.core.temporal_metadata_engine import (
    ExecutionMetadata,
    ExecutionPhase,
    FileType,
    TemporalMetadataEngine,
)


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "main.py").write_text(
        "import json\nfrom pathlib import Path\n\nclass Runner:\n    pass\n\ndef run():\n    return Path('.')\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    (tmp_path / "src" / "helper.py").write_text("def helper():\n    return 1\n", encoding="utf-8")
    (tmp_path / "tests" / "test_sample.py").write_text("def test_sample():\n    assert True\n", encoding="utf-8")
    return tmp_path


def test_temporal_engine_scans_classifies_and_persists(tmp_path):
    root = _workspace(tmp_path)
    db_path = root / ".dmaic" / "metadata.db"
    engine = TemporalMetadataEngine(root, db_path=db_path)

    assert db_path.exists()
    assert engine._determine_file_type(root / "main.py") == FileType.PYTHON
    assert engine._determine_file_type(root / "README.md") == FileType.MARKDOWN
    assert engine._determine_file_type(root / "unknown.bin") == FileType.OTHER
    assert engine._determine_folder_purpose(root / "tests") == "Test Suite"
    assert engine._determine_folder_purpose(root / "src") == "Source Code"
    assert engine._should_skip(root / ".git" / "objects") is True

    metadata = engine._extract_file_metadata(root / "main.py")
    assert metadata.is_main_entry is True
    assert metadata.file_type == FileType.PYTHON
    assert "run" in metadata.functions
    assert "Runner" in metadata.classes
    expected_hash = hashlib.sha256((root / "main.py").read_bytes()).hexdigest()
    assert metadata.hash_sha256 == expected_hash

    files, folders = engine.scan_workspace()
    assert any(f.file_path == "main.py" for f in files)
    assert any(f.file_type == FileType.PYTHON for f in files)
    assert any(folder.folder_path == "tests" and folder.is_test for folder in folders)

    with sqlite3.connect(db_path) as conn:
        assert conn.execute("select count(*) from file_metadata").fetchone()[0] > 0
        assert conn.execute("select count(*) from folder_metadata").fetchone()[0] > 0


def test_temporal_engine_execution_twin_and_report(tmp_path):
    root = _workspace(tmp_path)
    db_path = root / ".dmaic" / "metadata.db"
    engine = TemporalMetadataEngine(root, db_path=db_path)

    execution = ExecutionMetadata(
        execution_id="exec-1",
        timestamp="2026-09-26T12:00:00",
        phase=ExecutionPhase.MEASURE,
        iteration=1,
        input_files=["main.py"],
        output_files=["report.json"],
        duration_seconds=1.5,
        status="success",
        metrics={"files": 3},
        logs=["ok"],
        errors=[],
        warnings=[],
        provenance_chain=["main.py"],
    )
    engine.record_execution(execution)

    twin = engine.create_digital_twin()
    assert twin.file_count > 0
    assert twin.folder_count > 0
    assert twin.total_size_bytes > 0
    assert 0.0 <= twin.quality_metrics["python_file_ratio"] <= 1.0

    report_path = root / "reports" / "hierarchy.json"
    report = engine.generate_hierarchy_report(report_path)
    assert report_path.exists()
    assert report["summary"]["total_files"] > 0
    assert report["main_entry_points"] == ["main.py"]
    assert report["summary"]["file_types"]["python"] >= 2
    assert report["dependency_graph"]["main.py"]
    assert json.loads(report_path.read_text())["workspace_root"] == str(root)

    with sqlite3.connect(db_path) as conn:
        assert conn.execute("select status from execution_metadata where execution_id='exec-1'").fetchone()[0] == "success"
        assert conn.execute("select count(*) from digital_twin_state").fetchone()[0] == 1


def test_temporal_engine_count_helpers_and_error_paths(tmp_path, monkeypatch):
    root = _workspace(tmp_path)
    engine = TemporalMetadataEngine(root, db_path=root / ".dmaic" / "metadata.db")
    files, folders = engine.scan_workspace()

    file_counts = engine._count_file_types(files)
    folder_counts = engine._count_folder_purposes(folders)
    graph = engine._build_dependency_graph(files)

    assert file_counts["python"] >= 2
    assert folder_counts["Test Suite"] >= 1
    assert "main.py" in graph

    missing = root / "missing.py"
    assert engine._compute_file_hash(missing) == "error_computing_hash"
    assert engine._analyze_python_file(missing) == ([], [], [], [], [])
