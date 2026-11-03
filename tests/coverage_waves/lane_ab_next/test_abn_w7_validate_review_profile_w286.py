"""Gap tests for qps/visual_regression/w286/validate_review_profile.py main()."""

import json

from tests.coverage_waves.lane_b._l2_loader import load

vrp = load(
    "qps/visual_regression/w286/validate_review_profile.py",
    name="abn_w7_validate_review_profile_w286",
)


def _valid_profile():
    return {
        "schema": "abacus-qps-visual-regression-profile/1.0",
        "authority": "PRESENTATION_REVIEW_UX_ONLY",
        "review_classes": list(vrp.CLASSES),
        "dimensions": list(vrp.DIMS),
        "sample_only": True,
        "formal_credit_delta": 0,
        "forbidden_authority_fields": [
            "engineering_disposition_override",
            "compliance_override",
            "negotiation_override",
            "semantic_ssot_override",
        ],
    }


def _run(tmp_path, monkeypatch, profile):
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(profile), encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["prog", str(path)])
    return vrp.main()


def test_main_valid_profile_returns_zero(tmp_path, monkeypatch, capsys):
    assert _run(tmp_path, monkeypatch, _valid_profile()) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["errors"] == []
    assert [out[k] for k in out if k != "errors"] == [True]


def test_main_invalid_profile_returns_two(tmp_path, monkeypatch, capsys):
    profile = _valid_profile()
    profile["sample_only"] = False
    profile["forbidden_authority_fields"] = None
    assert _run(tmp_path, monkeypatch, profile) == 2
    out = json.loads(capsys.readouterr().out)
    assert out["errors"] == ["forbidden_fields", "sample_only"]
    assert [out[k] for k in out if k != "errors"] == [False]
