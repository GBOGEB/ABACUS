import json
import sqlite3

import pytest

from DMAIC_V3.core.temporal_metadata_engine import (
    ExecutionMetadata,
    ExecutionPhase,
    FileType,
    TemporalMetadataEngine,
)


@pytest.fixture
def temporal_workspace(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "docs").mkdir()

    (tmp_path / "src" / "sample.py").write_text(
        "import json\n"
        "from pathlib import Path\n\n"
        "class Sample:\n"
        "    pass\n\n"
        "def compute(value):\n"
        "    return value + 1\n",
        encoding="utf-8",
    )
    (tmp_path / "README").write_text("# Sample workspace\n", encoding="utf-8")
    (tmp_path / "config.yaml").write_text("enabled: true\n", encoding="utf-8")
    (tmp_path / "docs" / "guide.md").write_text("# Guide\n", encoding="utf-8")
    return tmp_path


@pytest.mark.unit
def test_initialization_creates_database_schema_and_type_map(temporal_workspace):
    engine = TemporalMetadataEngine(temporal_workspace)

    assert engine.db_path.exists()
    assert engine.file_type_map[".py"] is FileType.PYTHON
    assert engine.file_type_map["README"] is FileType.README

    with sqlite3.connect(engine.db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

    assert {
        "file_metadata",
        "folder_metadata",
        "execution_metadata",
        "digital_twin_state",
        "bidirectional_links",
    }.issubset(tables)


@pytest.mark.unit
def test_file_type_hash_and_python_analysis_are_deterministic(temporal_workspace):
    engine = TemporalMetadataEngine(temporal_workspace)
    py_file = temporal_workspace / "src" / "sample.py"

    assert engine._determine_file_type(py_file) is FileType.PYTHON
    assert engine._determine_file_type(temporal_workspace / "config.yaml") is FileType.YAML
    assert engine._determine_file_type(temporal_workspace / "README") is FileType.README

    digest_a = engine._compute_file_hash(py_file)
    digest_b = engine._compute_file_hash(py_file)
    assert digest_a == digest_b
    assert len(digest_a) == 64

    dependencies, imports, exports, functions, classes = engine._analyze_python_file(py_file)
    assert {"json", "pathlib"}.issubset(set(dependencies))
    assert "import json" in imports
    assert "from pathlib import Path" in imports
    assert "compute" in functions
    assert "Sample" in classes
    assert {"compute", "Sample"}.issubset(set(exports))


@pytest.mark.unit
def test_scan_workspace_persists_file_and_folder_metadata(temporal_workspace):
    engine = TemporalMetadataEngine(temporal_workspace)

    files, folders = engine.scan_workspace()

    sample = next(item for item in files if item.file_path == "src/sample.py")
    assert sample.file_type is FileType.PYTHON
    assert sample.size_bytes > 0
    assert "compute" in sample.functions
    assert "Sample" in sample.classes

    src_folder = next(item for item in folders if item.folder_path == "src")
    tests_folder = next(item for item in folders if item.folder_path == "tests")
    assert src_folder.is_source is True
    assert src_folder.purpose == "Source Code"
    assert tests_folder.is_test is True
    assert tests_folder.purpose == "Test Suite"

    with sqlite3.connect(engine.db_path) as conn:
        file_row = conn.execute(
            "SELECT file_type, size_bytes FROM file_metadata WHERE file_path = ?",
            ("src/sample.py",),
        ).fetchone()
        folder_row = conn.execute(
            "SELECT purpose, is_source FROM folder_metadata WHERE folder_path = ?",
            ("src",),
        ).fetchone()

    assert file_row is not None
    assert file_row[0] == "python"
    assert file_row[1] > 0
    assert folder_row == ("Source Code", 1)


@pytest.mark.unit
def test_skip_and_folder_purpose_contract(temporal_workspace):
    engine = TemporalMetadataEngine(temporal_workspace)

    assert engine._should_skip(temporal_workspace / ".git" / "objects") is True
    assert engine._should_skip(temporal_workspace / "node_modules" / "pkg") is True
    assert engine._should_skip(temporal_workspace / "src" / "sample.py") is False

    assert engine._determine_folder_purpose(temporal_workspace / "docs") == "Documentation"
    assert engine._determine_folder_purpose(temporal_workspace / "src") == "Source Code"
    assert engine._determine_folder_purpose(temporal_workspace / "unknown") == "General Purpose"


@pytest.mark.unit
def test_record_execution_persists_provenance_and_metrics(temporal_workspace):
    engine = TemporalMetadataEngine(temporal_workspace)
    execution = ExecutionMetadata(
        execution_id="exec-001",
        timestamp="2026-09-26T12:00:00Z",
        phase=ExecutionPhase.MEASURE,
        iteration=2,
        input_files=["src/sample.py"],
        output_files=["report.json"],
        duration_seconds=1.25,
        status="success",
        metrics={"coverage": 25.04},
        logs=["started", "finished"],
        errors=[],
        warnings=["coverage below target"],
        provenance_chain=["source-sha", "exec-001"],
    )

    engine.record_execution(execution)

    with sqlite3.connect(engine.db_path) as conn:
        row = conn.execute(
            """
            SELECT phase, iteration, status, metrics, provenance_chain
            FROM execution_metadata
            WHERE execution_id = ?
            """,
            ("exec-001",),
        ).fetchone()

    assert row is not None
    assert row[0] == "measure"
    assert row[1] == 2
    assert row[2] == "success"
    assert json.loads(row[3]) == {"coverage": 25.04}
    assert json.loads(row[4]) == ["source-sha", "exec-001"]


@pytest.mark.unit
def test_create_digital_twin_persists_snapshot(temporal_workspace):
    engine = TemporalMetadataEngine(temporal_workspace)

    twin = engine.create_digital_twin()

    assert twin.source_workspace == str(temporal_workspace)
    assert twin.file_count >= 4
    assert twin.folder_count >= 3
    assert twin.total_size_bytes > 0
    assert 0.0 <= twin.quality_metrics["python_file_ratio"] <= 1.0

    with sqlite3.connect(engine.db_path) as conn:
        row = conn.execute(
            """
            SELECT source_workspace, file_count, folder_count, total_size_bytes
            FROM digital_twin_state
            WHERE twin_id = ?
            """,
            (twin.twin_id,),
        ).fetchone()

    assert row is not None
    assert row[0] == str(temporal_workspace)
    assert row[1] == twin.file_count
    assert row[2] == twin.folder_count
    assert row[3] == twin.total_size_bytes


@pytest.mark.unit
def test_hierarchy_report_contains_counts_and_dependency_graph(temporal_workspace):
    engine = TemporalMetadataEngine(temporal_workspace)
    output = temporal_workspace / "out" / "hierarchy.json"

    report = engine.generate_hierarchy_report(output)

    assert output.exists()
    assert report["summary"]["total_files"] >= 4
    assert report["summary"]["total_folders"] >= 3
    assert report["summary"]["file_types"]["python"] >= 1
    assert report["summary"]["folder_purposes"]["Source Code"] >= 1
    assert "src/sample.py" in report["dependency_graph"]
    assert {"json", "pathlib"}.issubset(set(report["dependency_graph"]["src/sample.py"]))

    persisted = json.loads(output.read_text(encoding="utf-8"))
    assert persisted["workspace_root"] == str(temporal_workspace)
    assert persisted["summary"]["total_files"] == report["summary"]["total_files"]
