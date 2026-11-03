"""Behaviour tests for qps/human_rendition/w276/validate_review_profile.py."""

import copy
import json
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load(
    "qps/human_rendition/w276/validate_review_profile.py",
    name="abn_validate_review_profile",
)


def _valid():
    return dict(
        schema="abacus-qps-human-rendition-profile/1.0",
        authority="PRESENTATION_AND_REVIEW_UX_ONLY",
        tabs=sorted(mod.REQ_TABS),
        densities={
            name: dict(primary_question="Q?", max_primary_cards=2)
            for name in sorted(mod.REQ_DENSITIES)
        },
        forbidden_authority_fields=sorted(mod.FORBIDDEN),
        formal_credit_delta=0,
    )


def test_valid_profile_has_no_errors():
    assert mod.validate(_valid()) == []


def test_empty_profile_reports_every_top_level_error():
    assert mod.validate({}) == [
        "schema",
        "authority",
        "tabs",
        "densities",
        "forbidden_authority_fields",
        "formal_credit",
    ]


@pytest.mark.parametrize(
    "key,value,expected",
    [
        ("schema", "other/1.0", "schema"),
        ("authority", "ENGINEERING", "authority"),
        ("tabs", ["overview"], "tabs"),
        ("forbidden_authority_fields", [], "forbidden_authority_fields"),
        ("formal_credit_delta", 1, "formal_credit"),
    ],
)
def test_single_field_violation(key, value, expected):
    data = _valid()
    data[key] = value
    assert mod.validate(data) == [expected]


def test_density_entries_validated_individually():
    data = _valid()
    data["densities"]["clean"]["primary_question"] = ""
    data["densities"]["dense"]["max_primary_cards"] = 0
    del data["densities"]["balanced"]["max_primary_cards"]
    errors = mod.validate(data)
    assert sorted(errors) == ["density_balanced", "density_clean", "density_dense"]


def test_wrong_density_keys_reported_and_extra_checked():
    data = _valid()
    data["densities"]["extra"] = dict(primary_question="q", max_primary_cards="3")
    errors = mod.validate(data)
    assert errors == ["densities"]


def _run_main(monkeypatch, tmp_path, payload):
    path = tmp_path / "profile.json"
    path.write_bytes(json.dumps(payload).encode("utf-8"))
    monkeypatch.setattr(sys, "argv", ["validate_review_profile.py", str(path)])
    return mod.main()


def test_main_passes_valid_profile(monkeypatch, tmp_path, capsys):
    assert _run_main(monkeypatch, tmp_path, _valid()) == 0
    report = json.loads(capsys.readouterr().out)
    assert report == {"errors": [], "passed": True}


def test_main_fails_invalid_profile(monkeypatch, tmp_path, capsys):
    data = copy.deepcopy(_valid())
    data["formal_credit_delta"] = 5
    assert _run_main(monkeypatch, tmp_path, data) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["passed"] is False
    assert report["errors"] == ["formal_credit"]
