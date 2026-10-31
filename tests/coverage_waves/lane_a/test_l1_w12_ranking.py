"""Lane A wave 12: delta1_bridge.ranking Bradley-Terry adapter."""

import pytest

from delta1_bridge import ranking

IDS = ["a", "b", "c"]
ROWS = [
    {"a": "a", "b": "b", "a_score": 2, "b_score": 1},
    {"a": "a", "b": "c", "a_score": 3, "b_score": 1},
    {"a": "b", "b": "c", "a_score": 2, "b_score": 1},
    {"a": "c", "b": "a", "a_score": 1, "b_score": 0},
]


@pytest.fixture
def fallback(monkeypatch):
    monkeypatch.setattr(ranking, "CANONICAL_BT_AVAILABLE", False)
    monkeypatch.setattr(ranking, "_canonical_fit", None)


def _canonical(monkeypatch, fake):
    monkeypatch.setattr(ranking, "CANONICAL_BT_AVAILABLE", True)
    monkeypatch.setattr(ranking, "_canonical_fit", fake)


def test_validate_rejects_too_few_or_duplicate_ids():
    with pytest.raises(ValueError, match="two unique"):
        ranking._validate(["a"], [])
    with pytest.raises(ValueError, match="two unique"):
        ranking._validate(["a", "a"], [])


def test_validate_rejects_bad_comparisons():
    with pytest.raises(ValueError, match="distinct known"):
        ranking._validate(IDS, [{"a": "a", "b": "a"}])
    with pytest.raises(ValueError, match="distinct known"):
        ranking._validate(IDS, [{"a": "a", "b": "z"}])
    with pytest.raises(ValueError, match="distinct known"):
        ranking._validate(IDS, [{"a": "z", "b": "a"}])


def test_validate_stringifies_ids():
    assert ranking._validate([1, 2], [{"a": 1, "b": 2}]) == ["1", "2"]


def test_wins_matrix_counts_wins_losses_and_ties():
    rows = [
        {"a": "a", "b": "b", "a_score": 1, "b_score": 0},
        {"a": "a", "b": "b", "a_score": 0, "b_score": 1},
        {"a": "b", "b": "a"},
    ]
    assert ranking._wins_matrix(["a", "b"], rows) == [[0.0, 1.5], [1.5, 0.0]]


def test_fallback_ranks_dominant_item_first(fallback):
    result = ranking.fit_bradley_terry(IDS, ROWS)
    assert result["engine"] == "fallback"
    assert result["ranking"] == ["a", "b", "c"]
    assert sum(result["strengths"].values()) == pytest.approx(1.0)
    assert 1 <= result["iterations"] <= 2000


def test_fallback_no_comparisons_converges_immediately(fallback):
    result = ranking.fit_bradley_terry(["x", "y"], [])
    assert result["iterations"] == 1
    assert result["strengths"] == {"x": 0.5, "y": 0.5}


def test_fallback_respects_iteration_cap(fallback):
    result = ranking.fit_bradley_terry(IDS, ROWS, iterations=2, tolerance=0.0)
    assert result["iterations"] == 2


def test_fallback_zero_iterations(fallback):
    result = ranking.fit_bradley_terry(IDS, ROWS, iterations=0)
    assert result["iterations"] == 0
    assert result["strengths"]["a"] == pytest.approx(1 / 3)


def test_rank_pairwise_returns_list(fallback):
    assert ranking.rank_pairwise(IDS, ROWS, iterations=50) == ["a", "b", "c"]


def test_normalize_for_canonical():
    out = ranking._normalize_for_canonical(
        [
            {"a": "a", "b": "b", "a_score": 3, "b_score": 1},
            {"a": "b", "b": "c"},
        ]
    )
    assert out[0] == {"a": "a", "b": "b", "a_score": 0.75, "b_score": 0.25}
    assert out[1] == {"a": "b", "b": "c", "a_score": 0.5, "b_score": 0.5}


def test_canonical_dict_without_ranking(monkeypatch):
    seen = {}

    def fake(ids, comparisons, iterations, tolerance):
        seen.update(rows=comparisons, it=iterations, tol=tolerance)
        return {"strengths": {"a": 0.2, "b": 0.8}}

    _canonical(monkeypatch, fake)
    rows = [{"a": "a", "b": "b", "a_score": 1, "b_score": 4}]
    result = ranking.fit_bradley_terry(["a", "b"], rows, iterations=7, tolerance=0.5)
    assert result["engine"] == "canonical"
    assert result["ranking"] == ["b", "a"]
    assert seen["it"] == 7
    assert seen["tol"] == 0.5
    assert seen["rows"][0]["b_score"] == pytest.approx(0.8)


def test_canonical_dict_keeps_existing_fields(monkeypatch):
    def fake(ids, comparisons, iterations, tolerance):
        return {"strengths": {"a": 1}, "ranking": ["a", "b"], "engine": "x"}

    _canonical(monkeypatch, fake)
    result = ranking.fit_bradley_terry(["a", "b"], [])
    assert result == {"strengths": {"a": 1}, "ranking": ["a", "b"], "engine": "x"}


def test_canonical_dict_without_strengths(monkeypatch):
    def fake(ids, comparisons, iterations, tolerance):
        return {"note": "odd"}

    _canonical(monkeypatch, fake)
    result = ranking.fit_bradley_terry(["a", "b"], [])
    assert result == {"note": "odd", "engine": "canonical"}


def test_canonical_non_dict_wrapped(monkeypatch):
    def fake(ids, comparisons, iterations, tolerance):
        return [0.4, 0.6]

    _canonical(monkeypatch, fake)
    result = ranking.fit_bradley_terry(["a", "b"], [])
    assert result == {"strengths": [0.4, 0.6], "engine": "canonical"}


def test_canonical_flag_without_function_uses_fallback(monkeypatch):
    _canonical(monkeypatch, None)
    assert ranking.fit_bradley_terry(IDS, ROWS)["engine"] == "fallback"
