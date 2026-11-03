"""Gap tests for scripts/proposal_compatibility.py (error paths and CLI)."""

import copy
import json
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("scripts/proposal_compatibility.py", name="abn_w7_proposal_compat")

SHA = "a" * 40

CONTRACT = dict(
    required_fields=["method", "source_sha", "scope"],
    compatible_methods=["MIP", "DAB"],
    risk_classes=["MEASURED"],
    proposal_types=["PRESSURE_QUEUE"],
    mutation_modes=["READ_ONLY_PROPOSAL"],
    worker_model=dict(
        proposal_workers=dict(min=2, max=8, mode="READ_ONLY", scalable=True),
        mutation_writer=dict(count=1, required_for_mutation=True),
    ),
    coverage_growth=dict(required_fields=["applicability", "result"]),
)


def _envelope(tmp_path):
    evidence = tmp_path / "evidence.json"
    evidence.write_bytes(b"{}")
    return mod.emit_mip(SHA, evidence)


def test_load_json_rejects_non_object(tmp_path):
    path = tmp_path / "list.json"
    path.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(ValueError, match="expected JSON object"):
        mod.load_json(path)


def test_emitted_envelope_is_valid(tmp_path):
    assert mod.validate_envelope(_envelope(tmp_path), CONTRACT) == []


def test_validate_envelope_reports_every_top_level_violation():
    envelope = dict(
        method="OTHER",
        source_sha="XYZ",
        risk_class="?",
        proposal_type="?",
        mutation_mode="?",
        worker_model=["not", "a", "dict"],
        authority=dict(
            authority_transfer=True,
            formal_credit_delta=2,
            engineering_credit_delta=3,
        ),
        coverage_growth={},
    )
    errors = mod.validate_envelope(envelope, CONTRACT)
    assert errors == sorted(
        [
            "missing:scope",
            "method",
            "source_sha",
            "risk_class",
            "proposal_type",
            "mutation_mode",
            "worker_model",
            "authority_transfer",
            "formal_credit_delta",
            "engineering_credit_delta",
            "coverage_growth:applicability",
            "coverage_growth:result",
        ]
    )


def test_validate_envelope_flags_non_dict_worker_parts(tmp_path):
    envelope = _envelope(tmp_path)
    envelope["worker_model"] = dict(proposal_workers=None, mutation_writer="x")
    errors = mod.validate_envelope(envelope, CONTRACT)
    assert errors == ["mutation_writer", "proposal_workers"]


def test_validate_envelope_flags_worker_bounds_and_writer(tmp_path):
    envelope = _envelope(tmp_path)
    envelope["worker_model"] = dict(
        proposal_workers=dict(min=9, max=4, mode="WRITE", scalable=False),
        mutation_writer=dict(count=2, required_for_mutation=False),
    )
    contract = copy.deepcopy(CONTRACT)
    contract["worker_model"]["proposal_workers"]["max"] = 3
    errors = mod.validate_envelope(envelope, contract)
    assert errors == [
        "mutation_writer.count",
        "mutation_writer.required_for_mutation",
        "proposal_workers.max",
        "proposal_workers.mode",
        "proposal_workers.range",
        "proposal_workers.scalable",
    ]


def test_validate_envelope_rejects_boolean_worker_counts(tmp_path):
    envelope = _envelope(tmp_path)
    envelope["worker_model"]["proposal_workers"]["min"] = True
    envelope["worker_model"]["proposal_workers"]["max"] = False
    envelope["worker_model"]["mutation_writer"]["count"] = True
    errors = mod.validate_envelope(envelope, CONTRACT)
    assert errors == [
        "mutation_writer.count",
        "proposal_workers.max",
        "proposal_workers.min",
    ]


def _queue(**overrides):
    payload = dict(
        schema_version="abacus-dab-proposal-queue/1.1.0",
        source_sha=SHA,
        measurement=dict(total=3, families=dict(E501=2, F401=1)),
        protected_holds=dict(E501=dict(count=2), F401=dict(count=1)),
        worker_model=dict(
            proposal_workers=dict(min=2, max=8, mode="READ_ONLY"),
            mutation_writer_count=1,
            parallel_proposals_allowed=True,
            parallel_mutation_for_same_scope_allowed=False,
        ),
        governance=dict(
            authority_transfer=False,
            formal_credit_delta=0,
            engineering_credit_delta=0,
        ),
        proposals=[],
    )
    payload.update(overrides)
    return payload


def test_valid_empty_queue_accepts_fully_held_measurement():
    assert mod.valid_empty_queue(_queue()) is True


def test_valid_empty_queue_accepts_zero_total():
    zero = _queue(
        measurement=dict(total=0, families=dict(E501=0)),
        protected_holds=dict(E501=dict(count=0)),
    )
    assert mod.valid_empty_queue(zero) is True


@pytest.mark.parametrize(
    "overrides",
    [
        dict(schema_version="other/1"),
        dict(source_sha="A" * 40),
        dict(source_sha=5),
        dict(measurement="nope"),
        dict(measurement=dict(total=True, families={})),
        dict(measurement=dict(total=1, families=dict(E501=-1))),
        dict(measurement=dict(total=5, families=dict(E501=2, F401=1))),
        dict(worker_model="nope"),
        dict(
            worker_model=dict(
                proposal_workers=dict(min=1, max=8, mode="READ_ONLY"),
                mutation_writer_count=1,
                parallel_proposals_allowed=True,
                parallel_mutation_for_same_scope_allowed=False,
            )
        ),
        dict(governance=dict(authority_transfer=True)),
        dict(protected_holds=dict(E501="x", F401=dict(count=1))),
        dict(protected_holds=dict(E501=dict(count=-2), F401=dict(count=1))),
        dict(protected_holds=dict(E501=dict(count=1), F401=dict(count=1))),
        dict(protected_holds=dict(E501=dict(count=0), F401=dict(count=1))),
        dict(protected_holds=dict(E501=dict(count=2))),
    ],
)
def test_valid_empty_queue_rejects_malformed(overrides):
    assert mod.valid_empty_queue(_queue(**overrides)) is False


def test_iter_envelopes_wraps_single_payload():
    single = dict(method="MIP")
    assert mod.iter_envelopes(single) == [single]


def _run(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["proposal_compatibility.py", *argv])
    return mod.main()


def _contract_file(tmp_path, contract=None):
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(contract or CONTRACT), encoding="utf-8")
    return path


def test_main_emit_mip_rejects_short_sha(monkeypatch, tmp_path):
    contract = _contract_file(tmp_path)
    evidence = tmp_path / "e.json"
    evidence.write_bytes(b"{}")
    with pytest.raises(SystemExit, match="exact SHA"):
        _run(
            monkeypatch,
            "--contract",
            str(contract),
            "emit-mip",
            "--source-sha",
            "abc",
            "--evidence",
            str(evidence),
            "--out",
            str(tmp_path / "o.json"),
        )


def test_main_emit_mip_writes_valid_envelope(monkeypatch, tmp_path, capsys):
    contract = _contract_file(tmp_path)
    evidence = tmp_path / "e.json"
    evidence.write_bytes(b"{}")
    out = tmp_path / "nested" / "mip.json"
    rc = _run(
        monkeypatch,
        "--contract",
        str(contract),
        "emit-mip",
        "--source-sha",
        SHA,
        "--evidence",
        str(evidence),
        "--out",
        str(out),
    )
    assert rc == 0
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["proposal_id"] == "MIP-" + SHA[:12]
    assert json.loads(capsys.readouterr().out) == written


def test_main_emit_mip_rejects_incompatible_contract(monkeypatch, tmp_path):
    contract = copy.deepcopy(CONTRACT)
    contract["compatible_methods"] = ["DAB"]
    path = _contract_file(tmp_path, contract)
    evidence = tmp_path / "e.json"
    evidence.write_bytes(b"{}")
    with pytest.raises(SystemExit, match="invalid emitted MIP envelope: method"):
        _run(
            monkeypatch,
            "--contract",
            str(path),
            "emit-mip",
            "--source-sha",
            SHA,
            "--evidence",
            str(evidence),
            "--out",
            str(tmp_path / "o.json"),
        )


def test_main_validate_reports_failures(monkeypatch, tmp_path, capsys):
    contract = _contract_file(tmp_path)
    good = _envelope(tmp_path)
    bad = dict(good, method="BOGUS")
    payload = tmp_path / "in.json"
    payload.write_text(json.dumps(dict(proposals=[good, "text", bad])))
    rc = _run(
        monkeypatch, "--contract", str(contract), "validate", "--input", str(payload)
    )
    assert rc == 1
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "FAIL"
    assert report["errors"] == ["1:not_object", "2:method"]


def test_main_validate_rejects_invalid_empty_queue(monkeypatch, tmp_path, capsys):
    contract = _contract_file(tmp_path)
    payload = tmp_path / "in.json"
    payload.write_text(json.dumps(dict(proposals=[], schema_version="x")))
    rc = _run(
        monkeypatch, "--contract", str(contract), "validate", "--input", str(payload)
    )
    assert rc == 1
    assert "empty_queue_receipt" in capsys.readouterr().out


def test_main_validate_passes_on_valid_queue(monkeypatch, tmp_path, capsys):
    contract = _contract_file(tmp_path)
    payload = tmp_path / "in.json"
    payload.write_text(json.dumps(_queue()))
    rc = _run(
        monkeypatch, "--contract", str(contract), "validate", "--input", str(payload)
    )
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert report == dict(status="PASS", proposals=0)
