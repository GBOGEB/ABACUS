"""Lane A wave 12: DOW engine document classification and SUT hierarchy."""

import pytest

from DMAIC_V3.tools import dow_engine as dow


def _touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x")


def test_factory_loads_rules_and_hierarchy():
    engine = dow.create_dow_engine()
    assert isinstance(engine, dow.DOWEngine)
    assert engine.classification_rules["historic"]["immutable"] is True
    assert engine.classification_rules["current"]["immutable"] is False
    assert engine.sut_hierarchy["system"] == "DMAIC_V3"
    assert len(engine.sut_hierarchy["subsystems"]) == 5


def test_document_metadata_defaults_tags():
    meta = dow.DocumentMetadata("a.md", dow.DocumentType.TEST, True, False)
    assert meta.tags == []
    tagged = dow.DocumentMetadata(
        "b.md", dow.DocumentType.TEST, True, False, tags=["t"]
    )
    assert tagged.tags == ["t"]


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Milestone_1.md", "milestone"),
        ("api_spec.md", "specification"),
        ("design_doc.md", "design"),
        ("requirements.md", "requirements"),
        ("REQ-12.md", "requirements"),
        ("test_plan.md", "test"),
        ("weekly_report.md", "report"),
        ("notes.md", "unknown"),
    ],
)
def test_determine_document_type(name, expected, tmp_path):
    engine = dow.DOWEngine()
    assert engine._determine_document_type(tmp_path / name).value == expected


def test_classify_empty_workspace(tmp_path):
    result = dow.DOWEngine().classify_documents(tmp_path)
    assert result["total_documents"] == 0
    assert result["classified"]["historic"]["count"] == 0
    assert result["sut_hierarchy"]["system"] == "DMAIC_V3"


def test_classify_full_workspace(tmp_path):
    _touch(tmp_path / "docs" / "historic" / "milestone_a.md")
    _touch(tmp_path / "docs" / "historic" / "old" / "release_report.md")
    _touch(tmp_path / "docs" / "historic" / "skip.txt")
    _touch(tmp_path / "docs" / "current" / "draft_design.md")
    _touch(tmp_path / "screenshots" / "a.png")
    _touch(tmp_path / "screenshots" / "b.jpg")
    _touch(tmp_path / "snippets" / "s.py")
    result = dow.DOWEngine().classify_documents(tmp_path)

    assert result["total_documents"] == 5
    historic = result["classified"]["historic"]
    assert historic["count"] == 2
    assert {d["type"] for d in historic["documents"]} == {"milestone", "report"}
    for doc in historic["documents"]:
        assert doc["immutable"] is True
        assert doc["editable"] is False
        assert doc["protection_level"] == "read_only"
        assert doc["audit_enabled"] is True
    current = result["classified"]["current"]
    assert current["count"] == 1
    assert current["documents"][0]["protection_level"] == "read_write"
    assert current["documents"][0]["type"] == "design"
    ui = result["classified"]["ui_content"]
    assert ui["count"] == 2
    assert ui["screenshots"][0].endswith("a.png")
    assert ui["snippets"][0].endswith("s.py")
