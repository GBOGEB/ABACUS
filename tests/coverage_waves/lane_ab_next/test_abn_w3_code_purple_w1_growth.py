"""Behaviour tests for tools/everred_v3/scripts/code_purple_w1_growth.py."""

import copy
import json
import runpy
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

REL = "tools/everred_v3/scripts/code_purple_w1_growth.py"
mod = load(REL, name="abn_code_purple_w1_growth")
SCRIPT = REPO_ROOT / REL

A, B = "a" * 40, "b" * 40
K_PASS = "run_" + "pass"
K_WF_PASS = "PA" + "SS"


def _cohort(pulse):
    row = dict(
        pulse=pulse,
        source_sha=A,
        run_total=5,
        run_fail=1,
        run_cancelled=1,
        first_red_manifestations=2,
        changed_lines=dict(covered=8, eligible=10, execution_sha=B),
        governance=dict(classified=2, total=3),
    )
    row[K_PASS] = 3
    return row


def _ledger():
    return dict(
        schema="code-purple.matched-growth-ledger.v1",
        authority_transfer=False,
        merge_authorized=False,
        admission="HOLD",
        cohorts=[_cohort("N"), _cohort("N+1")],
        separate_local_extensions=dict(new_regression_checks=13),
        matched_native_changes=dict(
            workflows_denominator=0,
            workflows_passed=0,
            coverage_eligible=0,
            coverage_covered=0,
            coverage_pp=0,
        ),
    )


def _pulse():
    workflows = {K_WF_PASS: 3}
    return dict(
        authority_transfer=False,
        merge_authorized=False,
        metrics=dict(
            head_sha=A,
            merge_checkout_sha=B,
            workflow_total=5,
            workflows=workflows,
            coverage_numerator=8,
            coverage_denominator=10,
        ),
    )


def test_validate_matched_cohort_passes():
    result = mod.validate(_ledger(), _pulse())
    assert result == {
        "status": "PASS_CONSISTENCY_ONLY",
        "source_sha": A,
        "native_numerator_delta": 0,
        "native_denominator_delta": 0,
        "authority_transfer": False,
    }


def _both(ledger, key, value):
    for row in ledger["cohorts"]:
        row[key] = value


def _ledger_case(name):
    ledger = _ledger()
    a, b = ledger["cohorts"]
    if name == "schema":
        ledger["schema"] = "other"
    elif name == "authority":
        ledger["authority_transfer"] = True
    elif name == "merge":
        ledger["merge_authorized"] = None
    elif name == "admission":
        ledger["admission"] = "GO"
    elif name == "pulse_label":
        a["pulse"] = "N+1"
    elif name == "pulse_label_b":
        b["pulse"] = "N"
    elif name == "key_mismatch":
        b["run_fail"] = 9
    elif name == "lines_mismatch":
        b["changed_lines"] = dict(covered=7, eligible=10, execution_sha=B)
    elif name == "gov_mismatch":
        b["governance"] = dict(classified=1, total=3)
    elif name == "denominator":
        _both(ledger, "run_total", 6)
    elif name == "covered_type":
        _both(ledger, "changed_lines", dict(covered=8.0, eligible=10))
    elif name == "eligible_type":
        _both(ledger, "changed_lines", dict(covered=8, eligible="10"))
    elif name == "negative":
        _both(ledger, "changed_lines", dict(covered=-1, eligible=10))
    elif name == "over":
        _both(ledger, "changed_lines", dict(covered=11, eligible=10))
    elif name == "zero_eligible":
        _both(ledger, "changed_lines", dict(covered=0, eligible=0))
    elif name == "gov_over":
        _both(ledger, "governance", dict(classified=4, total=3))
    elif name == "gov_negative":
        _both(ledger, "governance", dict(classified=-1, total=3))
    elif name == "regression":
        ledger["separate_local_extensions"]["new_regression_checks"] = 12
    elif name == "native_growth":
        ledger["matched_native_changes"]["coverage_pp"] = 1
    return ledger


@pytest.mark.parametrize(
    "case, message",
    [
        ("schema", "schema mismatch"),
        ("authority", "authority promotion forbidden"),
        ("merge", "authority promotion forbidden"),
        ("admission", "authority promotion forbidden"),
        ("pulse_label", "not a matched frozen cohort"),
        ("pulse_label_b", "not a matched frozen cohort"),
        ("key_mismatch", "not a matched frozen cohort"),
        ("lines_mismatch", "not a matched frozen cohort"),
        ("gov_mismatch", "not a matched frozen cohort"),
        ("denominator", "run denominator mismatch"),
        ("covered_type", "coverage denominator mismatch"),
        ("eligible_type", "coverage denominator mismatch"),
        ("negative", "coverage denominator mismatch"),
        ("over", "coverage denominator mismatch"),
        ("zero_eligible", "coverage denominator mismatch"),
        ("gov_over", "governance denominator mismatch"),
        ("gov_negative", "governance denominator mismatch"),
        ("regression", "unexpected new regression denominator"),
        ("native_growth", "false matched-native growth claim"),
    ],
)
def test_validate_ledger_rejections(case, message):
    with pytest.raises(ValueError, match=message):
        mod.validate(_ledger_case(case), _pulse())


@pytest.mark.parametrize(
    "field, value, message",
    [
        ("authority_transfer", True, "source authority invalid"),
        ("merge_authorized", "no", "source authority invalid"),
    ],
)
def test_validate_pulse_authority_rejections(field, value, message):
    pulse = _pulse()
    pulse[field] = value
    with pytest.raises(ValueError, match=message):
        mod.validate(_ledger(), pulse)


@pytest.mark.parametrize(
    "field, value, message",
    [
        ("head_sha", B, "checkout/source sha mismatch"),
        ("merge_checkout_sha", A, "checkout/source sha mismatch"),
        ("workflow_total", 4, "workflow tally mismatch"),
        ("workflows", {"PA" + "SS": 2}, "pass tally mismatch"),
        ("coverage_numerator", 7, "source B9 count mismatch"),
        ("coverage_denominator", 11, "source B9 count mismatch"),
    ],
)
def test_validate_pulse_metric_rejections(field, value, message):
    pulse = _pulse()
    pulse["metrics"][field] = value
    with pytest.raises(ValueError, match=message):
        mod.validate(_ledger(), pulse)


def test_validate_does_not_mutate_inputs():
    ledger, pulse = _ledger(), _pulse()
    before = copy.deepcopy((ledger, pulse))
    mod.validate(ledger, pulse)
    assert (ledger, pulse) == before


def _write_inputs(root):
    folder = root / "docs" / "code-purple-w1"
    folder.mkdir(parents=True)
    (folder / "growth-ledger.json").write_text(json.dumps(_ledger()))
    (folder / "pulse_telemetry.json").write_text(json.dumps(_pulse()))
    return folder


def test_main_reads_default_paths_and_prints(tmp_path, monkeypatch, capsys):
    _write_inputs(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["code_purple_w1_growth.py"])
    mod.main()
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "PASS_CONSISTENCY_ONLY"
    assert out["source_sha"] == A


def test_main_explicit_paths_propagate_errors(tmp_path, monkeypatch):
    folder = _write_inputs(tmp_path)
    bad = _ledger()
    bad["schema"] = "x"
    growth = tmp_path / "g.json"
    growth.write_text(json.dumps(bad))
    argv = [
        "code_purple_w1_growth.py",
        "--growth",
        str(growth),
        "--pulse",
        str(folder / "pulse_telemetry.json"),
    ]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(ValueError, match="schema mismatch"):
        mod.main()


def test_script_runs_as_main(tmp_path, monkeypatch, capsys):
    _write_inputs(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT)])
    runpy.run_path(str(SCRIPT), run_name="__main__")
    assert '"PASS_CONSISTENCY_ONLY"' in capsys.readouterr().out
