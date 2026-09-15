import importlib.util
import json
from pathlib import Path


SPEC = importlib.util.spec_from_file_location(
    "w72_semantic_census", Path("tools/w72_semantic_census.py")
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def write(root: Path, rel: str, content: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_fixture(root: Path, *, omit_index_b: bool = False) -> None:
    write(
        root,
        "ssot/manifest.yaml",
        """current_bindings:
  - logical_id: AUTH-A
    path: ssot/a.yaml
    state: AUTHORITATIVE_CANDIDATE
  - logical_id: AUTH-B
    path: ssot/b.yaml
    state: AUTHORITATIVE_CANDIDATE
""",
    )
    authorities = [{"logical_id": "AUTH-A", "path": "ssot/a.yaml"}]
    if not omit_index_b:
        authorities.append({"logical_id": "AUTH-B", "path": "ssot/b.yaml"})
    write(root, "ssot/index.json", json.dumps({"authorities": authorities}))
    write(root, "ssot/a.yaml", "a: true\n")
    write(root, "ssot/b.yaml", "b: true\n")
    write(
        root,
        "ssot/ssot_items.yaml",
        """ssot_items:
  - id: SSOT-Q3
    source: docs/domain.md#q3
""",
    )
    write(
        root,
        "ssot/contractual_gap_register.yaml",
        """contractual_gaps:
  - id: CG-01
    title: Real gap
""",
    )
    write(
        root,
        "ssot/semantic_traceability.yaml",
        """semantic_traceability:
  Q3:
    ssot: SSOT-Q3
    gaps: [CG-01]
""",
    )
    write(root, "docs/domain.md", "# Q3\nAuthoritative domain source.\n")
    write(
        root,
        "docs/consumer.md",
        "Consumer binds SSOT-Q3, CG-01, ssot/a.yaml and AUTH-B.\n",
    )


def test_w72_separates_authority_registry_from_domain_and_gap_ids(tmp_path):
    build_fixture(tmp_path)
    receipts, row = MODULE.measure(tmp_path, "a" * 40)

    assert row["measurement_schema"] == MODULE.SCHEMA_VERSION
    assert row["registry_gap_rate"] == 0.0
    assert row["unresolved_reference_rate"] == 0.0
    assert row["consumer_penetration_rate"] == 1.0
    assert row["graph_drop_rate"] == 0.0
    assert row["lineage_gap_rate"] == 0.0
    assert receipts["A_registry_gap"]["findings"]["authority_registry_mismatches"] == []
    assert receipts["B_reference_gap"]["findings"]["unresolved_references"] == []


def test_w72_accepts_canonical_path_as_real_consumer_evidence(tmp_path):
    build_fixture(tmp_path)
    receipts, _ = MODULE.measure(tmp_path, "d" * 40)
    evidence = receipts["C_consumer_penetration"]["findings"]["consumer_evidence"]
    assert "docs/consumer.md" in evidence["AUTH-A"]


def test_w72_does_not_count_entity_source_as_downstream_consumer(tmp_path):
    build_fixture(tmp_path)
    write(tmp_path, "docs/consumer.md", "No semantic bindings here.\n")
    write(tmp_path, "docs/domain.md", "# Q3\nSSOT-Q3 is its own source label.\n")
    receipts, _ = MODULE.measure(tmp_path, "e" * 40)
    assert "SSOT-Q3" in receipts["C_consumer_penetration"]["findings"][
        "unbound_consumers"
    ]


def test_w72_detects_real_authority_registry_mismatch(tmp_path):
    build_fixture(tmp_path, omit_index_b=True)
    receipts, row = MODULE.measure(tmp_path, "b" * 40)

    assert row["registry_gap_rate"] > 0.0
    assert receipts["A_registry_gap"]["findings"]["authority_registry_mismatches"] == [
        "AUTH-B"
    ]


def test_w72_generated_receipts_do_not_self_satisfy_consumers(tmp_path):
    build_fixture(tmp_path)
    write(tmp_path, "docs/consumer.md", "No semantic bindings here.\n")
    write(tmp_path, "docs/domain.md", "# Q3\nNo semantic IDs here.\n")
    write(
        tmp_path,
        "architecture/w70/receipts/example/FEATURE_ROW.json",
        json.dumps({"text": "SSOT-Q3 CG-01 AUTH-A AUTH-B ssot/a.yaml ssot/b.yaml"}),
    )

    _, row = MODULE.measure(tmp_path, "c" * 40)
    assert row["consumer_penetration_rate"] == 0.0
