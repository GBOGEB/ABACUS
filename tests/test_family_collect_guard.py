from scripts.ci import family_collect_guard


def test_tally_counts_non_strict_xpass_property(tmp_path):
    junit = tmp_path / "junit.xml"
    junit.write_text(
        """\
<testsuites>
  <testsuite>
    <testcase classname="sample" name="test_pass" />
    <testcase classname="sample" name="test_xpass">
      <properties><property name="xfail" value="true" /></properties>
    </testcase>
  </testsuite>
</testsuites>
""",
        encoding="utf-8",
    )

    counts = family_collect_guard.tally(junit)

    assert counts["collected"] == 2
    assert counts["passed"] == 1
    assert counts["xpassed"] == 1
