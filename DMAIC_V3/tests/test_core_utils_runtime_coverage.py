"""Behavioral coverage for real DMAIC runtime utility branches (C2)."""

import hashlib
import json
import logging
from datetime import datetime

import pytest

from DMAIC_V3.core import utils


def test_hashes_are_stable_across_mapping_order_and_file_chunks(tmp_path):
    value = {"z": 2, "a": ["x", 4]}
    assert utils.compute_hash(value) == utils.compute_hash({"a": ["x", 4], "z": 2})
    assert utils.compute_hash("payload") == utils.compute_hash(b"payload")
    assert utils.compute_hash([1, 2]) == hashlib.sha256(b"[1, 2]").hexdigest()
    path = tmp_path / "payload.bin"
    payload = b"abc" * 2048
    path.write_bytes(payload)
    assert utils.compute_file_hash(path) == hashlib.sha256(payload).hexdigest()


def test_ensure_directory_and_json_roundtrip(tmp_path):
    directory = utils.ensure_directory(tmp_path / "nested" / "data")
    assert directory.is_dir()
    target = directory / "result.json"
    assert utils.safe_read_json(target) is None
    source = {"when": datetime(2026, 1, 2, 3, 4, 5), "count": 4}
    assert utils.safe_write_json(source, target)
    assert json.loads(target.read_text(encoding="utf-8")) == {
        "when": "2026-01-02 03:04:05",
        "count": 4,
    }
    assert utils.safe_read_json(target)["count"] == 4
    assert utils.save_json is utils.safe_write_json
    assert utils.read_json is utils.safe_read_json


def test_json_corruption_is_rejected_and_temp_file_is_cleaned(tmp_path, monkeypatch):
    target = tmp_path / "output.json"
    target.write_text("{bad-json", encoding="utf-8")
    assert utils.safe_read_json(target) is None

    def deny_move(_src, _dst):
        raise OSError("simulated replace error")

    monkeypatch.setattr(utils.shutil, "move", deny_move)
    assert utils.safe_write_json({"fresh": True}, target) is False
    assert target.read_text(encoding="utf-8") == "{bad-json"
    assert not target.with_suffix(".tmp").exists()


def test_path_and_permissions_validation(tmp_path, monkeypatch):
    directory = utils.ensure_directory(tmp_path / "root")
    existing = directory / "sample.txt"
    existing.write_text("contents", encoding="utf-8")
    missing = directory / "missing.txt"
    assert utils.validate_path_exists(existing)
    assert not utils.validate_path_exists(missing, "required input")
    assert utils.validate_file_readable(existing)
    assert not utils.validate_file_readable(directory)
    assert utils.validate_directory_writable(directory)
    assert not utils.validate_directory_writable(missing)
    with monkeypatch.context() as patch:
        patch.setattr(utils.os, "access", lambda *_: False)
        assert not utils.validate_file_readable(existing)
        assert not utils.validate_directory_writable(directory)


def test_recursive_sizes_and_zero_length_files(tmp_path):
    (tmp_path / "empty").write_bytes(b"")
    nested = utils.ensure_directory(tmp_path / "nested")
    (nested / "blob.bin").write_bytes(b"a" * 2048)
    assert utils.get_file_size_mb(nested / "blob.bin") == pytest.approx(2048 / 1048576)
    assert utils.get_directory_size_mb(tmp_path) == pytest.approx(2048 / 1048576)


def test_copy_file_and_archive_report_actual_disk_results(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("current", encoding="utf-8")
    destination = tmp_path / "out.txt"
    assert utils.copy_file_with_backup(source, destination)
    assert destination.read_text(encoding="utf-8") == "current"
    assert not utils.copy_file_with_backup(tmp_path / "missing.txt", destination)
    directory = utils.ensure_directory(tmp_path / "archive-src")
    (directory / "record.txt").write_text("record", encoding="utf-8")
    archive = tmp_path / "archives" / "bundle.zip"
    assert utils.archive_directory(directory, archive)
    assert archive.is_file()


def test_archive_failure_is_not_reported_as_success(tmp_path, monkeypatch):
    def reject_archive(*_args, **_kwargs):
        raise OSError("unavailable archive destination")

    monkeypatch.setattr(utils.shutil, "make_archive", reject_archive)
    assert utils.archive_directory(tmp_path, tmp_path / "output" / "bundle.zip") is False


def test_durations_timestamps_and_invalid_parse():
    assert utils.format_duration(3661.9) == "1h 1m 1s"
    assert utils.format_duration(90) == "1m 30s"
    assert utils.format_duration(9) == "9s"
    when = datetime(2026, 10, 16, 9, 30, 0)
    assert utils.format_timestamp(when) == "2026-10-16 09:30:00"
    assert datetime.strptime(utils.format_timestamp(), "%Y-%m-%d %H:%M:%S")
    assert utils.parse_timestamp("2026-10-16T09:30:00") == when
    assert utils.parse_timestamp("2026-10-16 09:30:00") == when
    assert utils.parse_timestamp("this is not a timestamp") is None


def test_truncation_sanitization_and_relative_paths(tmp_path):
    assert utils.truncate_string("exact", max_length=5) == "exact"
    assert utils.truncate_string("0123456789", max_length=7) == "0123..."
    assert utils.truncate_string("abcdefgh", max_length=5, suffix="~") == "abcd~"
    assert utils.sanitize_filename('a<>:"/\\|?*b') == "a_________b"
    base = tmp_path / "base"
    child = base / "nested" / "file.txt"
    assert utils.get_relative_path(child, base).as_posix() == "nested/file.txt"
    assert utils.get_relative_path(tmp_path / "outside.txt", base) == tmp_path / "outside.txt"


def test_file_logger_writes_evidence_to_selected_file(tmp_path):
    log_file = tmp_path / "log" / "runtime.log"
    logger = utils.setup_logger("dmaic-utils-c2-test", log_file=log_file, level=logging.DEBUG)
    try:
        logger.info("recorded C2 path")
        for handler in logger.handlers:
            handler.flush()
        assert "recorded C2 path" in log_file.read_text(encoding="utf-8")
        assert logger.level == logging.DEBUG
    finally:
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)


def test_copy_existing_destination_creates_backup_before_replace(tmp_path):
    source = tmp_path / "source.txt"
    destination = tmp_path / "out.txt"
    source.write_text("new", encoding="utf-8")
    destination.write_text("old", encoding="utf-8")

    assert utils.copy_file_with_backup(source, destination)
    assert destination.read_text(encoding="utf-8") == "new"
    assert destination.with_suffix(".txt.bak").read_text(encoding="utf-8") == "old"
