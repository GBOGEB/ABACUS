import pytest

from src.dmaic import recursion


def test_should_stop_handles_empty_max_iterations_and_continue():
    assert recursion.should_stop([], []) == (False, "No history")

    history = [{"score": 0.1}, {"score": 0.2}]
    stop, reason = recursion.should_stop(
        history,
        [{"type": "max_iterations", "value": 2}],
    )
    assert stop is True
    assert reason == "Maximum iterations reached"

    stop, reason = recursion.should_stop(
        [{"other": 1}, {"other": 2}, {"other": 3}],
        [{"type": "max_iterations", "value": 10}],
    )
    assert stop is False
    assert reason == "Continue iteration"


def test_should_stop_detects_convergence_and_respects_threshold():
    history = [
        {"score": 1.000},
        {"score": 1.004},
        {"score": 1.006},
    ]
    stop, reason = recursion.should_stop(
        history,
        [
            {"type": "max_iterations", "value": 10},
            {"type": "convergence_threshold", "value": 0.01},
        ],
    )
    assert stop is True
    assert reason == "Convergence detected"

    stop, reason = recursion.should_stop(
        history,
        [
            {"type": "max_iterations", "value": 10},
            {"type": "convergence_threshold", "value": 0.001},
        ],
    )
    assert stop is False
    assert reason == "Continue iteration"


@pytest.mark.parametrize(
    ("history", "expected"),
    [
        (
            [],
            {
                "converged": False,
                "iterations": 0,
                "trend": "unknown",
            },
        ),
        (
            [{"score": 1.0}],
            {
                "converged": False,
                "iterations": 1,
                "trend": "insufficient_data",
            },
        ),
    ],
)
def test_analyze_convergence_short_histories(history, expected):
    assert recursion.analyze_convergence(history) == expected


@pytest.mark.parametrize(
    ("scores", "trend"),
    [
        ([1.0, 1.2, 1.3], "improving"),
        ([1.3, 1.2, 1.0], "declining"),
        ([1.0, 1.1, 1.0], "stable"),
    ],
)
def test_analyze_convergence_score_trends(scores, trend):
    result = recursion.analyze_convergence(
        [{"score": score} for score in scores]
    )

    assert result["trend"] == trend
    assert result["iterations"] == 3
    assert result["final_score"] == scores[-1]
    assert result["score_range"] == pytest.approx(max(scores) - min(scores))
    assert result["converged"] is (
        max(scores) - min(scores)
        < recursion.DEFAULT_CONVERGENCE_THRESHOLD
    )


def test_analyze_convergence_detects_tight_range_and_missing_scores():
    converged = recursion.analyze_convergence(
        [{"score": 1.000}, {"score": 1.004}, {"score": 1.006}]
    )
    assert converged["converged"] is True
    assert converged["trend"] == "improving"

    missing = recursion.analyze_convergence(
        [{"score": 1.0}, {"other": 2.0}]
    )
    assert missing == {
        "converged": False,
        "iterations": 2,
        "trend": "no_scores_available",
    }


def test_generate_stop_rules_uses_defaults_and_overrides():
    assert recursion.generate_stop_rules({}) == [
        {
            "type": "max_iterations",
            "value": recursion.DEFAULT_MAX_ITERATIONS,
        },
        {
            "type": "convergence_threshold",
            "value": recursion.DEFAULT_CONVERGENCE_THRESHOLD,
        },
    ]

    assert recursion.generate_stop_rules(
        {"max_iterations": 4, "convergence_threshold": 0.25}
    ) == [
        {"type": "max_iterations", "value": 4},
        {"type": "convergence_threshold", "value": 0.25},
    ]
