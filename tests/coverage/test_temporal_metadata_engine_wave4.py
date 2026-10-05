from DMAIC_V3.core.temporal_metadata_engine import FileType, TemporalMetadataEngine


def _engine(tmp_path):
    return TemporalMetadataEngine(tmp_path, db_path=tmp_path / "metadata.db")


def test_file_type_mapping_skip_and_hash(tmp_path):
    engine = _engine(tmp_path)
    py = tmp_path / "sample.py"
    py.write_text("import json\n\ndef f():\n    return 1\n", encoding="utf-8")

    assert engine._determine_file_type(py) is FileType.PYTHON
    assert engine._determine_file_type(tmp_path / "README") is FileType.README
    assert engine._determine_file_type(tmp_path / "unknown.zzz") is FileType.OTHER
    assert engine._should_skip(tmp_path / ".git" / "config") is True
    assert engine._should_skip(py) is False
    assert len(engine._compute_file_hash(py)) == 64


def test_python_analysis_and_file_metadata(tmp_path):
    engine = _engine(tmp_path)
    py = tmp_path / "main.py"
    py.write_text(
        "import json\n"
        "from pathlib import Path\n"
        "class Example:\n"
        "    pass\n"
        "def helper():\n"
        "    return Path('.')\n",
        encoding="utf-8",
    )

    dependencies, imports, exports, functions, classes = engine._analyze_python_file(py)
    metadata = engine._extract_file_metadata(py)

    assert "json" in dependencies
    assert any(line.startswith("from pathlib") for line in imports)
    assert "helper" in functions
    assert "Example" in classes
    assert set(exports) == {"helper", "Example"}
    assert metadata.file_path == "main.py"
    assert metadata.is_main_entry is True
    assert metadata.file_type is FileType.PYTHON


def test_folder_purpose_counts_and_dependency_graph(tmp_path):
    engine = _engine(tmp_path)
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("import json\n", encoding="utf-8")

    folder = engine._extract_folder_metadata(src)
    file_meta = engine._extract_file_metadata(src / "a.py")

    assert folder.purpose == "Source Code"
    assert folder.is_source is True
    assert engine._count_file_types([file_meta]) == {"python": 1}
    assert engine._count_folder_purposes([folder]) == {"Source Code": 1}
    assert engine._build_dependency_graph([file_meta]) == {"src/a.py": ["json"]}


def test_scan_workspace_returns_file_and_folder_metadata(tmp_path):
    engine = _engine(tmp_path)
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("def hello():\n    return 1\n", encoding="utf-8")
    (tmp_path / "README").write_text("hello\n", encoding="utf-8")

    files, folders = engine.scan_workspace()

    assert any(item.file_path == "src/a.py" for item in files)
    assert any(item.folder_path == "src" for item in folders)

# Wave 5 exact-main broad coverage recensus trigger.
