import json

import pytest

from DMAIC_V3.core.ranking_engine import (
    GlobalRanking,
    RankingCategory,
    RankingEngine,
    RankingScore,
)


@pytest.mark.unit
def test_ranking_engine_end_to_end_persistence_history_and_report(tmp_path):
    engine = RankingEngine(tmp_path)
    assert engine._calculate_statistics() == {}

    score = RankingScore(
        category=RankingCategory.QUALITY.value,
        score=0.8,
        weight=0.5,
        confidence=0.75,
        evidence={"source": "wave5"},
        timestamp="2026-10-05T00:00:00",
    )
    assert score.weighted_score() == pytest.approx(0.3)

    empty_metadata = GlobalRanking(
        entity_id="sample",
        entity_type="file",
        entity_path="sample.py",
        overall_score=0.0,
        category_scores={},
        rank_position=0,
        percentile=0.0,
        total_entities=0,
        timestamp="2026-10-05T00:00:00",
    )
    assert empty_metadata.metadata == {}

    paths = [tmp_path / "alpha.py", tmp_path / "beta.py"]
    for path in paths:
        path.write_text("pass\n", encoding="utf-8")

    self_ranking = engine.calculate_self_ranking(
        paths[0],
        {
            "quality_score": 0.85,
            "complexity": 0.25,
            "test_coverage": 0.9,
            "doc_coverage": 0.75,
        },
    )
    assert self_ranking.confidence == 1.0
    assert "High code quality" in self_ranking.strengths
    assert self_ranking.recommendations == ["Maintain current quality standards"]

    first = engine.calculate_global_ranking(
        paths[0],
        "file",
        {
            RankingCategory.QUALITY.value: {
                "score": 0.9,
                "confidence": 1.0,
                "evidence": {"lint": "clean"},
            },
            RankingCategory.COVERAGE.value: {
                "score": 0.8,
                "confidence": 1.0,
                "evidence": {"coverage": 80},
            },
        },
    )
    second = engine.calculate_global_ranking(
        paths[1],
        "file",
        {
            RankingCategory.QUALITY.value: {
                "score": 0.4,
                "confidence": 1.0,
            }
        },
    )

    assert first.overall_score > second.overall_score
    assert engine._generate_entity_id(paths[0]) == "alpha.py"
    loaded_scores = engine._load_category_scores(first.entity_id)
    assert set(loaded_scores) == {
        RankingCategory.QUALITY.value,
        RankingCategory.COVERAGE.value,
    }

    engine.update_rankings_for_all_entities("file")
    ranked = engine.get_top_ranked("file", limit=2)
    assert [item.entity_id for item in ranked] == [first.entity_id, second.entity_id]
    assert [item.rank_position for item in ranked] == [1, 2]
    assert ranked[0].percentile == 100.0
    assert ranked[1].percentile == 50.0

    history = engine.get_ranking_history(first.entity_id, limit=5)
    assert len(history) == 1
    assert history[0]["rank_position"] == 1

    stats = engine._calculate_statistics("file")
    assert stats["count"] == 2
    assert stats["max"] == pytest.approx(first.overall_score)
    assert stats["min"] == pytest.approx(second.overall_score)

    report_path = tmp_path / "reports" / "ranking.json"
    engine.generate_ranking_report(report_path, "file")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["metadata"]["total_entities"] == 2
    assert report["statistics"]["count"] == 2
    assert report["top_ranked"][0]["rank_position"] == 1


@pytest.mark.unit
def test_ranking_engine_low_signal_self_ranking_recommends_improvements(tmp_path):
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
    assert len(ranking.improvement_areas) == 4
    assert "Run linters and fix code quality issues" in ranking.recommendations
    assert "Break down complex functions into smaller units" in ranking.recommendations
    assert "Add unit tests to increase coverage" in ranking.recommendations
    assert "Add docstrings and inline comments" in ranking.recommendations
