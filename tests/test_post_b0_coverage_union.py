import json

import pytest

from scripts import post_b0_coverage_union as union


SHA = "a" * 40


def _surface(executed, missing, context_prefix):
    contexts = {
        str(line): [f"{context_prefix}::test_path|run"]
        for line in executed
    }
    return {
        "meta": {"branch_coverage": True},
        "files": {
            "src/dmaic/contract.py": {
                "executed_lines": executed,
                "missing_lines": missing,
                "excluded_lines": [],
                "contexts": contexts,
                "executed_branches": [[1, 2]] if 1 in executed else [],
                "missing_branches": (
                    [] if 1 in executed else [[1, 2]]
                ),
                "summary": {
                    "num_statements": len(executed) + len(missing),
                    "covered_lines": len(executed),
                    "percent_covered": 0.0,
                },
            }
        },
    }


def test_union_uses_executed_line_sets_not_percentage_addition():
    canonical = _surface([1, 2], [3, 4], "tests.test_contract")
    b0 = _surface([2, 3], [1, 4], "DMAIC_V3.tests.test_contract")

    merged = union.merge_coverage_payloads(
        [("canonical", canonical), ("b0", b0)]
    )
    row = merged["files"]["src/dmaic/contract.py"]

    assert row["executed_lines"] == [1, 2, 3]
    assert row["missing_lines"] == [4]
    assert row["summary"]["num_statements"] == 4
    assert row["summary"]["covered_lines"] == 3
    assert row["contexts"]["2"] == [
        "DMAIC_V3.tests.test_contract::test_path|run",
        "tests.test_contract::test_path|run",
    ]


def test_post_b0_census_reranks_remaining_measured_pressure():
    canonical = _surface([1], [2, 3, 4], "tests.test_contract")
    b0 = _surface([2, 3], [1, 4], "DMAIC_V3.tests.test_contract")
    criticality = {
        "files": {
            "src/dmaic/contract.py": {
                "criticality": "USER_DIRECTED_HIGH",
                "source": "controlled-test",
            }
        }
    }

    result = union.build_post_b0_census(
        [("canonical", canonical), ("b0_report_only", b0)],
        exact_sha=SHA,
        criticality=criticality,
    )
    row = result["rows"][0]

    assert result["schema"] == "abacus-post-b0-coverage-dab/1.0.0"
    assert result["exact_sha"] == SHA
    assert result["measurement"]["same_sha_required"] is True
    assert result["active_source"]["statements"] == 4
    assert result["active_source"]["covered_statements"] == 3
    assert result["active_source"]["missed_statements"] == 1
    assert row["maximum_statement_gain"] == 1
    assert row["expected_gain"] == "WITHHELD"
    assert row["surface_measurements"]["canonical"]["covered_lines"] == 1
    assert row["surface_measurements"]["b0_report_only"]["covered_lines"] == 2
    assert result["formal_credit_delta"] == 0
    assert result["engineering_credit_delta"] == 0
    assert result["authority_transfer"] is False


def test_main_round_trip_writes_union_census(tmp_path):
    canonical_path = tmp_path / "canonical.json"
    b0_path = tmp_path / "b0.json"
    criticality_path = tmp_path / "criticality.json"
    matrix_path = tmp_path / "matrix.json"
    evidence_path = tmp_path / "evidence.json"
    out_path = tmp_path / "out.json"

    canonical_path.write_text(
        json.dumps(_surface([1, 2], [3, 4], "tests.test_contract")),
        encoding="utf-8",
    )
    b0_path.write_text(
        json.dumps(_surface([2, 3], [1, 4], "DMAIC_V3.tests.test_contract")),
        encoding="utf-8",
    )
    criticality_path.write_text(
        json.dumps(
            {
                "files": {
                    "src/dmaic/contract.py": {
                        "criticality": "HIGH",
                        "source": "test",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    matrix_path.write_text(
        json.dumps({"python": ["3.12"]}),
        encoding="utf-8",
    )
    evidence_path.write_text(
        json.dumps({"rows": []}),
        encoding="utf-8",
    )

    assert (
        union.main(
            [
                "--coverage-surface",
                f"canonical={canonical_path}",
                "--coverage-surface",
                f"b0_report_only={b0_path}",
                "--criticality",
                str(criticality_path),
                "--matrix-baseline",
                str(matrix_path),
                "--test-evidence",
                str(evidence_path),
                "--exact-sha",
                SHA,
                "--out",
                str(out_path),
            ]
        )
        == 0
    )

    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert written["exact_sha"] == SHA
    assert written["measurement"]["surfaces"] == [
        "canonical",
        "b0_report_only",
    ]
    assert written["legacy_matrix_baseline"] == {"python": ["3.12"]}


def test_union_rejects_bad_inputs_and_handles_sparse_surfaces(tmp_path):
    with pytest.raises(ValueError, match="at least one coverage payload"):
        union.merge_coverage_payloads([])

    with pytest.raises(ValueError, match="files must be an object"):
        union.merge_coverage_payloads([("bad", {"files": []})])

    malformed = tmp_path / "malformed.json"
    malformed.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="expected JSON object"):
        union._load_json(malformed)

    canonical = _surface([1], [2], "tests.test_contract")
    canonical["files"]["src/dmaic/contract.py"]["contexts"] = []
    canonical["files"]["src/dmaic/contract.py"]["executed_branches"] = [
        [1],
        [1, "x"],
    ]
    canonical["files"]["src/dmaic/contract.py"]["missing_branches"] = [[1, 2]]
    other = {"meta": {"branch_coverage": False}, "files": {}}

    merged = union.merge_coverage_payloads(
        [("canonical", canonical), ("other", other)]
    )
    assert merged["files"]["src/dmaic/contract.py"]["contexts"] == {}
    assert merged["_surface_stats"]["src/dmaic/contract.py"]["other"] == {
        "present": False,
        "covered_lines": 0,
        "contexts": 0,
    }
