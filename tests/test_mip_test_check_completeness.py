from pathlib import Path

from scripts import mip_test_check_completeness as mip


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_inventory_detects_orphan_pytest_surface(tmp_path):
    write(tmp_path / "tests" / "test_ok.py", "def test_ok():\n    assert True\n")
    write(tmp_path / "integration" / "demo" / "tests" / "test_report.py", "def test_report():\n    assert True\n")
    write(tmp_path / "stray_test.py", "def test_stray():\n    assert True\n")
    write(tmp_path / "src" / "mod.py", "VALUE = 1\n")
    write(tmp_path / ".github" / "workflows" / "a.yml", "on: [push]\njobs:\n  t:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo ok\n")

    inventory = mip.discover_inventory(tmp_path.resolve())

    assert inventory["pytest_test_file_count"] == 3
    assert inventory["canonical_test_file_count"] == 1
    assert inventory["report_only_test_file_count"] == 1
    assert inventory["orphan_test_file_count"] == 1
    assert inventory["orphan_test_files"] == ["stray_test.py"]
    assert inventory["active_source_python_count"] == 1


def test_workflow_trigger_and_executable_shape(tmp_path):
    workflow = tmp_path / ".github" / "workflows" / "proof.yml"
    write(
        workflow,
        """on:
  push:
  workflow_dispatch:
jobs:
  proof:
    runs-on: ubuntu-latest
    steps:
      - name: prove
        run: echo ok
""",
    )

    row = mip.workflow_shape(workflow, tmp_path.resolve())

    assert row["triggers"] == ["push", "workflow_dispatch"]
    assert row["job_count"] == 1
    assert row["static_executable"] is True
    assert row["manual_only"] is False


def test_workflow_shape_accepts_quoted_on_and_indentationless_steps(tmp_path):
    workflow = tmp_path / ".github" / "workflows" / "serialized.yml"
    write(
        workflow,
        """name: Serialized workflow
'on':
  workflow_dispatch:
jobs:
  proof:
    runs-on: ubuntu-latest
    steps:
    - name: prove
      run: echo ok
""",
    )

    row = mip.workflow_shape(workflow, tmp_path.resolve())

    assert row["triggers"] == ["workflow_dispatch"]
    assert row["job_count"] == 1
    assert row["static_step_count"] == 1
    assert row["static_executable"] is True
    assert row["manual_only"] is True


def test_false_green_census_uses_repo_relative_paths(tmp_path):
    rel = ".github/workflows/masked.yml"
    write(
        tmp_path / rel,
        """on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: pytest || echo "masked"
""",
    )

    result = mip.false_green_census(tmp_path.resolve(), [rel])

    assert result["unguarded_count"] == 1
    assert result["findings"][0]["path"] == rel


def test_build_report_ranks_infra_before_admission_coverage_and_static(tmp_path):
    write(
        tmp_path / ".github" / "workflows" / "mip-coverage-evidence.yml",
        """on:
  workflow_dispatch:
jobs:
  census:
    runs-on: ubuntu-latest
    steps:
      - run: pytest || echo "masked"
""",
    )
    write(tmp_path / "tests" / "test_ok.py", "def test_ok():\n    assert True\n")
    write(tmp_path / "orphan_test.py", "def test_orphan():\n    assert True\n")
    write(tmp_path / "src" / "critical.py", "def f(x):\n    return x + 1\n")

    coverage = {
        "schema": "abacus-post-b0-coverage-dab/1.0.0",
        "measurement": {"dynamic_context": "test_function"},
        "active_source": {"statements": 2, "covered_statements": 0, "missed_statements": 2},
        "full_measurement": {
            "missing_lines": 2,
            "missing_branches": 1,
            "percent_covered": 0.0,
        },
        "rows": [
            {
                "path": "src/critical.py",
                "source_class": "ACTIVE_SOURCE",
                "existing_test_surface": [],
                "missed_statements": 2,
                "coverage_pct": 0.0,
                "criticality": "USER_DIRECTED_HIGH",
                "disposition": "ADMISSION_PENDING",
            }
        ],
    }
    evidence = {
        "ratchet_status": "PASS",
        "outcomes": {"pass": 1},
        "rows": [{"test": "tests.test_ok.test_ok", "test_state": "TEST_GREEN"}],
    }
    admission = {
        "test_file_count": 1,
        "rows": [
            {
                "path": "DMAIC_V3/tests/test_latent.py",
                "test_state": "TEST_EXISTS_UNCOLLECTED",
                "collection_status": "GREEN",
            }
        ],
    }
    static = {"total": 9, "families": {"F841": 9}}

    report = mip.build_report(
        tmp_path.resolve(),
        "deadbeef",
        coverage,
        evidence,
        admission,
        {},
        static,
    )

    categories = [row["category"] for row in report["ranked_residual"]]
    assert categories[0] == "INFRA/CHECK"
    assert "TEST_ADMISSION" in categories
    assert "NO_TEST" in categories
    assert "COVERAGE" in categories
    assert categories[-1] == "STATIC_ANALYSIS"
    assert report["tc2_dynamic_context_crosswalk"]["user_directed_high_without_context"] == [
        "src/critical.py"
    ]
    assert report["tc4_false_green"]["syntactic_unguarded_count"] == 1
    assert report["tc4_false_green"]["semantic_false_green_count"] == 1
    assert report["tc4_false_green"]["semantic_counts"]["TEST_MASK"] == 1
    assert report["ranked_residual"][0]["rank"] == 1


def test_semantic_false_green_distinguishes_test_mask_from_cleanup(tmp_path):
    rel = ".github/workflows/semantic.yml"
    write(
        tmp_path / rel,
        """on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Run tests
        run: pytest -q || echo "tests completed"
      - name: Cleanup
        run: trap 'kill "$pid" 2>/dev/null || true' EXIT
""",
    )
    rows = mip.false_green_census(tmp_path.resolve(), [rel])["findings"]
    test_row = mip.semantic_false_green_kind(rows[0], tmp_path.resolve())
    cleanup_row = mip.semantic_false_green_kind(rows[1], tmp_path.resolve())

    assert test_row["semantic_kind"] == "TEST_MASK"
    assert test_row["semantic_false_green"] is True
    assert test_row["step_name"] == "Run tests"
    assert cleanup_row["semantic_kind"] == "CLEANUP_BEST_EFFORT"
    assert cleanup_row["semantic_false_green"] is False
