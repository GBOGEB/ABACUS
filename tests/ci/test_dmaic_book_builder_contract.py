"""Fail-closed tests for Pandoc book outputs and input contract."""

import importlib.util
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "build_book.py"
spec = importlib.util.spec_from_file_location("dmaic_book_builder", SCRIPT)
book = importlib.util.module_from_spec(spec)
spec.loader.exec_module(book)


def test_all_formats_reject_missing_output(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "build").mkdir()
    for build in (book.build_pdf, book.build_html, book.build_epub):
        with patch.object(book.subprocess, "run") as run:
            run.return_value.returncode = 0
            run.return_value.stderr = ""
            assert build() is False
            assert "book.yaml" not in run.call_args.args[0]


def test_all_formats_require_nonempty_artifacts(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "build").mkdir()
    cases = (
        (book.build_pdf, "DMAIC_V3_BOOK.pdf"),
        (book.build_html, "DMAIC_V3_BOOK.html"),
        (book.build_epub, "DMAIC_V3_BOOK.epub"),
    )
    for build, name in cases:
        output = tmp_path / "build" / name
        output.write_bytes(b"")
        with patch.object(book.subprocess, "run") as run:
            run.return_value.returncode = 0
            run.return_value.stderr = ""
            assert build() is False
            output.write_bytes(b"nonempty test fixture")
            assert build() is True
            output.unlink()


def test_html_uses_current_embed_flag(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "build").mkdir()
    with patch.object(book.subprocess, "run") as run:
        run.return_value.returncode = 1
        run.return_value.stderr = "expected"
        assert book.build_html() is False
        args = run.call_args.args[0]
        assert "--embed-resources" in args
        assert "--self-contained" not in args
