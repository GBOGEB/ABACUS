import json

import pytest
import yaml

from DMAIC_V3.core.canonical_index import (
    ArtifactType,
    CanonicalIndexSystem,
    CanonicalMetadata,
    CanonicalVersion,
    IndexEntry,
    VersionStatus,
)


@pytest.mark.unit
def test_canonical_version_roundtrip_and_metadata_serialization():
    version = CanonicalVersion.from_string("2.3.4-rc1+build7")

    assert version.major == 2
    assert version.minor == 3
    assert version.patch == 4
    assert version.prerelease == "rc1"
    assert version.build == "build7"
    assert str(version) == "2.3.4-rc1+build7"

    metadata = CanonicalMetadata(
        canonical_name="sample_artifact",
        display_name="Sample Artifact",
        version=version,
        artifact_type=ArtifactType.FILE.value,
        status=VersionStatus.ACTIVE.value,
        created_at="2026-09-26T00:00:00",
        updated_at="2026-09-26T00:00:00",
        tags=["test"],
    )
    payload = metadata.to_dict()
    assert payload["version"] == "2.3.4-rc1+build7"
    assert payload["tags"] == ["test"]


@pytest.mark.unit
def test_name_generation_and_empty_checksum(tmp_path):
    system = CanonicalIndexSystem(tmp_path)

    assert system.generate_canonical_name("My Artifact v2") == "my_artifact_v2"
    assert system.generate_canonical_name("123 Report") == "artifact_123_report"
    assert system.generate_display_name("my_artifact_v2") == "My Artifact V2"
    assert system._calculate_checksum(tmp_path / "missing.bin") == ""


@pytest.mark.unit
def test_register_artifact_persists_json_yaml_and_checksum(tmp_path):
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("payload\n", encoding="utf-8")
    system = CanonicalIndexSystem(tmp_path)

    entry = system.register_artifact(
        artifact,
        canonical_name="artifact",
        display_name="Artifact",
        artifact_type=ArtifactType.FILE,
        version=CanonicalVersion(1, 2, 3),
        description="demo",
        tags=["alpha", "beta"],
        dependencies=["dep-a"],
    )

    assert entry.canonical_id == "artifact__v1.2.3"
    assert entry.size_bytes == artifact.stat().st_size
    assert len(entry.checksum) == 64
    assert entry.metadata.description == "demo"
    assert entry.metadata.tags == ["alpha", "beta"]
    assert entry.metadata.dependencies == ["dep-a"]

    json_payload = json.loads(system.master_index_json.read_text(encoding="utf-8"))
    yaml_payload = yaml.safe_load(system.master_index_yaml.read_text(encoding="utf-8"))
    assert json_payload["metadata"]["total_entries"] == 1
    assert yaml_payload["entries"][0]["canonical_id"] == "artifact__v1.2.3"


@pytest.mark.unit
def test_update_search_and_count_contract(tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("a", encoding="utf-8")
    b.write_text("bb", encoding="utf-8")
    system = CanonicalIndexSystem(tmp_path)

    first = system.register_artifact(
        a,
        "first",
        "First",
        ArtifactType.FILE,
        tags=["shared", "one"],
    )
    second = system.register_artifact(
        b,
        "second",
        "Second",
        ArtifactType.REPORT,
        tags=["shared", "two"],
    )

    system.update_artifact(
        first.canonical_id,
        version=CanonicalVersion(2, 0, 0),
        status=VersionStatus.DEPRECATED,
        quality_score=91.5,
        rank_position=2,
    )

    updated = system.get_artifact(first.canonical_id)
    assert updated is not None
    assert updated.version == "2.0.0"
    assert updated.status == "deprecated"
    assert updated.metadata.quality_score == 91.5
    assert updated.metadata.rank_position == 2

    assert system.search_artifacts(artifact_type=ArtifactType.REPORT) == [second]
    assert system.search_artifacts(status=VersionStatus.DEPRECATED) == [updated]
    assert system.search_artifacts(tags=["two"]) == [second]
    assert system.search_artifacts(min_quality_score=90) == [updated]
    assert system._count_by_field("artifact_type") == {"file": 1, "report": 1}

    with pytest.raises(ValueError, match="Artifact not found"):
        system.update_artifact("missing__v1.0.0", quality_score=1.0)


@pytest.mark.unit
def test_reload_preserves_registered_entry(tmp_path):
    artifact = tmp_path / "reload.txt"
    artifact.write_text("reload", encoding="utf-8")
    system = CanonicalIndexSystem(tmp_path)
    entry = system.register_artifact(
        artifact,
        "reloadable",
        "Reloadable",
        ArtifactType.FILE,
        version=CanonicalVersion(1, 1, 0),
        tags=["persisted"],
    )

    reloaded = CanonicalIndexSystem(tmp_path)
    loaded = reloaded.get_artifact(entry.canonical_id)

    assert loaded is not None
    assert loaded.canonical_name == "reloadable"
    assert loaded.version == "1.1.0"
    assert loaded.metadata.tags == ["persisted"]
    assert loaded.checksum == entry.checksum


@pytest.mark.unit
def test_version_history_orders_newest_semantically(tmp_path):
    system = CanonicalIndexSystem(tmp_path)
    versions = [CanonicalVersion(1, 0, 0), CanonicalVersion(2, 0, 0), CanonicalVersion(1, 5, 0)]

    for idx, version in enumerate(versions):
        artifact = tmp_path / f"history-{idx}.txt"
        artifact.write_text(str(version), encoding="utf-8")
        system.register_artifact(
            artifact,
            "history",
            "History",
            ArtifactType.FILE,
            version=version,
        )

    history = system.get_version_history("history")
    assert [entry.version for entry in history] == ["2.0.0", "1.5.0", "1.0.0"]


@pytest.mark.unit
def test_export_reports_sort_ranked_entries_and_support_both_formats(tmp_path):
    system = CanonicalIndexSystem(tmp_path)
    for name, rank, score in [("later", 5, 80.0), ("first", 1, 95.0), ("unranked", 0, 10.0)]:
        artifact = tmp_path / f"{name}.txt"
        artifact.write_text(name, encoding="utf-8")
        entry = system.register_artifact(
            artifact,
            name,
            name.title(),
            ArtifactType.REPORT,
        )
        system.update_artifact(
            entry.canonical_id,
            rank_position=rank,
            quality_score=score,
        )

    json_path = tmp_path / "reports" / "index.json"
    yaml_path = tmp_path / "reports" / "index.yaml"
    system.export_to_json(json_path)
    system.export_to_yaml(yaml_path)

    json_report = json.loads(json_path.read_text(encoding="utf-8"))
    yaml_report = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

    assert json_report["statistics"]["avg_quality_score"] == pytest.approx((80 + 95 + 10) / 3)
    assert [entry["canonical_name"] for entry in json_report["entries"]] == [
        "first",
        "later",
        "unranked",
    ]
    assert yaml_report["metadata"]["total_entries"] == 3
