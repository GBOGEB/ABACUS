import json

from DMAIC_V3.core.canonical_index import (
    ArtifactType,
    CanonicalIndexSystem,
    CanonicalVersion,
    VersionStatus,
)


def test_version_and_name_helpers_round_trip(tmp_path):
    system = CanonicalIndexSystem(tmp_path)
    version = CanonicalVersion.from_string("2.4.1-rc2+build9")

    assert str(version) == "2.4.1-rc2+build9"
    assert system.generate_canonical_name("123 Demo / Artifact") == "artifact_123_demo_artifact"
    assert system.generate_display_name("artifact_123_demo_artifact") == "Artifact 123 Demo Artifact"
    assert system._generate_canonical_id("demo", version) == "demo__v2.4.1-rc2+build9"
    assert system._calculate_checksum(tmp_path / "missing.bin") == ""


def test_register_update_search_reload_and_export(tmp_path):
    system = CanonicalIndexSystem(tmp_path)
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("payload\n", encoding="utf-8")

    entry = system.register_artifact(
        artifact,
        canonical_name="demo_artifact",
        display_name="Demo Artifact",
        artifact_type=ArtifactType.FILE,
        version=CanonicalVersion(1, 2, 0),
        description="runtime test",
        tags=["wave6", "runtime"],
        dependencies=["dep-a"],
    )

    assert entry.canonical_id == "demo_artifact__v1.2.0"
    assert len(entry.checksum) == 64
    assert entry.size_bytes == artifact.stat().st_size

    system.update_artifact(
        entry.canonical_id,
        version=CanonicalVersion(2, 0, 0),
        status=VersionStatus.DEPRECATED,
        quality_score=92.5,
        rank_position=1,
    )

    updated = system.get_artifact(entry.canonical_id)
    assert updated is not None
    assert updated.version == "2.0.0"
    assert updated.status == "deprecated"
    assert updated.metadata.quality_score == 92.5
    assert updated.metadata.rank_position == 1

    assert system.search_artifacts(
        artifact_type=ArtifactType.FILE,
        status=VersionStatus.DEPRECATED,
        tags=["wave6"],
        min_quality_score=90,
    ) == [updated]
    assert system._count_by_field("artifact_type") == {"file": 1}

    report_path = tmp_path / "reports" / "index.json"
    system.export_to_json(report_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["metadata"]["total_entries"] == 1
    assert report["entries"][0]["canonical_name"] == "demo_artifact"

    reloaded = CanonicalIndexSystem(tmp_path)
    loaded = reloaded.get_artifact(entry.canonical_id)
    assert loaded is not None
    assert loaded.version == "2.0.0"
    assert loaded.metadata.tags == ["wave6", "runtime"]


def test_version_history_uses_semantic_order(tmp_path):
    system = CanonicalIndexSystem(tmp_path)

    for idx, version in enumerate(
        [CanonicalVersion(1, 0, 0), CanonicalVersion(2, 0, 0), CanonicalVersion(1, 5, 0)]
    ):
        artifact = tmp_path / f"history-{idx}.txt"
        artifact.write_text(str(version), encoding="utf-8")
        system.register_artifact(
            artifact,
            canonical_name="history",
            display_name="History",
            artifact_type=ArtifactType.FILE,
            version=version,
        )

    assert [entry.version for entry in system.get_version_history("history")] == [
        "2.0.0",
        "1.5.0",
        "1.0.0",
    ]
