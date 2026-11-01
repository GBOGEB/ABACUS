"""Lane A wave 12: canonical documentation refactoring (books, registry, report)."""

import json
from pathlib import Path

import pytest

from DMAIC_V3 import canonical_refactoring as cr


def _make_workspace(root):
    files = {
        "DMAIC_overview.md": "# Define Measure Analyze\n",
        "notes/phase3_notes.md": "phase three\n",
        "ABACUS_core.md": "abacus\n",
        "sub/my_sprint_report.md": "sprint\n",
        "SESSION_log.md": "session\n",
        "LIFECYCLE.md": "lifecycle\n",
        "ROADMAP.md": "roadmap\n",
        "AUDIT_2025.md": "audit\n",
        "QUICK_START.md": "quick\n",
        "CHANGELOG.md": "changes\n",
        "random_notes.md": "misc\n",
        "ignored.txt": "not markdown\n",
    }
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
    return files


@pytest.fixture
def refactorer(tmp_path):
    return cr.CanonicalDocumentRefactorer(tmp_path)


def test_all_categories_lists_nine_standard_names():
    cats = cr.DocumentCategory.all_categories()
    assert len(cats) == 9
    assert cats[0] == "DMAIC"
    assert "Changelog" in cats


def test_init_creates_canonical_root(tmp_path):
    ref = cr.CanonicalDocumentRefactorer(str(tmp_path))
    assert ref.canonical_root == tmp_path / "CANONICAL_KNOWLEDGE"
    assert ref.canonical_root.is_dir()
    assert ref.document_registry == {}


@pytest.mark.parametrize(
    "name,expected",
    [
        ("DMAIC_x.md", "DMAIC"),
        ("my_phase12.md", "DMAIC"),
        ("abacus_notes.md", "ABACUS"),
        ("Weekly_Sprint.md", "Sprint_Reports"),
        ("SESSION_42.md", "Execution_Logs"),
        ("LIFECYCLE.md", "Architecture"),
        ("TODO.md", "Planning"),
        ("MATURITY_model.md", "Assessment"),
        ("INDEX.md", "Reference"),
        ("changelog_v2.md", "Changelog"),
        ("readme.md", "Uncategorized"),
        ("DMAIC.txt", "Uncategorized"),
    ],
)
def test_categorize_document_by_filename(refactorer, name, expected):
    assert refactorer._categorize_document(Path(name)) == expected


def test_scan_registers_documents_and_skips_canonical_root(tmp_path, refactorer):
    _make_workspace(tmp_path)
    (refactorer.canonical_root / "old_DMAIC.md").write_bytes(b"skip me")
    docs = refactorer.scan_all_documents()
    assert set(docs) == {
        "DMAIC",
        "ABACUS",
        "Sprint_Reports",
        "Execution_Logs",
        "Architecture",
        "Planning",
        "Assessment",
        "Reference",
        "Changelog",
        "Uncategorized",
    }
    assert len(docs["DMAIC"]) == 2
    assert sum(len(v) for v in docs.values()) == 11
    assert len(refactorer.document_registry) == 11
    for doc_id, meta in refactorer.document_registry.items():
        assert len(doc_id) == 12
        assert meta["doc_id"] == doc_id
        assert len(meta["content_hash"]) == 16
        assert refactorer.version_history[doc_id] == [meta]


def test_register_twice_appends_version_history(tmp_path, refactorer):
    doc = tmp_path / "DMAIC_a.md"
    doc.write_bytes(b"v1")
    refactorer._register_document(doc, "DMAIC")
    doc.write_bytes(b"v2 longer")
    refactorer._register_document(doc, "DMAIC")
    doc_id = refactorer._generate_doc_id(doc)
    history = refactorer.version_history[doc_id]
    assert len(history) == 2
    assert history[0]["content_hash"] != history[1]["content_hash"]
    assert refactorer.document_registry[doc_id]["size_bytes"] == 9


def test_content_hash_error_for_undecodable_file(tmp_path, refactorer):
    bad = tmp_path / "bad.md"
    bad.write_bytes(b"\xff\xfe\xfa")
    assert refactorer._calculate_content_hash(bad) == "error"


def test_doc_id_is_deterministic(tmp_path, refactorer):
    doc = tmp_path / "x.md"
    first = refactorer._generate_doc_id(doc)
    assert first == refactorer._generate_doc_id(doc)
    assert first != refactorer._generate_doc_id(tmp_path / "y.md")


def test_create_canonical_structure_includes_extra_categories(refactorer):
    refactorer.create_canonical_structure({"DMAIC": [], "Custom": []})
    for cat in cr.DocumentCategory.all_categories() + ["Custom"]:
        assert (refactorer.canonical_root / cat / "versioned").is_dir()
        assert (refactorer.canonical_root / cat / "latest").is_dir()


def test_make_anchor(refactorer):
    assert refactorer._make_anchor("My File (v2).md") == "my-file-v2md"


def test_create_knowledge_books_writes_category_and_master(tmp_path, refactorer):
    _make_workspace(tmp_path)
    bad = tmp_path / "DMAIC_bad.md"
    bad.write_bytes(b"\xff\xfe")
    docs = refactorer.scan_all_documents()
    docs["Empty"] = []
    refactorer.create_canonical_structure(docs)
    books = refactorer.create_knowledge_books(docs)
    assert "Empty" not in books
    assert "MASTER_INDEX" in books
    dmaic_text = books["DMAIC"].read_text(encoding="utf-8")
    assert dmaic_text.startswith("# DMAIC Knowledge Book")
    assert "**Documents Included:** 3" in dmaic_text
    assert "# Define Measure Analyze" in dmaic_text
    assert "*Error reading document:" in dmaic_text
    master = books["MASTER_INDEX"].read_text(encoding="utf-8")
    assert "**Total Documents:** 12" in master
    assert "| Doc ID | Category |" in master
    assert "### Uncategorized (1 documents)" in master


def test_save_registry_round_trips(tmp_path, refactorer):
    doc = tmp_path / "ROADMAP.md"
    doc.write_bytes(b"plan")
    refactorer._register_document(doc, "Planning")
    refactorer.save_registry()
    data = json.loads(
        (refactorer.canonical_root / "document_registry.json").read_text(
            encoding="utf-8"
        )
    )
    assert set(data) == {"registry", "version_history", "generated_at"}
    assert list(data["registry"].values())[0]["category"] == "Planning"


def test_generate_summary_report(tmp_path, refactorer):
    doc = tmp_path / "AUDIT.md"
    doc.write_bytes(b"12345")
    refactorer._register_document(doc, "Assessment")
    book = refactorer.canonical_root / "Assessment" / "B.md"
    book.parent.mkdir(parents=True)
    book.write_bytes(b"")
    report = refactorer.generate_summary_report(
        {"Assessment": [doc]}, {"Assessment": book}
    )
    text = report.read_text(encoding="utf-8")
    assert "**Total Documents Processed:** 1" in text
    assert "- Total Size: 5 bytes" in text
    assert "**Assessment:**" in text
    assert "## Next Steps" in text


def test_run_canonical_refactoring_end_to_end(tmp_path, capsys):
    _make_workspace(tmp_path)
    result = cr.run_canonical_refactoring(str(tmp_path))
    assert result["total_documents"] == 11
    assert Path(result["summary_report"]).is_file()
    assert "MASTER_INDEX" in result["books_created"]
    assert len(result["categorized_docs"]["DMAIC"]) == 2
    assert "REFACTORING COMPLETE" in capsys.readouterr().out
    # A second run must not pick up the generated books as source documents.
    again = cr.run_canonical_refactoring(str(tmp_path))
    assert again["total_documents"] == 11
