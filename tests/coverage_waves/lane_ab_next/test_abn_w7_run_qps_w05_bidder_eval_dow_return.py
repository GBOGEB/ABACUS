"""Gap tests for tools/run_qps_w05_bidder_eval_dow_return.py (guards, git SHA)."""

import copy
from pathlib import Path

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load(
    "tools/run_qps_w05_bidder_eval_dow_return.py", name="abn_w7_qps_w05_dow_return"
)
ROOT = Path(mod.__file__).resolve().parents[1]
BASE_REQUEST = mod.load(ROOT / mod.REQUEST)
BASE_SNAPSHOT = mod.load(ROOT / mod.SNAPSHOT)
SHA = "0123456789abcdef0123456789abcdef01234567"


def _set_corr(req, snap):
    req["correlation_id"] = "OTHER"


def _set_wave(req, snap):
    snap["source_wave"] = "OTHER-WAVE"


def _set_repo(req, snap):
    req["child"]["repository"] = "other/repo"


def _set_baseline(req, snap):
    req["child"]["baseline_sha"] = "f" * 40


def _set_bad_sha(req, snap):
    req["child"]["baseline_sha"] = "XYZ"
    snap["source_child"]["source_merge_sha"] = "XYZ"


def _set_artifact(req, snap):
    req["child"]["artifact"] = ""


def _set_artifact_sha(req, snap):
    req["child"]["artifact_sha256"] = "nothex"


def _set_redaction(req, snap):
    snap["confidentiality"]["prices_removed"] = False


def _set_ops_empty(req, snap):
    req["requested_DOW_operations"] = []


def _set_ops_dup(req, snap):
    ops = req["requested_DOW_operations"]
    req["requested_DOW_operations"] = ops + ops[:1]


def _set_bidders(req, snap):
    snap["bidders"]["BIDDER_C"] = snap["bidders"]["BIDDER_A"]


def _set_families_missing(req, snap):
    req["input_contract"]["priority_families"] = []


def _set_family_mismatch(req, snap):
    snap["bidders"]["BIDDER_B"]["family_edges"].pop("NOISE")


@pytest.mark.parametrize(
    "mutate, message",
    [
        (_set_corr, "correlation mismatch"),
        (_set_wave, "source-wave mismatch"),
        (_set_repo, "child repository mismatch"),
        (_set_baseline, "child baseline mismatch"),
        (_set_bad_sha, "invalid child baseline SHA"),
        (_set_artifact, "artifact path missing"),
        (_set_artifact_sha, "invalid child artifact SHA-256"),
        (_set_redaction, "redaction contract failed"),
        (_set_ops_empty, "non-empty string list"),
        (_set_ops_dup, "contains duplicates"),
        (_set_bidders, "exactly two anonymized"),
        (_set_families_missing, "priority families missing"),
        (_set_family_mismatch, "priority-family mismatch for BIDDER_B"),
    ],
)
def test_validate_inputs_fail_closed(mutate, message):
    req = copy.deepcopy(BASE_REQUEST)
    snap = copy.deepcopy(BASE_SNAPSHOT)
    mutate(req, snap)
    with pytest.raises(SystemExit, match=message):
        mod.validate_inputs(req, snap)


def test_load_rejects_non_mapping(tmp_path):
    path = tmp_path / "list.yaml"
    path.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="not a YAML mapping"):
        mod.load(path)


def _git(tmp_path, head):
    git = tmp_path / ".git"
    git.mkdir()
    (git / "HEAD").write_text(head, encoding="utf-8")
    return git


def test_git_sha_detached_head(tmp_path):
    _git(tmp_path, SHA + "\n")
    assert mod.git_sha(tmp_path) == SHA


def test_git_sha_loose_ref(tmp_path):
    git = _git(tmp_path, "ref: refs/heads/main\n")
    (git / "refs" / "heads").mkdir(parents=True)
    (git / "refs" / "heads" / "main").write_text(SHA + "\n", encoding="utf-8")
    assert mod.git_sha(tmp_path) == SHA


def test_git_sha_packed_ref(tmp_path):
    git = _git(tmp_path, "ref: refs/heads/main\n")
    packed = "# pack-refs\n" + SHA + " refs/heads/main\n" + "e" * 40 + " refs/x\n"
    (git / "packed-refs").write_text(packed, encoding="utf-8")
    assert mod.git_sha(tmp_path) == SHA


def test_git_sha_unresolved_packed_ref(tmp_path):
    git = _git(tmp_path, "ref: refs/heads/main\n")
    (git / "packed-refs").write_text("e" * 40 + " refs/other\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="unable to resolve"):
        mod.git_sha(tmp_path)


def test_git_sha_invalid_head(tmp_path):
    _git(tmp_path, "garbage\n")
    with pytest.raises(SystemExit, match="unable to resolve"):
        mod.git_sha(tmp_path)
