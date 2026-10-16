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


def federation_receipt(repo, rid):
    return {
        "receipt_id": rid,
        "repository": repo,
        "source_sha": "d" * 40,
        "method_id": "security-sast",
        "applicable": True,
        "independent": True,
    }


def adaptive_receipt():
    return {
        "source_sha": "a" * 40,
        "method_id": "security-sast",
        "baseline_receipt": "base-1",
        "candidate_receipt": "candidate-1",
        "metric": "recall",
        "delta": 0.05,
        "improved": True,
    }


def test_unknown_fails_closed():
    e = sample()
    del e["job_id"]
    assert m.qualify(e)["state"] == "UNKNOWN"


def test_blank_and_malformed_identity_stays_m0():
    for key, value in (
        ("repository", ""),
        ("source_sha", ""),
        ("source_sha", "not-a-sha"),
        ("method_id", ""),
        ("method_id", "not-registered"),
        ("tool_version", ""),
        ("config_digest", "short"),
        ("corpus_digest", "short"),
        ("run_id", 0),
        ("job_id", -1),
        ("attempt", 0),
    ):
        e = sample()
        e[key] = value
        result = m.qualify(e)
        assert result["state"] == "INVALID"
        assert result["level"] == "M0"
        assert result["merge_authorized"] is False


def test_m2_not_repair():
    assert m.qualify(sample())["level"] == "M2"


def test_m4_negative_and_repair():
    e = sample()
    e.update(repair_receipt="root", negative_controls_pass=True)
    assert m.qualify(e)["level"] == "M4"


def test_false_negative_blocks_m4():
    e = sample()
    e.update(fn=1, repair_receipt="root", negative_controls_pass=True)
    assert m.qualify(e)["level"] == "M3"


def test_string_false_negative_control_is_invalid_not_truthy():
    e = sample()
    e.update(repair_receipt="root", negative_controls_pass="false")
    result = m.qualify(e)
    assert result["state"] == "INVALID"
    assert result["level"] == "M0"


def test_malformed_federation_receipts_do_not_award_m5():
    e = sample()
    e.update(
        repair_receipt="root",
        negative_controls_pass=True,
        federation_receipts=["x", "y"],
        adaptive_receipt="trial",
    )
    assert m.qualify(e)["level"] == "M4"

    e["federation_receipts"] = [
        federation_receipt("GBOGEB/CODEX", "same"),
        federation_receipt("GBOGEB/CODEX", "same"),
    ]
    assert m.qualify(e)["level"] == "M4"


def test_valid_independent_receipts_award_m5_but_not_m6_without_comparison():
    e = sample()
    e.update(
        repair_receipt="root",
        negative_controls_pass=True,
        federation_receipts=[
            federation_receipt("GBOGEB/CODEX", "codex-1"),
            federation_receipt("GBOGEB/cryoplant-project", "qps-1"),
        ],
        adaptive_receipt={"trial": True},
    )
    assert m.qualify(e)["level"] == "M5"


def test_m6_requires_source_bound_adaptive_improvement_receipt():
    e = sample()
    e.update(
        repair_receipt="root",
        negative_controls_pass=True,
        federation_receipts=[
            federation_receipt("GBOGEB/CODEX", "codex-1"),
            federation_receipt("GBOGEB/cryoplant-project", "qps-1"),
        ],
        adaptive_receipt=adaptive_receipt(),
    )
    result = m.qualify(e)
    assert result["level"] == "M6"
    assert result["merge_authorized"] is False

    bad = sample()
    bad.update(
        repair_receipt="root",
        negative_controls_pass=True,
        federation_receipts=e["federation_receipts"],
        adaptive_receipt={**adaptive_receipt(), "source_sha": "e" * 40},
    )
    assert m.qualify(bad)["level"] == "M5"


def test_negative_count_invalid():
    e = sample()
    e["tp"] = -1
    assert m.qualify(e)["state"] == "INVALID"
