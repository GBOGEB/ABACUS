import json
from pathlib import Path

import pytest

from dow_phase2_statistics import measure
from dow_phase3_reporting import report


def fixture_csv(tmp_path: Path) -> Path:
    path = tmp_path / "data.csv"
    path.write_text(
        "group,score\ntest_a,95.5\ntest_a,94.2\ntest_b,88.7\ntest_b,89.1\n",
        encoding="utf-8",
    )
    return path


def test_valid_roundtrip_and_nonempty_outputs(tmp_path):
    source = fixture_csv(tmp_path)
    meta_path = measure(source, tmp_path / "dow_output")
    assert meta_path.stat().st_size > 0
    metadata = json.loads(meta_path.read_text())
    assert set(metadata["groups"]) == {"test_a", "test_b"}
    assert metadata["semantics_status"] == "PROVISIONAL_REVIEW_REQUIRED"
    assert metadata["merge_admission"] == "HOLD"
    outputs = report(meta_path, tmp_path / "phase3_reports")
    assert all(path.exists() and path.stat().st_size > 0 for path in outputs)
    assert (
        json.loads(outputs[0].read_text())["metadata_receipt_sha256"]
        == metadata["receipt_sha256"]
    )


def test_determinism_for_identical_input(tmp_path):
    source = fixture_csv(tmp_path)
    a = measure(source, tmp_path / "r1").read_bytes()
    b = measure(source, tmp_path / "r2").read_bytes()
    assert a == b


@pytest.mark.parametrize(
    "data",
    [
        "",
        "other,score\na,1\n",
        "group,score\na,1\nb,2\n",
        "group,score\na,1\na,nan\nb,2\nb,3\n",
        "group,score\na,1\na,x\nb,2\nb,3\n",
    ],
)
def test_invalid_csv_fails_closed(tmp_path, data):
    source = tmp_path / "bad.csv"
    source.write_text(data)
    with pytest.raises(ValueError):
        measure(source, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_alpha_boundaries(tmp_path):
    source = fixture_csv(tmp_path)
    for alpha in (0.0, 1.0, float("nan")):
        with pytest.raises(ValueError):
            measure(source, tmp_path / "out", alpha)


def test_rejects_modified_receipt(tmp_path):
    source = fixture_csv(tmp_path)
    path = measure(source, tmp_path / "out")
    data = json.loads(path.read_text())
    data["groups"]["test_a"]["mean"] += 3
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="digest mismatch"):
        report(path, tmp_path / "reports")
    assert not (tmp_path / "reports").exists()


def test_rejects_unreadable_metadata(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{")
    with pytest.raises(ValueError):
        report(path, tmp_path / "reports")


def test_rejects_missing_metadata(tmp_path):
    with pytest.raises(FileNotFoundError):
        report(tmp_path / "no.json", tmp_path / "reports")


def test_group_count_bounded(tmp_path):
    source = tmp_path / "many_groups.csv"
    source.write_text("group,score\n" + "".join(f"g{i},1\ng{i},2\n" for i in range(33)))
    with pytest.raises(ValueError, match="at most 32 groups"):
        measure(source, tmp_path / "out")
    assert not (tmp_path / "out").exists()
