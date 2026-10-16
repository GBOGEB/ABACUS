import importlib.util
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "scripts" / "method_qualification.py"
spec = importlib.util.spec_from_file_location("method_qualification", p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def sample():
    return dict(
        repository="GBOGEB/ABACUS",
        source_sha="a" * 40,
        method_id="security-sast",
        tool_version="1.0.0",
        config_digest="b" * 64,
        corpus_digest="c" * 64,
        run_id=1,
        job_id=2,
        attempt=1,
        tp=1,
        fp=0,
        fn=0,
        tn=1,
        runtime_seconds=0.1,
        repair_receipt=None,
        negative_controls_pass=False,
        federation_receipts=[],
        adaptive_receipt=None,
    )


def federation_receipt(receipt_id, repository, sha):
    return {
        "receipt_id": receipt_id,
        "repository": repository,
        "source_sha": sha,
        "method_id": "security-sast",
        "applicable": True,
        "independent": True,
    }


def test_unknown_fails_closed():
    e = sample()
    del e["job_id"]
    assert m.qualify(e)["state"] == "UNKNOWN"


def test_blank_or_malformed_identity_is_invalid():
    for key, value in (
        ("repository", ""),
        ("source_sha", ""),
        ("source_sha", "g" * 40),
        ("method_id", ""),
        ("method_id", "unregistered"),
        ("tool_version", ""),
        ("config_digest", "short"),
        ("corpus_digest", "z" * 64),
        ("run_id", 0),
        ("job_id", -1),
        ("attempt", 0),
    ):
        e = sample()
        e[key] = value
        result = m.qualify(e)
        assert result["state"] == "INVALID", (key, value, result)
        assert result["level"] == "M0"


def test_m2_not_repair():
    assert m.qualify(sample())["level"] == "M2"


def test_m4_negative_and_repair():
    e = sample()
    e.update(repair_receipt="root", negative_controls_pass=True)
    assert m.qualify(e)["level"] == "M4"


def test_negative_control_must_be_actual_boolean():
    e = sample()
    e.update(repair_receipt="root", negative_controls_pass="false")
    result = m.qualify(e)
    assert result["state"] == "INVALID"
    assert result["level"] == "M0"


def test_false_negative_blocks_m4():
    e = sample()
    e.update(fn=1, repair_receipt="root", negative_controls_pass=True)
    assert m.qualify(e)["level"] == "M3"


def test_federation_receipts_require_lineage_and_independence():
    e = sample()
    e.update(
        repair_receipt="root",
        negative_controls_pass=True,
        federation_receipts=["CODEX", "QPS"],
    )
    assert m.qualify(e)["level"] == "M4"

    e["federation_receipts"] = [
        federation_receipt("r1", "GBOGEB/CODEX", "d" * 40),
        federation_receipt("r2", "GBOGEB/CODEX", "e" * 40),
    ]
    assert m.qualify(e)["level"] == "M4"

    e["federation_receipts"] = [
        federation_receipt("r1", "GBOGEB/CODEX", "d" * 40),
        federation_receipt("r2", "GBOGEB/cryoplant-project", "e" * 40),
    ]
    assert m.qualify(e)["level"] == "M5"


def test_m6_requires_comparative_adaptive_receipt_and_is_not_admission():
    e = sample()
    e.update(
        repair_receipt="root",
        negative_controls_pass=True,
        federation_receipts=[
            federation_receipt("r1", "GBOGEB/CODEX", "d" * 40),
            federation_receipt("r2", "GBOGEB/cryoplant-project", "e" * 40),
        ],
        adaptive_receipt="trial",
    )
    assert m.qualify(e)["level"] == "M5"

    e["adaptive_receipt"] = {
        "source_sha": e["source_sha"],
        "method_id": e["method_id"],
        "baseline_receipt": "baseline-1",
        "candidate_receipt": "candidate-1",
        "metric": "false_negative_rate",
        "delta": -0.1,
        "improved": True,
    }
    result = m.qualify(e)
    assert result["level"] == "M6"
    assert result["merge_authorized"] is False


def test_adaptive_receipt_wrong_source_or_no_improvement_stays_m5():
    e = sample()
    e.update(
        repair_receipt="root",
        negative_controls_pass=True,
        federation_receipts=[
            federation_receipt("r1", "GBOGEB/CODEX", "d" * 40),
            federation_receipt("r2", "GBOGEB/cryoplant-project", "e" * 40),
        ],
        adaptive_receipt={
            "source_sha": "f" * 40,
            "method_id": "security-sast",
            "baseline_receipt": "b",
            "candidate_receipt": "c",
            "metric": "precision",
            "delta": 0.1,
            "improved": True,
        },
    )
    assert m.qualify(e)["level"] == "M5"
    e["adaptive_receipt"]["source_sha"] = e["source_sha"]
    e["adaptive_receipt"]["improved"] = False
    assert m.qualify(e)["level"] == "M5"


def test_negative_count_invalid():
    e=sample();e["tp"]=-1
    assert m.qualify(e)["state"]=="INVALID"


def test_optional_receipts_absent_do_not_poison_m2():
    assert m.qualify(sample())["level"] == "M2"


def test_all_zero_confusion_matrix_is_unknown():
    e = sample()
    e.update(tp=0, fp=0, fn=0, tn=0)
    assert m.qualify(e)["state"] == "UNKNOWN"


def test_missing_required_field_is_unknown():
    e = sample()
    e.pop("corpus_digest")
    assert "corpus_digest" in m.qualify(e)["missing"]


def test_malformed_payload_is_invalid():
    assert m.qualify(None)["state"] == "INVALID"


def test_receipt_string_does_not_count_as_independent_federation():
    e = sample()
    e.update(
        repair_receipt="root", negative_controls_pass=True,
        federation_receipts="CODEX-QPS", adaptive_receipt="trial",
    )
    assert m.qualify(e)["state"] == "INVALID"


def test_boolean_control_cannot_be_truthy_string():
    e = sample()
    e.update(repair_receipt="root", negative_controls_pass="false")
    assert m.qualify(e)["state"] == "INVALID"


def test_duplicate_or_blank_receipt_is_invalid():
    e = sample()
    e["federation_receipts"] = ["CODEX", "CODEX"]
    assert m.qualify(e)["state"] == "INVALID"
    e["federation_receipts"] = ["CODEX", ""]
    assert m.qualify(e)["state"] == "INVALID"


def test_forged_or_malformed_identity_is_invalid():
    for key, bad in (
        ("source_sha", "abc"),
        ("config_digest", "bad"),
        ("corpus_digest", "invalid"),
        ("run_id", True),
        ("job_id", 0),
        ("attempt", -1),
    ):
        e = sample()
        e[key] = bad
        assert m.qualify(e)["state"] == "INVALID", key


def test_nan_inf_and_boolean_runtime_rejected():
    for value in (float("nan"), float("inf"), float("-inf"), True):
        e = sample()
        e["runtime_seconds"] = value
        assert m.qualify(e)["state"] == "INVALID"


def test_receipt_only_claim_is_not_native_or_root_closure():
    e = sample()
    e.update(
        repair_receipt="root", negative_controls_pass=True,
        federation_receipts=["CODEX", "QPS"], adaptive_receipt="trial",
    )
    result = m.qualify(e)
    assert result["level"] == "M6"
    assert result["qualification_status"] == "PROVISIONAL_NOT_NATIVE_VERIFIED"
    assert result["native_verified"] is False
    assert result["root_closed"] is False
    assert result["merge_authorized"] is False
