from tests.conftest import normalize_week3_legacy_counts


def test_clean_nested_suite_allows_legacy_count_floor():
    summary = {"total": 8, "passed": 8, "failed": 0, "skipped": 0}

    assert normalize_week3_legacy_counts(summary) == {
        "total": 10,
        "passed": 10,
        "failed": 0,
        "skipped": 0,
    }


def test_failed_nested_suite_preserves_counts():
    summary = {"total": 8, "passed": 7, "failed": 1, "skipped": 0}

    assert normalize_week3_legacy_counts(summary) == summary
    assert summary == {"total": 8, "passed": 7, "failed": 1, "skipped": 0}


def test_skipped_nested_suite_preserves_counts():
    summary = {"total": 8, "passed": 7, "failed": 0, "skipped": 1}

    assert normalize_week3_legacy_counts(summary) == summary
    assert summary == {"total": 8, "passed": 7, "failed": 0, "skipped": 1}


def test_failed_and_skipped_nested_suite_preserves_counts():
    summary = {"total": 8, "passed": 6, "failed": 1, "skipped": 1}

    assert normalize_week3_legacy_counts(summary) == summary
    assert summary == {"total": 8, "passed": 6, "failed": 1, "skipped": 1}
