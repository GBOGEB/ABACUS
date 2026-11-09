"""Unit and integration tests for verification_hook.py."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.verification_hook import (
    create_mock_sidecar,
    get_mime_type,
    load_manifest,
    now_iso,
    process_directory,
    process_file,
    save_manifest,
    sha256_hash,
    update_manifest,
)


class TestSha256Hash:
    def test_deterministic(self, tmp_dir):
        path = tmp_dir / "test.bin"
        path.write_bytes(b"hello world")
        h1 = sha256_hash(str(path))
        h2 = sha256_hash(str(path))
        assert h1 == h2
        assert len(h1) == 64

    def test_different_content_different_hash(self, tmp_dir):
        p1 = tmp_dir / "a.bin"
        p2 = tmp_dir / "b.bin"
        p1.write_bytes(b"content A")
        p2.write_bytes(b"content B")
        assert sha256_hash(str(p1)) != sha256_hash(str(p2))


class TestGetMimeType:
    def test_pptx(self):
        assert "presentation" in get_mime_type("test.pptx")

    def test_pdf(self):
        assert get_mime_type("test.pdf") == "application/pdf"

    def test_png(self):
        assert get_mime_type("test.png") == "image/png"

    def test_unknown(self):
        assert get_mime_type("test.xyz") == "application/octet-stream"


class TestNowIso:
    def test_format(self):
        ts = now_iso()
        assert "T" in ts
        assert ts.endswith("Z")


class TestCreateMockSidecar:
    def test_creates_mock_file(self, tmp_dir):
        binary = tmp_dir / "test.pptx"
        binary.write_bytes(b"\x00" * 100)
        mock_data = create_mock_sidecar(str(binary), "a" * 64, 100)
        mock_path = Path(mock_data["mock_file"])
        assert mock_path.exists()
        assert mock_data["sha256"] == "a" * 64
        assert mock_data["file_size"] == 100

    def test_mock_content_valid_json(self, tmp_dir):
        binary = tmp_dir / "test.pdf"
        binary.write_bytes(b"%PDF" + b"\x00" * 100)
        mock_data = create_mock_sidecar(str(binary), "b" * 64, 104)
        mock_path = Path(mock_data["mock_file"])
        loaded = json.loads(mock_path.read_text())
        assert loaded["filename"] == "test.pdf"
        assert loaded["sha256"] == "b" * 64


class TestManifest:
    def test_load_nonexistent_creates_empty(self, tmp_dir):
        manifest = load_manifest(str(tmp_dir / "manifest.json"))
        assert manifest["version"] == "1.0.0"
        assert manifest["assets"] == []

    def test_save_and_load(self, tmp_dir):
        path = str(tmp_dir / "manifest.json")
        manifest = {"version": "1.0.0", "assets": [], "lineage": []}
        save_manifest(manifest, path)
        loaded = load_manifest(path)
        assert loaded["version"] == "1.0.0"

    def test_update_new_asset(self):
        manifest = {"version": "1.0.0", "assets": [], "lineage": []}
        mock_data = {
            "filename": "test.pptx",
            "sha256": "a" * 64,
            "file_size": 1024,
            "mime_type": "application/pptx",
            "ingested_at": "2026-05-20T00:00:00Z",
            "mock_file": "Input_Master/test.pptx.mock",
            "processing_status": "verified",
        }
        is_new = update_manifest(manifest, mock_data)
        assert is_new
        assert len(manifest["assets"]) == 1

    def test_update_existing_asset(self):
        manifest = {
            "version": "1.0.0",
            "assets": [{"filename": "test.pptx", "sha256": "old_hash"}],
            "lineage": [],
        }
        mock_data = {
            "filename": "test.pptx",
            "sha256": "new_hash",
            "file_size": 2048,
            "mime_type": "application/pptx",
            "ingested_at": "2026-05-20T01:00:00Z",
            "mock_file": "Input_Master/test.pptx.mock",
            "processing_status": "verified",
        }
        is_new = update_manifest(manifest, mock_data)
        assert not is_new
        assert len(manifest["assets"]) == 1
        assert manifest["assets"][0]["sha256"] == "new_hash"


class TestProcessFile:
    def test_process_binary(self, tmp_dir):
        input_dir = tmp_dir / "Input_Master"
        input_dir.mkdir()
        binary = input_dir / "test.pptx"
        binary.write_bytes(b"PK\x03\x04" + b"\x00" * 100)

        data_dir = tmp_dir / "_data"
        data_dir.mkdir()

        result = process_file(str(binary), str(data_dir), verbose=False)
        assert result is not None
        assert result["filename"] == "test.pptx"
        assert len(result["sha256"]) == 64

        # Check manifest was created
        manifest_path = data_dir / "lineage_manifest.json"
        assert manifest_path.exists()

    def test_skip_non_binary(self, tmp_dir):
        txt = tmp_dir / "readme.txt"
        txt.write_text("hello")
        result = process_file(str(txt), str(tmp_dir), verbose=False)
        assert result is None

    def test_skip_mock_file(self, tmp_dir):
        mock = tmp_dir / "test.mock"
        mock.write_text("{}")
        result = process_file(str(mock), str(tmp_dir), verbose=False)
        assert result is None


class TestProcessDirectory:
    def test_process_empty_dir(self, tmp_dir):
        input_dir = tmp_dir / "Input_Master"
        input_dir.mkdir()
        data_dir = tmp_dir / "_data"
        data_dir.mkdir()
        results = process_directory(str(input_dir), str(data_dir), verbose=False)
        assert len(results) == 0

    def test_process_with_files(self, tmp_dir):
        input_dir = tmp_dir / "Input_Master"
        input_dir.mkdir()
        (input_dir / "a.pptx").write_bytes(b"PK" + b"\x00" * 50)
        (input_dir / "b.pdf").write_bytes(b"%PDF" + b"\x00" * 50)

        data_dir = tmp_dir / "_data"
        data_dir.mkdir()

        results = process_directory(str(input_dir), str(data_dir), verbose=False)
        assert len(results) == 2

        # Check manifest
        manifest = json.loads((data_dir / "lineage_manifest.json").read_text())
        assert len(manifest["assets"]) == 2

    @pytest.mark.integration
    def test_end_to_end_pipeline(self, tmp_dir):
        """Integration test: full ingestion pipeline."""
        input_dir = tmp_dir / "Input_Master"
        input_dir.mkdir()
        data_dir = tmp_dir / "_data"
        data_dir.mkdir()

        import os as _os

        # Drop asset
        asset = input_dir / "deck.pptx"
        asset.write_bytes(b"PK\x03\x04" + _os.urandom(200))

        # Process
        results = process_directory(str(input_dir), str(data_dir), verbose=False)
        assert len(results) == 1

        # Verify .mock exists
        mock_path = asset.with_suffix(".pptx.mock")
        assert mock_path.exists()

        # Verify manifest
        manifest = json.loads((data_dir / "lineage_manifest.json").read_text())
        assert manifest["assets"][0]["filename"] == "deck.pptx"
        assert len(manifest["assets"][0]["sha256"]) == 64
