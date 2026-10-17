"""GCA-3 fail-closed request and acceptance counter regression tests."""
import copy
import json
from pathlib import Path

import pytest

from scripts import gca3_contract as gca

TEMPLATE = (
    Path(__file__).resolve().parents[1]
    / "MIP"
    / "GCA3_REQUEST_TEMPLATE.json"
)
REQ = json.loads(TEMPLATE.read_text(encoding="utf-8"))


def wave(i, *, status="PASS", gates="PASS"):
    return {
        "attempt_index": i,
        "planned_wave_n": REQ["baseline"]["accepted_n"] + i,
        "status": status,
        "pulses": [
            {"id": "U1", "status": "PASS", "evidence": ["native-job-id"]}
        ],
        "source_heads": ["a" * 40],
        "gate_results": {k: gates for k in REQ["required_gates"]},
        "engineering_dov": status == "PASS",
        "release_admission": "HOLD",
    }


def receipt(*statuses):
    rows = [wave(i, status=s) for i, s in enumerate(statuses, 1)]
    accepted = 0
    for status in statuses:
        if status != "PASS":
            break
        accepted += 1
    return {
        "schema": gca.RECEIPT,
        "mission_id": REQ["mission_id"],
        "waves": rows,
        "attempted_waves": len(rows),
        "accepted_n": REQ["baseline"]["accepted_n"] + accepted,
        "summary": "Source-bound mission result",
    }


def test_template_preflight_three_waves_and_bounded_pulses():
    out = gca.validate_request(REQ)
    assert out["planned_waves"] == 3
    assert out["target_n"] - out["from_n"] == 3
    assert out["maximum_pulses"] == 9


@pytest.mark.parametrize(
    "mutation",
    [
        lambda r: r["authority"].update(automatic_main_merge=True),
        lambda r: r["authority"].update(automatic_security_waiver=True),
        lambda r: r["authority"].update(automatic_reviewer_approval=True),
        lambda r: r["authority"].update(automatic_ruleset_relaxation=True),
        lambda r: r["budgets"].update(max_manual_unchanged_head_reruns=1),
        lambda r: r["advance"].update(target_n=999),
        lambda r: r["advance"].update(max_pulses_per_wave=9),
        lambda r: r["baseline"].update(main_sha="short"),
        lambda r: r.update(mode="persistent_background"),
    ],
)
def test_unsafe_or_unbounded_invocation_rejected(mutation):
    request = copy.deepcopy(REQ)
    mutation(request)
    with pytest.raises(ValueError):
        gca.validate_request(request)


def test_three_accepted_waves_advance_contiguously():
    v = gca.validate_receipt(receipt("PASS", "PASS", "PASS"), REQ)
    assert v["full_n_plus_3_accepted"] is True
    assert v["accepted_contiguous_waves"] == 3


def test_hold_cannot_inflate_n_plus_three():
    with pytest.raises(ValueError, match="cannot accept"):
        gca.validate_receipt(receipt("PASS", "HOLD", "PASS"), REQ)


def test_hold_retains_earlier_accepted_wave_only():
    v = gca.validate_receipt(receipt("PASS", "HOLD", "HOLD"), REQ)
    assert v["accepted_n"] == REQ["baseline"]["accepted_n"] + 1
    assert v["attempted_waves"] == 3


def test_partial_mission_requires_stop_not_silent_hold():
    v = gca.validate_receipt(receipt("PASS", "STOP"), REQ)
    assert v["full_n_plus_3_accepted"] is False
    with pytest.raises(ValueError, match="explicit STOP"):
        gca.validate_receipt(receipt("PASS", "HOLD"), REQ)


def test_forged_engineering_pass_and_incomplete_gates_rejected():
    data = receipt("PASS", "PASS", "PASS")
    data["waves"][0]["engineering_dov"] = False
    with pytest.raises(ValueError, match="engineering DoV"):
        gca.validate_receipt(data, REQ)
    data = receipt("PASS", "PASS", "PASS")
    data["waves"][0]["gate_results"].pop("security")
    with pytest.raises(ValueError, match="incomplete gate"):
        gca.validate_receipt(data, REQ)


def test_release_pass_does_not_override_security_hold():
    data = receipt("PASS", "PASS", "PASS")
    data["waves"][0]["release_admission"] = "PASS"
    data["waves"][0]["gate_results"]["security"] = "HOLD"
    with pytest.raises(ValueError, match="contradicts gate"):
        gca.validate_receipt(data, REQ)


def test_pulse_evidence_and_sequence_required():
    data = receipt("PASS", "PASS", "PASS")
    data["waves"][0]["pulses"][0].pop("evidence")
    with pytest.raises(ValueError, match="pulse evidence"):
        gca.validate_receipt(data, REQ)
    data = receipt("PASS", "PASS", "PASS")
    data["waves"][1]["attempt_index"] = 1
    with pytest.raises(ValueError, match="sequential"):
        gca.validate_receipt(data, REQ)


def test_boolean_counters_do_not_forge_completed_work():
    data = receipt("PASS", "PASS", "PASS")
    data["attempted_waves"] = True
    with pytest.raises(ValueError):
        gca.validate_receipt(data, REQ)
    data = receipt("PASS", "PASS", "PASS")
    data["accepted_n"] = True
    with pytest.raises(ValueError):
        gca.validate_receipt(data, REQ)


def test_cli_preflight(tmp_path, capsys):
    path = tmp_path / "request.json"
    path.write_text(json.dumps(REQ), encoding="utf-8")
    assert gca.main([str(path)]) == 0
    assert "NOT_AUTHORIZED_BY_REQUEST" in capsys.readouterr().out
