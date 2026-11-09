"""Behaviour tests for abacus_v21_migration_test_comprehensive.py.

The production module defines its own ``unittest.TestCase``. It is loaded under
a non-test module name and the class is only ever reached through ``suite_mod``
inside test functions, so pytest never collects it from this namespace.
"""

import json
import runpy

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

suite_mod = load(
    "abacus_v21_migration_test_comprehensive.py", name="abn_w2_migration_suite"
)

TEMPORAL_SRC = (
    "import datetime\n"
    "class FileMetadata:\n    created_at = modified_at = None\n"
    "class DigitalTwinState:\n    timestamp = None\n"
)
DOW_SRC = "ABACUS-UNIFIED ABACUS-v031 orchestrate deploy\n"
DOCS = (
    "ABACUS_SPRINT_COMPLETION_SUMMARY.md",
    "ABACUS_INDEXING_SUMMARY.md",
    "ABACUS_VERSION_CONSOLIDATION_FINAL_REPORT.md",
    "ABACUS_VERSION_CONSOLIDATION_TRACEABILITY.md",
    "ABACUS_QUICK_REFERENCE.md",
)
PHASE_KEYS = ["phase_%d" % i for i in range(1, 9)]


def _populate(root):
    core = root / "DMAIC_V3" / "core"
    core.mkdir(parents=True)
    (core / "recursive_engine.py").write_bytes(b"def r():\n    return r\n")
    (core / "temporal_metadata_engine.py").write_bytes(TEMPORAL_SRC.encode())
    (root / "DOW_DEPLOYMENT_ORCHESTRATOR.py").write_bytes(DOW_SRC.encode())
    for version in ("ABACUS-UNIFIED", "ABACUS-v031", "ABACUS-v032"):
        vdir = root / version
        vdir.mkdir()
        (vdir / "plain.py").write_bytes(b"x = 1\n")
        (vdir / "notes.md").write_bytes(b"# notes\n")
    (root / "ABACUS-v031" / "old.py").write_bytes(b"# Deprecated helper\n")
    (root / "ABACUS-v032" / "new.py").write_bytes(b"# Enhanced pipeline\n")
    (root / "ABACUS-v032" / "recursive_engine").mkdir()
    (root / "ABACUS_SPRINT_COMPLETION_SUMMARY.md").write_bytes(b"Release v2.1\n")
    (root / "ABACUS_INDEXING_SUMMARY.md").write_bytes(b"older index\n")
    (root / "ABACUS_VERSION_CONSOLIDATION_TRACEABILITY.md").write_bytes(
        b"UNIFIED v031 v031 migration\n"
    )


def _case(root, monkeypatch, method):
    """Run setUpClass with cwd=root and return a case bound to ``method``."""
    monkeypatch.chdir(root)
    cls = suite_mod.ABACUSv21MigrationTest
    cls.setUpClass()
    return cls(method)


def _phase(case, key):
    return case.migration_results["phases"][key]


def test_constants():
    assert suite_mod.KnowledgeStatus.DEPRECATED == "deprecated"
    assert suite_mod.MigrationPhase.PHASE_8_DEPLOYMENT_VALIDATION.startswith("Phase 8")


def test_setupclass_initialises_results(tmp_path, monkeypatch, capsys):
    case = _case(tmp_path, monkeypatch, "test_01_recursive_engine_integration")
    assert case.workspace_root == tmp_path
    assert (tmp_path / "ABACUS_V21_MIGRATION_OUTPUT").is_dir()
    assert case.migration_results["version"] == "2.1"
    assert case.migration_results["phases"] == {}
    assert "COMPREHENSIVE MIGRATION TEST SUITE" in capsys.readouterr().out


def test_phase1_passes_with_components(tmp_path, monkeypatch, capsys):
    _populate(tmp_path)
    case = _case(tmp_path, monkeypatch, "test_01_recursive_engine_integration")
    case.test_01_recursive_engine_integration()
    checks = _phase(case, "phase_1")["checks"]
    assert checks["DMAIC_V3/core/recursive_engine.py"]["type"] == "file"
    assert checks["DMAIC_V3/core/recursive_engine.py"]["lines"] == 2
    assert checks["ABACUS-v032/recursive_engine"]["type"] == "directory"
    quick = "CRYO_LINAC_HANDOVER_v2.1.0_20251103_020746/RECURSIVE_ENGINE_QUICK_START.md"
    assert checks[quick] == {"exists": False, "type": "missing"}
    out = capsys.readouterr().out
    assert "Found: DMAIC_V3/core/recursive_engine.py" in out
    assert "Missing: CRYO_LINAC_HANDOVER" in out


def test_phase1_fails_on_empty_workspace(tmp_path, monkeypatch):
    case = _case(tmp_path, monkeypatch, "test_01_recursive_engine_integration")
    with pytest.raises(AssertionError, match="recursive engine component"):
        case.test_01_recursive_engine_integration()
    assert _phase(case, "phase_1")["status"] == "completed"


def test_phase2_counts_date_tracking(tmp_path, monkeypatch, capsys):
    _populate(tmp_path)
    case = _case(tmp_path, monkeypatch, "test_02_temporal_engine_validation")
    case.test_02_temporal_engine_validation()
    res = _phase(case, "phase_2")
    assert res["temporal_engine_found"] is True
    assert res["date_tracking"] == {
        "datetime": 1,
        "timestamp": 1,
        "created_at": 1,
        "modified_at": 1,
        "accessed_at": 0,
    }
    assert res["metadata_validation"] == {
        "FileMetadata": True,
        "FolderMetadata": False,
        "ExecutionMetadata": False,
        "DigitalTwinState": True,
    }
    assert "Metadata class: DigitalTwinState" in capsys.readouterr().out


def test_phase2_fails_without_engine(tmp_path, monkeypatch, capsys):
    case = _case(tmp_path, monkeypatch, "test_02_temporal_engine_validation")
    with pytest.raises(AssertionError, match="Temporal engine must exist"):
        case.test_02_temporal_engine_validation()
    assert "Temporal engine not found" in capsys.readouterr().out


def test_phase2_fails_when_engine_has_no_dates(tmp_path, monkeypatch):
    core = tmp_path / "DMAIC_V3" / "core"
    core.mkdir(parents=True)
    (core / "temporal_metadata_engine.py").write_bytes(b"pass\n")
    case = _case(tmp_path, monkeypatch, "test_02_temporal_engine_validation")
    with pytest.raises(AssertionError, match="date tracking"):
        case.test_02_temporal_engine_validation()


def test_phase3_integration_points(tmp_path, monkeypatch):
    _populate(tmp_path)
    case = _case(tmp_path, monkeypatch, "test_03_dow_integration_validation")
    case.test_03_dow_integration_validation()
    res = _phase(case, "phase_3")
    assert res["dow_orchestrator"] == {"found": True}
    assert res["integration_points"] == {
        "ABACUS-UNIFIED": True,
        "ABACUS-v031": True,
        "ABACUS-v032": False,
        "orchestrate": True,
        "deploy": True,
    }


def test_phase3_fails_without_orchestrator(tmp_path, monkeypatch):
    case = _case(tmp_path, monkeypatch, "test_03_dow_integration_validation")
    with pytest.raises(AssertionError, match="DOW orchestrator must exist"):
        case.test_03_dow_integration_validation()
    assert _phase(case, "phase_3")["dow_orchestrator"] == {"found": False}


def test_phase4_tracks_status_markers(tmp_path, monkeypatch, capsys):
    _populate(tmp_path)
    # a directory matching *.py makes open() fail; the suite must swallow it
    (tmp_path / "ABACUS-UNIFIED" / "pkg.py").mkdir()
    case = _case(tmp_path, monkeypatch, "test_04_knowledge_preservation_tracking")
    case.test_04_knowledge_preservation_tracking()
    res = _phase(case, "phase_4")
    tracking = res["status_tracking"]
    assert tracking["active"] == ["ABACUS-UNIFIED", "ABACUS-v031", "ABACUS-v032"]
    assert [p.replace("\\", "/") for p in tracking["deprecated"]] == [
        "ABACUS-v031/old.py"
    ]
    assert [p.replace("\\", "/") for p in tracking["improved"]] == [
        "ABACUS-v032/new.py"
    ]
    assert res["knowledge_items"]["ABACUS-UNIFIED"]["python_files"] == 2
    assert res["knowledge_items"]["ABACUS-v031"]["total_knowledge_artifacts"] == 3
    assert "Total knowledge artifacts tracked: 9" in capsys.readouterr().out


def test_phase4_fails_without_artifacts(tmp_path, monkeypatch, capsys):
    case = _case(tmp_path, monkeypatch, "test_04_knowledge_preservation_tracking")
    with pytest.raises(AssertionError, match="knowledge artifacts"):
        case.test_04_knowledge_preservation_tracking()
    assert "ABACUS-v031 not found" in capsys.readouterr().out


def test_phase5_documentation_alignment(tmp_path, monkeypatch, capsys):
    _populate(tmp_path)
    case = _case(tmp_path, monkeypatch, "test_05_documentation_alignment")
    case.test_05_documentation_alignment()
    docs = _phase(case, "phase_5")["required_docs"]
    assert docs[DOCS[0]]["v21_aligned"] is True
    assert docs[DOCS[1]]["v21_aligned"] is False
    assert docs[DOCS[1]]["lines"] == 1
    assert docs[DOCS[2]]["exists"] is False
    assert docs[DOCS[4]]["exists"] is False
    out = capsys.readouterr().out
    assert "v2.1 alignment confirmed" in out
    assert "Documentation missing: ABACUS_QUICK_REFERENCE.md" in out


def test_phase5_fails_without_docs(tmp_path, monkeypatch):
    case = _case(tmp_path, monkeypatch, "test_05_documentation_alignment")
    with pytest.raises(AssertionError, match="required document"):
        case.test_05_documentation_alignment()


def test_phase6_traceability(tmp_path, monkeypatch):
    _populate(tmp_path)
    case = _case(tmp_path, monkeypatch, "test_06_traceability_matrix_validation")
    case.test_06_traceability_matrix_validation()
    res = _phase(case, "phase_6")
    assert res["traceability_file"] == {"found": True}
    assert res["version_mapping"]["v031"] == 2
    assert res["version_mapping"]["v2.1"] == 0
    assert res["version_mapping"]["consolidation"] == 0


def test_phase6_fails_without_matrix(tmp_path, monkeypatch, capsys):
    case = _case(tmp_path, monkeypatch, "test_06_traceability_matrix_validation")
    with pytest.raises(AssertionError, match="Traceability information"):
        case.test_06_traceability_matrix_validation()
    assert "Traceability matrix not found" in capsys.readouterr().out


def test_phase7_consolidation(tmp_path, monkeypatch):
    _populate(tmp_path)
    case = _case(tmp_path, monkeypatch, "test_07_version_consolidation_validation")
    case.test_07_version_consolidation_validation()
    res = _phase(case, "phase_7")
    assert res["versions"]["ABACUS-v031"]["actual_files"] == 2
    assert res["versions"]["ABACUS-v031"]["expected_files"] == 43
    assert res["consolidation_status"] == {
        "total_versions": 3,
        "found_versions": 3,
        "consolidation_complete": True,
    }


def test_phase7_fails_with_one_version(tmp_path, monkeypatch):
    (tmp_path / "ABACUS-v032").mkdir()
    case = _case(tmp_path, monkeypatch, "test_07_version_consolidation_validation")
    with pytest.raises(AssertionError, match="At least 2 versions"):
        case.test_07_version_consolidation_validation()
    res = _phase(case, "phase_7")
    assert res["versions"]["ABACUS-UNIFIED"] == {"exists": False, "status": "missing"}
    assert res["consolidation_status"]["consolidation_complete"] is False


@pytest.mark.parametrize(
    "completed, score, verdict",
    [
        (7, 100.0, "DEPLOYMENT APPROVED"),
        (5, 500 / 7, "DEPLOYMENT CONDITIONAL"),
    ],
)
def test_phase8_readiness_bands(
    tmp_path, monkeypatch, capsys, completed, score, verdict
):
    case = _case(tmp_path, monkeypatch, "test_08_deployment_validation")
    for key in PHASE_KEYS[:completed]:
        case.migration_results["phases"][key] = {"status": "completed"}
    case.test_08_deployment_validation()
    res = _phase(case, "phase_8")
    assert res["readiness_score"] == pytest.approx(score)
    assert sum(res["deployment_checks"].values()) == completed
    assert verdict in capsys.readouterr().out


def test_phase8_blocks_below_sixty(tmp_path, monkeypatch, capsys):
    case = _case(tmp_path, monkeypatch, "test_08_deployment_validation")
    case.migration_results["phases"]["phase_1"] = {"status": "completed"}
    case.migration_results["phases"]["phase_2"] = {"status": "in_progress"}
    with pytest.raises(AssertionError, match="at least 60%"):
        case.test_08_deployment_validation()
    out = capsys.readouterr().out
    assert "DEPLOYMENT BLOCKED" in out
    assert "Recursive Engine: PASS" in out
    assert "Temporal Engine: FAIL" in out


def test_teardown_writes_reports_in_progress(tmp_path, monkeypatch, capsys):
    cls = _case(tmp_path, monkeypatch, "test_08_deployment_validation").__class__
    cls.migration_results["phases"]["phase_1"] = {"status": "completed"}
    cls.migration_results["phases"]["phase_2"] = {"status": "in_progress"}
    cls.migration_results["phases"]["phase_8"] = {
        "status": "completed",
        "readiness_score": 71.4286,
    }
    cls.tearDownClass()
    out_dir = tmp_path / "ABACUS_V21_MIGRATION_OUTPUT"
    data = json.loads(
        (out_dir / "ABACUS_V21_MIGRATION_REPORT.json").read_text(encoding="utf-8")
    )
    assert data["summary"]["total_phases"] == 3
    assert data["summary"]["completed_phases"] == 2
    md = (out_dir / "ABACUS_V21_MIGRATION_REPORT.md").read_text(encoding="utf-8")
    assert "**Status:** ⚠️ IN PROGRESS" in md
    assert "**Status:** ⚠️ IN_PROGRESS" in md
    assert "**Status:** ❌ NOT_STARTED" in md
    assert "**Deployment Readiness Score:** 71.4%" in md
    out = capsys.readouterr().out
    assert "Total Phases: 3" in out
    assert "Completed: 2" in out


def test_markdown_report_all_completed(tmp_path, monkeypatch):
    cls = _case(tmp_path, monkeypatch, "test_08_deployment_validation").__class__
    for key in PHASE_KEYS[:7]:
        cls.migration_results["phases"][key] = {"status": "completed"}
    cls.migration_results["phases"]["phase_8"] = {"status": "completed"}
    cls.migration_results["summary"] = {"completed_phases": 8, "total_phases": 8}
    md = cls._generate_markdown_report()
    assert "**Status:** ✅ COMPLETED" in md
    assert "IN PROGRESS" not in md
    assert "Deployment Readiness Score" not in md
    assert md.count("**Status:** ✅ COMPLETED") == 9


def test_main_succeeds_on_populated_workspace(tmp_path, monkeypatch, capsys):
    _populate(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert suite_mod.main() == 0
    captured = capsys.readouterr()
    assert "Ran 8 tests" in captured.err
    assert "OK" in captured.err
    report = (
        tmp_path / "ABACUS_V21_MIGRATION_OUTPUT" / "ABACUS_V21_MIGRATION_REPORT.json"
    )
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["summary"]["completed_phases"] == 8
    assert data["phases"]["phase_8"]["readiness_score"] == 100.0


def test_main_fails_on_empty_workspace(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert suite_mod.main() == 1
    assert "FAILED (failures=" in capsys.readouterr().err


def test_main_block_exits_with_suite_result(tmp_path, monkeypatch, capsys):
    _populate(tmp_path)
    monkeypatch.chdir(tmp_path)
    path = str(REPO_ROOT / "abacus_v21_migration_test_comprehensive.py")
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(path, run_name="__main__")
    assert exc.value.code == 0
    assert "Ran 8 tests" in capsys.readouterr().err
