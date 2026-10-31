"""Gap tests for triage/issue_ageing_metrics.py.

Uses the committed source-bound census snapshots as the valid baseline and
applies synthetic negative-control mutations to reach each fail-closed guard
that tests/test_issue_ageing_metrics.py does not exercise, plus the CLI.
"""

import copy
import json

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

mod = load("triage/issue_ageing_metrics.py", name="abn_w7_issue_ageing_metrics")

ISSUES = json.loads(
    (REPO_ROOT / "triage" / "ABACUS_ISSUE_AGEING_CENSUS_20261017.json").read_text(
        encoding="utf-8"
    )
)
HEADS = json.loads(
    (REPO_ROOT / "triage" / "ABACUS_PR_HEAD_REGISTER_20261017.json").read_text(
        encoding="utf-8"
    )
)


def _rename_issue(issues, old, new):
    row = next(r for r in issues["issue_records"] if r["issue"] == old)
    row["issue"] = new
    row["url"] = "https://github.com/GBOGEB/ABACUS/issues/" + str(new)


def _issue_mutations():
    def schema(i):
        i["schema"] = "other"

    def empty(i):
        i["issue_records"] = []

    def bad_id(i):
        i["issue_records"][0]["issue"] = "1"

    def band(i):
        i["issue_records"][0]["age_band"] = "ancient"

    def dup_row(i):
        i["issue_records"].append(copy.deepcopy(i["issue_records"][0]))

    def denominator(i):
        i["live"]["ordinary_open_issues"] += 1

    def pr_total(i):
        i["live"]["open_pr_total"] += 1

    def dashboard(i):
        i["live"]["open_dashboard_tickets"] += 1

    def root_absent(i):
        _rename_issue(i, 1885, 987654)

    def closed_count(i):
        i["live"]["recent_closed_duplicate_issues"] += 1

    def closed_still_open(i):
        i["closed_housekeeping"][0]["issue"] = i["issue_records"][0]["issue"]

    return [
        (schema, "unknown evidence schema"),
        (empty, "open issue evidence missing"),
        (bad_id, "invalid issue"),
        (band, "unknown ageing cohort"),
        (dup_row, "duplicate issue record"),
        (denominator, "issue denominator mismatch"),
        (pr_total, "PR population mismatch"),
        (dashboard, "dashboard issue count mismatch"),
        (root_absent, "canonical dashboard root issue not open"),
        (closed_count, "closed cohort mismatch"),
        (closed_still_open, "duplicate closed ID or still open"),
    ]


@pytest.mark.parametrize("mutate,message", _issue_mutations())
def test_issue_census_guards(mutate, message):
    issues = copy.deepcopy(ISSUES)
    mutate(issues)
    with pytest.raises(mod.CensusError, match=message):
        mod.summarize(issues, HEADS)


def _head_mutations():
    def dup_pr(h):
        h["primary_source_heads"].append(copy.deepcopy(h["primary_source_heads"][0]))

    def owner_absent(h):
        h["primary_source_heads"] = [
            p for p in h["primary_source_heads"] if p["pr"] != 2026
        ]

    def bseries_pr(h):
        h["bseries_source_matched"]["pr"] = 1

    def bad_pair(h):
        h["bseries_source_matched"]["statement_before"] = [1]

    def bad_ratio(h):
        h["bseries_source_matched"]["branches_before"] = [9, 3]

    def other_head(h):
        h["bseries_source_matched"]["new_head"] = "0" * 40

    return [
        (dup_pr, "duplicate PR"),
        (owner_absent, "required owner PR absent"),
        (bseries_pr, "B-series source/PR not bound"),
        (bad_pair, "invalid matched numerator/denominator"),
        (bad_ratio, "invalid matched coverage ratio"),
        (other_head, "different head recorded within snapshot"),
    ]


@pytest.mark.parametrize("mutate,message", _head_mutations())
def test_pr_register_guards(mutate, message):
    heads = copy.deepcopy(HEADS)
    mutate(heads)
    with pytest.raises(mod.CensusError, match=message):
        mod.summarize(ISSUES, heads)


def test_count_rejects_negative_and_bool():
    with pytest.raises(mod.CensusError, match="invalid thing"):
        mod._count(-1, "thing")
    with pytest.raises(mod.CensusError):
        mod._count(True, "flag")
    assert mod._count(0, "zero") == 0


def test_main_writes_metrics_and_prints_summary(tmp_path, capsys):
    issues = tmp_path / "issues.json"
    heads = tmp_path / "heads.json"
    issues.write_text(json.dumps(ISSUES), encoding="utf-8")
    heads.write_text(json.dumps(HEADS), encoding="utf-8")
    out = tmp_path / "nested" / "metrics.json"
    rc = mod.main(["--issues", str(issues), "--heads", str(heads), "--out", str(out)])
    assert rc == 0
    printed = json.loads(capsys.readouterr().out)
    written = json.loads(out.read_text(encoding="utf-8"))
    assert printed == dict(
        open_issues=written["open_issues"], open_prs=written["open_prs"], P0="HOLD"
    )
    assert written["schema"] == "abacus.triage.ageing-metrics.v1"
    assert written["open_issues"] == len(ISSUES["issue_records"])
