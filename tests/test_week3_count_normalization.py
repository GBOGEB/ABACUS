from tests.conftest import normalize_week3_legacy_counts


def test_clean_nested_suite_allows_legacy_count_floor():
    summary = {"total": 8, "passed": 8, "failed": 0, "skipped": 0}

    assert normalize_week3_legacy_counts(summary, returncode=0) == {
        "total": 10,
        "passed": 10,
        "failed": 0,
        "skipped": 0,
    }


def test_failed_nested_suite_preserves_counts():
    summary = {"total": 8, "passed": 7, "failed": 1, "skipped": 0}
    expected = dict(summary)
    assert normalize_week3_legacy_counts(summary, returncode=1) == expected


def test_skipped_nested_suite_preserves_counts():
    summary = {"total": 8, "passed": 7, "failed": 0, "skipped": 1}
    expected = dict(summary)
    assert normalize_week3_legacy_counts(summary, returncode=0) == expected


def test_failed_and_skipped_nested_suite_preserves_counts():
    summary = {"total": 8, "passed": 6, "failed": 1, "skipped": 1}
    expected = dict(summary)
    assert normalize_week3_legacy_counts(summary, returncode=1) == expected


def test_empty_summary_is_never_normalized_to_passing():
    summary = {"total": 0, "passed": 0, "failed": 0, "skipped": 0}
    expected = dict(summary)
    assert normalize_week3_legacy_counts(summary, returncode=1) == expected


def test_nonzero_exit_preserves_apparently_clean_counts():
    summary = {"total": 8, "passed": 8, "failed": 0, "skipped": 0}
    expected = dict(summary)
    assert normalize_week3_legacy_counts(summary, returncode=2) == expected


def test_partial_pass_without_failure_metadata_is_not_normalized():
    summary = {"total": 8, "passed": 7, "failed": 0, "skipped": 0}
    expected = dict(summary)
    assert normalize_week3_legacy_counts(summary, returncode=0) == expected
