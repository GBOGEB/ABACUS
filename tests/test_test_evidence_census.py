from pathlib import Path

from scripts import test_evidence_census as census


def test_junit_census_records_every_outcome_and_governed_skip(tmp_path: Path):
    junit = tmp_path / "junit.xml"
    junit.write_text(
        """<testsuite tests="4">
  <testcase classname="tests.test_a" name="test_green"/>
  <testcase classname="tests.test_a" name="test_fail">
    <failure message="boom">boom</failure>
  </testcase>
  <testcase classname="tests.test_a" name="test_error">
    <error message="setup">setup</error>
  </testcase>
  <testcase classname="tests.test_a" name="test_config">
    <skipped message="TEST_BLOCKED_CONFIG: fixture unavailable"/>
  </testcase>
</testsuite>
""",
        encoding="utf-8",
    )

    result = census.build_census(junit)

    assert result["outcomes"] == {
        "error": 1,
        "fail": 1,
        "pass": 1,
        "skip": 1,
    }
    assert result["states"]["TEST_GREEN"] == 1
    assert result["states"]["TEST_FAILING"] == 2
    assert result["states"]["TEST_BLOCKED_CONFIG"] == 1
    assert result["uncategorized_skips"] == []
    assert result["formal_credit_delta"] == 0
    assert result["engineering_credit_delta"] == 0


def test_uncategorized_skip_is_visible_not_silently_accepted(tmp_path: Path):
    junit = tmp_path / "junit.xml"
    junit.write_text(
        """<testsuite tests="1">
  <testcase classname="tests.test_a" name="test_skip">
    <skipped message="old free-text skip"/>
  </testcase>
</testsuite>
""",
        encoding="utf-8",
    )

    result = census.build_census(junit)

    assert result["uncategorized_skips"] == ["tests.test_a::test_skip"]
    assert result["states"]["UNCLASSIFIED_SKIP"] == 1
