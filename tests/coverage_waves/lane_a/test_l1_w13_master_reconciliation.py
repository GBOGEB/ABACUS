"""Lane A wave 13: DMAIC_V3.generators.master_reconciliation in a sandbox root."""

import json
from pathlib import Path

import pytest

from DMAIC_V3.generators import master_reconciliation as mr


@pytest.fixture
def system(tmp_path):
    (tmp_path / "master_document_system").mkdir()
    return mr.MasterReconciliationSystem(tmp_path)


def _docs(system):
    return system.master_doc_dir


def test_init_paths(system, tmp_path):
    assert system.master_doc_dir == tmp_path / "master_document_system"
    assert system.output_dir == tmp_path / "output"
    assert system.version == "3.1.0"
    assert len(system.timestamp) == 15


def test_log_records_and_prints(system, capsys):
    system.log("hello", "WARN")
    assert system.reconciliation_log[-1].endswith("[WARN] hello")
    assert "[WARN] hello" in capsys.readouterr().out


def test_fix_python_unicode_errors(system):
    docs = _docs(system)
    (docs / "arrows.py").write_bytes("x = 'a → b ← c ↔'\n".encode())
    (docs / "plain.py").write_bytes(b"x = 1\n")
    (docs / "broken.py").write_bytes(b"\xff\xfe\x00bad")
    fixed = system.fix_python_unicode_errors()
    assert fixed == 1
    fixed_text = (docs / "arrows.py").read_text(encoding="utf-8")
    assert fixed_text.strip() == "x = 'a -> b <- c <->'"
    log = "\n".join(system.reconciliation_log)
    assert "[SUCCESS]   Fixed: arrows.py" in log
    assert "No changes needed: plain.py" in log
    assert "[ERROR]   Error fixing broken.py" in log
    assert "Fixed 1/3 Python files" in log


def test_generate_dmaic_metrics_per_phase(system):
    phases = system.generate_dmaic_metrics_per_phase()
    assert list(phases) == ["DEFINE", "MEASURE", "ANALYZE", "IMPROVE", "CONTROL"]
    metrics_dir = system.output_dir / "dmaic_metrics"
    files = sorted(p.name for p in metrics_dir.glob("*.json"))
    assert len(files) == 6
    define = next(metrics_dir.glob("DMAIC_DEFINE_*.json"))
    data = json.loads(define.read_text(encoding="utf-8"))
    assert data["metadata"]["phase_number"] == 0
    assert data["status"] == "INITIALIZED"
    summary = json.loads(
        next(metrics_dir.glob("DMAIC_SUMMARY_*.json")).read_text(encoding="utf-8")
    )
    assert summary["overall_status"] == "IN_PROGRESS"
    assert set(summary["phases"]) == set(phases)


def test_reconcile_markdown_files_idempotent_header(system):
    docs = _docs(system)
    (docs / "README.md").write_bytes(b"# Readme\nbody\n")
    (docs / "INTEGRATION_PLAN.md").write_bytes(b"\xff\xfe bad")
    assert system.reconcile_markdown_files() == 1
    assert system.reconcile_markdown_files() == 1
    text = (docs / "README.md").read_text(encoding="utf-8")
    assert text.count("<!-- DMAIC V3 RECONCILIATION -->") == 1
    assert text.endswith("# Readme\nbody\n")
    assert "<!-- Status: RECONCILED -->" in text
    log = "\n".join(system.reconciliation_log)
    assert "Skipping (not found): DEPLOYMENT_COMPLETE.md" in log
    assert "Error reconciling INTEGRATION_PLAN.md" in log
    assert "Reconciled 1/4 markdown files" in log


def test_markdown_as_code_and_index(system):
    mac = system.create_markdown_as_code()
    assert mac.parent == _docs(system)
    assert mac.name.startswith("MARKDOWN_AS_CODE_master_document_handler_V3_")
    assert "## ASCII INSTRUCTION SET" in mac.read_text(encoding="utf-8")
    index = system.create_index_and_helpers()
    content = index.read_text(encoding="utf-8")
    assert index.name.startswith("INDEX_master_document_handler_V3_")
    assert f"MARKDOWN_AS_CODE_master_document_handler_V3_{system.timestamp}.md" in (
        content
    )


def test_update_victory_conditions(system):
    vc = system.update_victory_conditions()
    assert len(vc["conditions"]) == 8
    overall = vc["overall_status"]
    assert overall["completed"] + overall["in_progress"] == overall["total_conditions"]
    files = list((system.output_dir / "victory_conditions").glob("*.json"))
    assert len(files) == 1
    assert json.loads(files[0].read_text(encoding="utf-8")) == vc
    assert "Overall Status: 62.5% complete" in system.reconciliation_log[-1]


def test_generate_final_report_includes_log(system):
    system.log("earlier step")
    report = system.generate_final_report()
    assert report["metadata"]["report_type"] == "MASTER_RECONCILIATION"
    assert any("earlier step" in e for e in report["reconciliation_log"])
    files = list((system.output_dir / "reconciliation").glob("*.json"))
    assert len(files) == 1


def test_run_full_reconciliation(system, capsys):
    (_docs(system) / "README.md").write_bytes(b"hi\n")
    system.run_full_reconciliation()
    out = system.output_dir
    assert list((out / "dmaic_metrics").glob("*.json"))
    assert list((out / "victory_conditions").glob("*.json"))
    assert list((out / "reconciliation").glob("*.json"))
    assert list(_docs(system).glob("INDEX_*.md"))
    assert "RECONCILIATION COMPLETE" in capsys.readouterr().out


def test_main_targets_repo_root(monkeypatch):
    seen = []

    def fake_run(self):
        seen.append(self.root_dir)

    monkeypatch.setattr(
        mr.MasterReconciliationSystem, "run_full_reconciliation", fake_run
    )
    assert mr.main() == 0
    assert seen == [Path(mr.__file__).parent.parent.parent]
