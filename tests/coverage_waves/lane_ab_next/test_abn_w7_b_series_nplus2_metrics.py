"""Gap tests for scripts/b_series_nplus2_metrics.py (fail-closed guards, main)."""

import copy
import json
from pathlib import Path

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

core = load("scripts/b_series_temporal_metrics.py", name="abn_w7_bseries_core")
nplus1 = load(
    "scripts/b_series_nplus1_metrics.py",
    name="abn_w7_bseries_nplus1",
    deps={"b_series_temporal_metrics": core},
)
mod = load(
    "scripts/b_series_nplus2_metrics.py",
    name="abn_w7_bseries_nplus2",
    deps={"b_series_temporal_metrics": core, "b_series_nplus1_metrics": nplus1},
)
DOCS = Path(mod.__file__).resolve().parents[1] / "docs" / "ci"
DATA_PATH = str(DOCS / "B_SERIES_NATIVE_NPLUS2_20261017.json")
PRIOR_PATH = str(DOCS / "B_SERIES_NATIVE_NPLUS1_20261017.json")
B1_PATH = str(DOCS / "B_SERIES_B1_FINGERPRINT_CENSUS_20261017.json")


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


DATA = _read(DATA_PATH)
PRIOR = _read(PRIOR_PATH)
B1 = _read(B1_PATH)


def _run(data=None, prior=None, b1=None):
    return mod.extend(
        copy.deepcopy(DATA) if data is None else data,
        copy.deepcopy(PRIOR) if prior is None else prior,
        copy.deepcopy(B1) if b1 is None else b1,
    )


def _both(field, ref_field, value):
    data = copy.deepcopy(DATA)
    b1 = copy.deepcopy(B1)
    data["observations"][-1][field] = value
    b1["comparison"][-1][ref_field] = value
    return data, b1


def test_expected_fingerprint_rejects_non_dict():
    with pytest.raises(core.EvidenceError, match="invalid fingerprint atom"):
        mod._expected_fingerprint(["x"])


def test_expected_fingerprint_rejects_unsorted_patterns():
    atom = {"path": ".github/workflows/a.yml", "line": 3}
    atom.update(patterns=["b", "a"], text="run: x")
    with pytest.raises(core.EvidenceError, match="invalid native finding"):
        mod._expected_fingerprint(atom)


def test_finite_fraction_rejects_negative():
    with pytest.raises(core.EvidenceError, match="negative B1 detection"):
        mod._finite_fraction(-1, 5)


def test_unbound_lineage_rejected():
    data = copy.deepcopy(DATA)
    data["extension"] = "OTHER"
    with pytest.raises(core.EvidenceError, match="unbound N\\+2 lineage"):
        _run(data=data)


def test_pulse_count_mismatch_rejected():
    data = copy.deepcopy(DATA)
    data["observations"].pop()
    with pytest.raises(core.EvidenceError, match="pulse identity/order"):
        _run(data=data)


def test_prior_pulse_count_mismatch_rejected():
    prior = copy.deepcopy(PRIOR)
    prior["observations"].pop()
    with pytest.raises(core.EvidenceError, match="prior four-pulse"):
        _run(prior=prior)


def test_unqualified_ledger_schema_rejected():
    b1 = copy.deepcopy(B1)
    b1["schema"] = "other"
    with pytest.raises(core.EvidenceError, match="unqualified fingerprint ledger"):
        _run(b1=b1)


def test_ledger_authority_transfer_rejected():
    b1 = copy.deepcopy(B1)
    b1["authority_transfer"] = True
    with pytest.raises(core.EvidenceError, match="authority transfer"):
        _run(b1=b1)


def test_incomplete_comparisons_rejected():
    b1 = copy.deepcopy(B1)
    b1["comparison"].pop()
    with pytest.raises(core.EvidenceError, match="incomplete native B1"):
        _run(b1=b1)


def test_b1_job_identity_mismatch_rejected():
    b1 = copy.deepcopy(B1)
    b1["comparison"][-1]["b1_job_id"] = 1
    with pytest.raises(core.EvidenceError, match="B1 job identity mismatch"):
        _run(b1=b1)


def test_unreconciled_findings_rejected():
    data, b1 = _both("b1_allowed_count", "allowed_findings", 46)
    with pytest.raises(core.EvidenceError, match="do not reconcile"):
        _run(data=data, b1=b1)


def test_negative_new_fingerprints_rejected():
    data, b1 = _both("b1_new_fingerprints", "new_fingerprints", -1)
    with pytest.raises(core.EvidenceError, match="invalid fingerprint intersection"):
        _run(data=data, b1=b1)


def test_population_join_failure_rejected():
    data, b1 = _both("b1_new_fingerprints", "new_fingerprints", 1)
    with pytest.raises(core.EvidenceError, match="population does not join"):
        _run(data=data, b1=b1)


def test_scanner_configuration_drift_rejected():
    data = copy.deepcopy(DATA)
    row = data["observations"][-1]
    row["b1_max_unguarded"] = 268
    row["b1_source_config_identity"] = ":".join(
        [row["b1_scanner_blob_sha"], row["b0_workflow_blob_sha"], "268"]
    )
    with pytest.raises(core.EvidenceError, match="configuration identity drift"):
        _run(data=data)


def test_nonmonotonic_b1_clocks_rejected():
    data = copy.deepcopy(DATA)
    rows = data["observations"]
    rows[-1]["b1_observation_at"] = rows[-2]["b1_observation_at"]
    with pytest.raises(core.EvidenceError, match="nonmonotonic B1 clocks"):
        _run(data=data)


def test_main_writes_result_and_prints_status(tmp_path, capsys):
    out = tmp_path / "nested" / "out.json"
    rc = mod.main(
        [
            "--observed",
            DATA_PATH,
            "--prior",
            PRIOR_PATH,
            "--fingerprints",
            B1_PATH,
            "--out",
            str(out),
        ]
    )
    assert rc == 0
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["schema"] == mod.SCHEMA
    assert written["merge_admission"] == "HOLD"
    status = json.loads(capsys.readouterr().out)
    assert status == {
        "status": "PERSISTENT_FINGERPRINTS_WITH_SCOPE_DRIFT",
        "pulses": 5,
        "admission": "HOLD",
    }
