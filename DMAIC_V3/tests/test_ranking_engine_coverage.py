import json
import sqlite3

import pytest

from DMAIC_V3.core.ranking_engine import (
    RankingCategory,
    RankingEngine,
    RankingScore,
)


@pytest.mark.unit
def test_weighted_score_uses_score_weight_and_confidence():
    score = RankingScore(
        category=RankingCategory.QUALITY.value,
        score=0.8,
        weight=0.5,
        confidence=0.75,
        evidence={"source": "test"},
        timestamp="2026-09-26T00:00:00",
    )

    assert score.weighted_score() == pytest.approx(0.3)


@pytest.mark.unit
def test_self_ranking_persists_score_strengths_and_recommendations(tmp_path):
    engine = RankingEngine(tmp_path)
    entity = tmp_path / "core" / "worker.py"
    entity.parent.mkdir()
    entity.write_text("pass\n", encoding="utf-8")

    ranking = engine.calculate_self_ranking(
        entity,
        {
            "quality_score": 0.9,
            "complexity": 0.2,
            "test_coverage": 0.85,
            "doc_coverage": 0.75,
        },
    )

    assert ranking.entity_id == "core__worker.py"
    assert ranking.self_score == pytest.approx(0.835)
    assert ranking.confidence == 1.0
    assert ranking.improvement_areas == []
    assert "High code quality" in ranking.strengths
    assert "Excellent test coverage" in ranking.strengths
    assert ranking.recommendations == ["Maintain current quality standards"]

    with sqlite3.connect(engine.db_path) as conn:
        row = conn.execute(
            """
            SELECT self_score, strengths, recommendations, confidence
            FROM self_rankings
            WHERE entity_id = ?
            """,
            (ranking.entity_id,),
        ).fetchone()

    assert row is not None
    assert row[0] == pytest.approx(ranking.self_score)
    assert "High code quality" in json.loads(row[1])
    assert json.loads(row[2]) == ["Maintain current quality standards"]
    assert row[3] == 1.0


@pytest.mark.unit
def test_self_ranking_marks_low_quality_complexity_coverage_and_docs(tmp_path):
    engine = RankingEngine(tmp_path)
    ranking = engine.calculate_self_ranking(
        tmp_path / "legacy.py",
        {
            "quality_score": 0.4,
            "complexity": 0.9,
            "test_coverage": 0.2,
            "doc_coverage": 0.1,
        },
    )

    assert ranking.confidence == 1.0
    assert "Code quality needs improvement" in ranking.improvement_areas
    assert "High complexity - consider refactoring" in ranking.improvement_areas
    assert "Test coverage below 80%" in ranking.improvement_areas
    assert "Documentation coverage below 60%" in ranking.improvement_areas
    assert "Run linters and fix code quality issues" in ranking.recommendations
    assert "Add unit tests to increase coverage" in ranking.recommendations

    partial = engine.calculate_self_ranking(
        tmp_path / "partial.py",
        {"quality_score": 0.8},
    )
    assert partial.confidence == pytest.approx(0.25)


@pytest.mark.unit
def test_global_ranking_uses_confidence_weighted_categories_and_persists(tmp_path):
    engine = RankingEngine(tmp_path)
    entity = tmp_path / "module.py"
    entity.write_text("pass\n", encoding="utf-8")

    ranking = engine.calculate_global_ranking(
        entity,
        "file",
        {
            RankingCategory.QUALITY.value: {
                "score": 0.9,
                "confidence": 1.0,
                "evidence": {"lint": "clean"},
            },
            RankingCategory.COVERAGE.value: {
                "score": 0.6,
                "confidence": 0.5,
                "evidence": {"coverage": 60},
            },
        },
        custom_weights={
            RankingCategory.QUALITY.value: 0.6,
            RankingCategory.COVERAGE.value: 0.4,
        },
    )

    expected = ((0.9 * 0.6 * 1.0) + (0.6 * 0.4 * 0.5)) / ((0.6 * 1.0) + (0.4 * 0.5))
    assert ranking.overall_score == pytest.approx(expected)
    assert ranking.metadata["total_weight"] == pytest.approx(0.8)
    assert ranking.rank_position == 0

    with sqlite3.connect(engine.db_path) as conn:
        global_row = conn.execute(
            "SELECT overall_score, metadata FROM global_rankings WHERE entity_id = ?",
            (ranking.entity_id,),
        ).fetchone()
        category_count = conn.execute(
            "SELECT count(*) FROM category_scores WHERE entity_id = ?",
            (ranking.entity_id,),
        ).fetchone()[0]

    assert global_row is not None
    assert global_row[0] == pytest.approx(expected)
    assert json.loads(global_row[1])["total_weight"] == pytest.approx(0.8)
    assert category_count == 2


@pytest.mark.unit
def test_global_ranking_zero_confidence_falls_back_to_zero(tmp_path):
    engine = RankingEngine(tmp_path)
    ranking = engine.calculate_global_ranking(
        tmp_path / "unknown.py",
        "file",
        {
            RankingCategory.QUALITY.value: {
                "score": 1.0,
                "confidence": 0.0,
            }
        },
        custom_weights={RankingCategory.QUALITY.value: 1.0},
    )

    assert ranking.overall_score == 0.0
    assert ranking.metadata["total_weight"] == 0.0


@pytest.mark.unit
def test_update_ranks_top_ranked_history_and_percentiles(tmp_path):
    engine = RankingEngine(tmp_path)

    entries = [
        ("a.py", 0.9),
        ("b.py", 0.6),
        ("c.py", 0.3),
    ]
    for name, score in entries:
        path = tmp_path / name
        path.write_text(name, encoding="utf-8")
        engine.calculate_global_ranking(
            path,
            "file",
            {RankingCategory.QUALITY.value: {"score": score, "confidence": 1.0}},
            custom_weights={RankingCategory.QUALITY.value: 1.0},
        )

    engine.update_rankings_for_all_entities(entity_type="file")
    ranked = engine.get_top_ranked(entity_type="file", limit=3)

    assert [item.entity_path for item in ranked] == [
        str(tmp_path / "a.py"),
        str(tmp_path / "b.py"),
        str(tmp_path / "c.py"),
    ]
    assert [item.rank_position for item in ranked] == [1, 2, 3]
    assert [item.total_entities for item in ranked] == [3, 3, 3]
    assert ranked[0].percentile == pytest.approx(100.0)
    assert ranked[1].percentile == pytest.approx(200 / 3)
    assert ranked[2].percentile == pytest.approx(100 / 3)
    assert ranked[0].category_scores[RankingCategory.QUALITY.value].score == pytest.approx(0.9)

    history = engine.get_ranking_history(ranked[0].entity_id, limit=5)
    assert len(history) == 1
    assert history[0]["rank_position"] == 1
    assert history[0]["overall_score"] == pytest.approx(0.9)


@pytest.mark.unit
def test_entity_type_filter_keeps_rank_domains_independent(tmp_path):
    engine = RankingEngine(tmp_path)

    file_path = tmp_path / "file.py"
    module_path = tmp_path / "module"
    file_path.write_text("pass\n", encoding="utf-8")

    engine.calculate_global_ranking(
        file_path,
        "file",
        {RankingCategory.QUALITY.value: {"score": 0.4}},
        custom_weights={RankingCategory.QUALITY.value: 1.0},
    )
    engine.calculate_global_ranking(
        module_path,
        "module",
        {RankingCategory.QUALITY.value: {"score": 0.95}},
        custom_weights={RankingCategory.QUALITY.value: 1.0},
    )

    engine.update_rankings_for_all_entities(entity_type="file")
    files = engine.get_top_ranked(entity_type="file")
    modules = engine.get_top_ranked(entity_type="module")

    assert len(files) == 1
    assert files[0].entity_type == "file"
    assert files[0].rank_position == 1
    assert len(modules) == 1
    assert modules[0].entity_type == "module"


@pytest.mark.unit
def test_statistics_and_report_export(tmp_path):
    engine = RankingEngine(tmp_path)

    for idx, score in enumerate([0.2, 0.5, 0.8]):
        path = tmp_path / f"report-{idx}.py"
        path.write_text(str(score), encoding="utf-8")
        engine.calculate_global_ranking(
            path,
            "file",
            {
                RankingCategory.QUALITY.value: {
                    "score": score,
                    "confidence": 1.0,
                    "evidence": {"index": idx},
                }
            },
            custom_weights={RankingCategory.QUALITY.value: 1.0},
        )

    engine.update_rankings_for_all_entities("file")
    stats = engine._calculate_statistics("file")
    assert stats["count"] == 3
    assert stats["mean"] == pytest.approx(0.5)
    assert stats["min"] == pytest.approx(0.2)
    assert stats["max"] == pytest.approx(0.8)
    assert stats["median"] == pytest.approx(0.5)
    assert stats["std_dev"] > 0
    assert engine._calculate_statistics("missing") == {}

    output = tmp_path / "reports" / "ranking.json"
    engine.generate_ranking_report(output, entity_type="file")
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload["metadata"]["total_entities"] == 3
    assert payload["statistics"]["count"] == 3
    assert [item["rank_position"] for item in payload["top_ranked"]] == [1, 2, 3]
    assert payload["top_ranked"][0]["category_scores"]["quality"]["weighted_score"] == pytest.approx(0.8)


@pytest.mark.unit
def test_external_entity_id_preserves_path_when_outside_workspace(tmp_path):
    engine = RankingEngine(tmp_path / "workspace")
    external = tmp_path / "external" / "thing.py"

    entity_id = engine._generate_entity_id(external)

    assert entity_id.endswith("external__thing.py")
