import importlib.util
import json
from pathlib import Path


SPEC = importlib.util.spec_from_file_location(
    "w73_topology", Path("tools/w73_build_semantic_topology_rows.py")
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def receipt(tmp_path: Path, *, open_count: int, evidence: dict) -> Path:
    path = tmp_path / "C_consumer_penetration.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "W72-SEMANTIC-CENSUS-2.0.0",
                "lane": "C_consumer_penetration",
                "source_sha": "a" * 40,
                "totals": {
                    "total_population": 3,
                    "backlog_open": open_count,
                },
                "findings": {"consumer_evidence": evidence},
            }
        ),
        encoding="utf-8",
    )
    return path


def test_w73_derives_bounded_topology_features(tmp_path):
    path = receipt(
        tmp_path,
        open_count=1,
        evidence={"A": ["one.md", "two.md"], "B": ["two.md"], "C": []},
    )
    row = MODULE.topology_row(path)
    assert row["consumer_penetration_rate"] == 0.666667
    assert row["consumer_edge_density"] == 0.5
    assert 0.0 <= row["consumer_degree_concentration"] <= 1.0
    assert row["topology_counts"] == {
        "semantic_entities": 3,
        "bound_entities": 2,
        "consumer_edges": 3,
        "consumer_files": 2,
    }


def test_w73_rejects_receipt_when_evidence_does_not_match_totals(tmp_path):
    path = receipt(
        tmp_path,
        open_count=0,
        evidence={"A": ["one.md"], "B": ["two.md"], "C": []},
    )
    try:
        MODULE.topology_row(path)
    except ValueError as exc:
        assert "consumer evidence coverage" in str(exc)
    else:
        raise AssertionError("expected evidence/totals mismatch to fail")
