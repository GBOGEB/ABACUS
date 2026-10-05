from __future__ import annotations

import json
from types import SimpleNamespace

from DMAIC_V3.phases.phase1_define import Phase1Define


def _phase(tmp_path):
    phase = object.__new__(Phase1Define)
    phase.config = SimpleNamespace(paths=SimpleNamespace(output_root=tmp_path))
    return phase


def test_calculate_artifact_ranking_reads_existing_json(tmp_path):
    phase = _phase(tmp_path)
    payload = {"total_ranked": 4, "items": [{"name": "a"}]}
    (tmp_path / "artifact_rankings.json").write_text(json.dumps(payload), encoding="utf-8")

    assert phase.calculate_artifact_ranking(7) == payload


def test_calculate_artifact_ranking_returns_none_when_missing(tmp_path):
    phase = _phase(tmp_path)

    assert phase.calculate_artifact_ranking(1) is None


def test_generate_define_book_ranking_yaml_and_analysis_report(tmp_path):
    phase = _phase(tmp_path)
    results = {
        "total_files": 10,
        "folders_scanned": 3,
        "categorized": {"Documentation": 3, "Code": 5, "Data": 1, "Notebooks": 1},
        "changes": {"added": 2, "modified": 1, "deleted": 1, "total": 4},
        "artifact_rankings": {"total_ranked": 2},
    }

    book = phase._generate_define_book(results, tmp_path, 2)
    ranking = phase._generate_ranking_yaml(results, tmp_path, 2)
    report = phase._generate_analysis_report(results, tmp_path, 2)

    book_text = book.read_text(encoding="utf-8")
    ranking_text = ranking.read_text(encoding="utf-8")
    report_text = report.read_text(encoding="utf-8")

    assert "DEFINE BOOK - Iteration 2" in book_text
    assert "Total Files Scanned:** 10" in book_text
    assert "top_30:" in ranking_text
    assert "artifact: placeholder_1" in ranking_text
    assert "Total files analyzed: 10" in report_text
    assert "**Code:** 5 (50.0%)" in report_text
