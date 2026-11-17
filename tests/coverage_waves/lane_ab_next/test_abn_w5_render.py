"""Behaviour tests for tools/everred_v3/acceptance/render.py.

The ``acceptance`` directory is loaded as a privately named package so the
relative ``from .core import ...`` resolves without touching sys.path.
"""

import hashlib
import importlib
import importlib.util
import json
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT

ACC_DIR = REPO_ROOT / "tools" / "everred_v3" / "acceptance"
PKG = "abn_w5_acceptance_render_pkg"


def _load_package(name):
    spec = importlib.util.spec_from_file_location(
        name, ACC_DIR / "__init__.py", submodule_search_locations=[str(ACC_DIR)]
    )
    package = importlib.util.module_from_spec(spec)
    sys.modules[name] = package
    spec.loader.exec_module(package)
    return package


_load_package(PKG)
render = importlib.import_module(PKG + ".render")
core = importlib.import_module(PKG + ".core")

URL = "https://github.com/GBOGEB/ABACUS/actions/runs/7"


def _obligation(code, state, url=None, sha=None, epoch=None, deps=(), title=None):
    return dict(
        id=code,
        repo="GBOGEB/ABACUS",
        title=title or "Title " + code,
        kind="test",
        scope="head",
        depends_on=list(deps),
        evidence_state=state,
        evidence_checked=state == "OBSERVED",
        admission_checked=False,
        latest_evidence_url=url,
        latest_subject_sha=sha,
        latest_epoch=epoch,
    )


def _projection():
    return {
        "schema": "codepurple.acceptance.projection.v1",
        "admission": "HOLD",
        "metrics": dict(
            evidence_observed=1, obligations=2, evidence_stale=0, evidence_blocked=1
        ),
        "obligations": [
            _obligation(
                "ACC-001",
                "OBSERVED",
                url=URL,
                sha="a" * 40,
                epoch=0,
                title="Pipe | split\nline <b>",
            ),
            _obligation("ACC-002", "BLOCKED_DEPENDENCY", deps=["ACC-001"]),
        ],
        "ledger": [{"id": "OBS-001"}, {"id": "OBS-002"}],
    }


def _graph():
    frontier = [
        dict(id="F" + str(n), observed_state="MISSING", downstream_dependency_reach=n)
        for n in range(16)
    ]
    return {"nodes": [], "edges": [], "blocked_frontier": frontier}


def _sipoc(admission="HOLD"):
    sources = {"GBOGEB/CODEX": dict(plane="review", consumer="QPS & co")}
    return {"sources": sources, "admission": admission}


def _temporal():
    return {
        "pulses": [
            dict(
                pulse=0,
                observed_evidence=0,
                obligations=2,
                state_changes_from_previous=None,
                descriptive_status_stability=None,
            ),
            dict(
                pulse=1,
                observed_evidence=1,
                obligations=2,
                state_changes_from_previous=1,
                descriptive_status_stability=0.3333,
            ),
        ]
    }


def test_esc_quotes_and_coerces():
    assert render.esc("<a href='x'>&\"") == "&lt;a href=&#x27;x&#x27;&gt;&amp;&quot;"
    assert render.esc(5) == "5"
    assert render.esc(None) == "None"


def test_markdown_debt_table_and_links():
    text = render.markdown_debt(_projection())
    lines = text.splitlines()
    assert lines[0] == "# CODE PURPLE - acceptance debt (read-only projection)"
    row = "| ACC-001 | [x] | [ ] | GBOGEB/ABACUS | Pipe \\| split line <b> | OBSERVED |"
    assert row in lines
    assert "| ACC-002 | [ ] | [ ] | GBOGEB/ABACUS | Title ACC-002 |" in text
    link = "- ACC-001: [read native source](" + URL + ") on head `" + "a" * 40
    assert link in text
    assert "- ACC-002:" not in text
    assert text.endswith("diff coverage are unverified.\n")


def test_render_html_escapes_and_lists_sections():
    html = render.render_html(_projection(), _graph(), _sipoc(), _temporal())
    assert html.startswith("<!doctype html>")
    assert "Pipe | split\nline &lt;b&gt;" in html
    assert "line <b>" not in html
    assert "href='" + URL + "'>Evidence source</a>" in html
    assert "<span class='muted'>No receipt</span>" in html
    assert "Requires: ACC-001" in html
    assert "Requires: none" in html
    assert "Observed head: <code>UNKNOWN</code>" in html
    assert "Epoch: <code>0</code>" in html
    assert "Epoch: <code>UNKNOWN</code>" in html
    assert "<strong>1 / 2</strong>" in html
    assert "<td>F13</td>" in html
    assert "<td>F14</td>" not in html
    assert "<tr><td>0</td><td>0/2</td><td>UNKNOWN</td><td>UNKNOWN</td></tr>" in html
    assert "<tr><td>1</td><td>1/2</td><td>1</td><td>33.3</td></tr>" in html
    assert "<td>GBOGEB/CODEX</td><td>review</td><td>QPS &amp; co</td>" in html
    assert "Local standalone testflight" not in html


def test_render_html_with_testflight_defaults_unknown():
    flight = {"coverage_percent": 97.5}
    html = render.render_html(_projection(), _graph(), _sipoc(), _temporal(), flight)
    assert "Local standalone testflight: UNKNOWN cases, 97.5%" in html


def test_render_html_empty_testflight_is_omitted():
    html = render.render_html(_projection(), _graph(), _sipoc(), _temporal(), {})
    assert "Local standalone testflight" not in html


@pytest.mark.parametrize("which", ["projection", "sipoc"])
def test_render_html_refuses_non_hold(which):
    projection = _projection()
    sipoc = _sipoc()
    if which == "projection":
        projection["admission"] = "ADMITTED"
    else:
        sipoc["admission"] = "ADMITTED"
    with pytest.raises(core.InvalidEvidence, match="unadmitted source"):
        render.render_html(projection, _graph(), sipoc, _temporal())


def test_write_bundle_writes_files_and_hash_manifest(tmp_path):
    out = tmp_path / "a" / "b"
    projection = _projection()
    hashes = render.write_bundle(
        out, projection, _graph(), _sipoc(), _temporal(), {"tests_passed": 3}
    )
    expected = {
        "acceptance.json",
        "acceptance_debt.md",
        "dag.json",
        "dmaic_mip_pulses.json",
        "index.html",
        "ledger_proposals.jsonl",
        "sipoc.json",
    }
    assert set(hashes) == expected
    assert list(hashes) == sorted(hashes)
    for name in expected:
        text = (out / name).read_text(encoding="utf-8")
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert digest == hashes[name], name
    manifest = json.loads((out / "sha256.json").read_text(encoding="utf-8"))
    assert manifest == hashes
    acceptance = json.loads((out / "acceptance.json").read_text(encoding="utf-8"))
    assert "ledger" not in acceptance
    assert acceptance["admission"] == "HOLD"
    ledger_text = (out / "ledger_proposals.jsonl").read_text(encoding="utf-8")
    ledger = [json.loads(line) for line in ledger_text.splitlines()]
    assert ledger == projection["ledger"]
    assert json.loads((out / "dag.json").read_text(encoding="utf-8")) == _graph()
    assert "3 cases" in (out / "index.html").read_text(encoding="utf-8")


def test_write_bundle_refuses_non_hold_before_writing_hashes(tmp_path):
    with pytest.raises(core.InvalidEvidence):
        render.write_bundle(
            tmp_path, _projection(), _graph(), _sipoc("ADMITTED"), _temporal()
        )
    assert not (tmp_path / "sha256.json").exists()
