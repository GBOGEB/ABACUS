"""Behaviour tests for scripts/dmaic_metrics_dump.py."""

import csv

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("scripts/dmaic_metrics_dump.py", name="abn_w4_dmaic_metrics_dump")


def _read_rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_dump_writes_header_and_rows_creating_nested_dir(tmp_path):
    out_dir = tmp_path / "a" / "b"
    metrics = [
        {"phase": "define", "score": 1.5},
        {"phase": "measure", "score": 2},
    ]
    assert mod.dump_dmaic_metrics(metrics, str(out_dir)) is None
    target = out_dir / "dmaic_metrics.csv"
    assert target.is_file()
    rows = _read_rows(target)
    assert rows == [
        {"phase": "define", "score": "1.5"},
        {"phase": "measure", "score": "2"},
    ]


def test_dump_uses_first_row_keys_as_columns(tmp_path):
    metrics = [{"b": 1, "a": 2}, {"a": 3, "b": 4}]
    mod.dump_dmaic_metrics(metrics, str(tmp_path))
    with open(tmp_path / "dmaic_metrics.csv", newline="", encoding="utf-8") as fh:
        header = next(csv.reader(fh))
    assert header == ["b", "a"]


def test_dump_empty_metrics_writes_blank_header(tmp_path):
    mod.dump_dmaic_metrics([], str(tmp_path))
    data = (tmp_path / "dmaic_metrics.csv").read_bytes()
    assert data.strip() == b""


def test_dump_overwrites_existing_file(tmp_path):
    mod.dump_dmaic_metrics([{"k": "old"}], str(tmp_path))
    mod.dump_dmaic_metrics([{"k": "new"}], str(tmp_path))
    assert _read_rows(tmp_path / "dmaic_metrics.csv") == [{"k": "new"}]
