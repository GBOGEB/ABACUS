from DMAIC_V3.generators.execution_tracker import (
    ErrorType,
    ExecutionResult,
    ExecutionStatistics,
    ExecutionStatus,
    ExecutionTracker,
)


def test_execution_result_serializes_enums():
    result = ExecutionResult(
        file_path="sample.py",
        file_type="python",
        status=ExecutionStatus.FAILED,
        execution_time=0.1,
        error_type=ErrorType.TYPE_ERROR,
        error_message="TypeError: bad value",
    )

    payload = result.to_dict()

    assert payload["status"] == "FAILED"
    assert payload["error_type"] == "TypeError"
    assert payload["timestamp"]


def test_statistics_initialize_independent_mutable_fields():
    first = ExecutionStatistics()
    second = ExecutionStatistics()

    first.error_breakdown["TypeError"] = 1
    first.victory_conditions_met["python_execution"] = True

    assert second.error_breakdown == {}
    assert second.victory_conditions_met == {}
    assert first.to_dict()["error_breakdown"] == {"TypeError": 1}


def test_error_classification_covers_known_and_unknown_cases(tmp_path):
    tracker = ExecutionTracker(tmp_path)

    cases = {
        "SyntaxError: invalid syntax": ErrorType.SYNTAX_ERROR,
        "ModuleNotFoundError: missing": ErrorType.IMPORT_ERROR,
        "TypeError: wrong": ErrorType.TYPE_ERROR,
        "ValueError: wrong": ErrorType.VALUE_ERROR,
        "AttributeError: x": ErrorType.ATTRIBUTE_ERROR,
        "NameError: x": ErrorType.NAME_ERROR,
        "No such file": ErrorType.FILE_NOT_FOUND,
        "Permission denied": ErrorType.PERMISSION_ERROR,
        "operation timeout": ErrorType.TIMEOUT_ERROR,
        "mystery": ErrorType.UNKNOWN_ERROR,
    }

    for message, expected in cases.items():
        assert tracker._classify_error(message) is expected
