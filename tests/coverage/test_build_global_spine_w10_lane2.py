"""Lane 2 coverage: W10 Global SPINE renderer evidence integrity.

``build_global_spine_w10.py`` renders HTML/Markdown/metrics from a frozen
history and appends W11/W12 panels only after verifying pinned evidence files
(``W11_OBSERVED_MAIN_EPOCH.json``, ``SPINE_*_W11.json``, ``SPINE_STATS_W12.json``)
next to the module (``BASE``).

Hermetic: every test copies the committed inputs into ``tmp_path`` and
monkeypatches the module-level ``BASE`` to that copy, so tampering and
rendering never touch the committed W10/W11 artifacts.  Outputs always go to
``tmp_path``.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
W10_DIR = REPO_ROOT / "MIP" / "G3CS_CONVERGENCE_V2" / "observatory" / "w10"
MODULE_PATH = W10_DIR / "build_global_spine_w10.py"
MODULE_NAME = "_lane2_build_global_spine_w10"

INPUTS = (
    "W10_FROZEN_HISTORY.json",
    "W11_OBSERVED_MAIN_EPOCH.json",
    "CODE_PURPLE_W10_REPO_SPINE.mmd",
    "CODE_PURPLE_W10_REPO_SPINE.svg",
    "spine_contract.py",
    "dependency_metrics.py",
    "SPINE_DAG_W11.json",
    "SPINE_SIPOC_W11.json",
    "SPINE_CONTRACT_W11.json",
    "SPINE_STATS_W12.json",
)
OUTPUTS = (
    "CODE_PURPLE_GLOBAL_SPINE_W10.html",
    "index.html",
    "CODE_PURPLE_GLOBAL_SPINE_W10_HANDOVER.md",
    "CODE_PURPLE_GLOBAL_SPINE_W10_METRICS.json",
)


def _load_path(name, path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


render = _load_path(MODULE_NAME, MODULE_PATH)


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path, obj):
    Path(path).write_text(json.dumps(obj), encoding="utf-8")


@pytest.fixture
def base(tmp_path, monkeypatch):
    folder = tmp_path / "w10"
    folder.mkdir()
    for name in INPUTS:
        shutil.copy2(W10_DIR / name, folder / name)
    monkeypatch.setattr(render, "BASE", folder)
    return folder


@pytest.fixture
def history():
    return _read_json(W10_DIR / "W10_FROZEN_HISTORY.json")


def _repin(folder: Path, hist: dict) -> None:
    """Re-pin W11/W12 evidence in the tmp copy for a modified history."""
    contract = _load_path(
        f"_lane2_spine_contract_{id(folder)}", folder / "spine_contract.py"
    )
    outcome = contract.build(hist)
    _write_json(folder / "SPINE_DAG_W11.json", outcome["dag"])
    _write_json(folder / "SPINE_SIPOC_W11.json", outcome["sipoc"])
    _write_json(
        folder / "SPINE_CONTRACT_W11.json",
        {k: v for k, v in outcome.items() if k not in ("dag", "sipoc")},
    )
    metrics = _load_path(
        f"_lane2_dependency_metrics_{id(folder)}", folder / "dependency_metrics.py"
    )
    epoch = _read_json(folder / "W11_OBSERVED_MAIN_EPOCH.json")
    _write_json(folder / "SPINE_STATS_W12.json", metrics.build(hist, epoch))


def _run_main(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["build_global_spine_w10.py", *map(str, args)])
    render.main()


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------


@pytest.mark.parametrize("bad", [-1, 1.0, "3", None, True])
def test_ensure_uint_rejects(bad):
    with pytest.raises(ValueError, match="nonnegative integer"):
        render.ensure_uint(bad)


def test_ensure_uint_accepts_zero_and_positive():
    assert render.ensure_uint(0) == 0
    assert render.ensure_uint(17046) == 17046


def test_formatting_helpers():
    assert render.esc('<a href="x">&\'') == "&lt;a href=&quot;x&quot;&gt;&amp;&#x27;"
    assert render.pct(1, 4) == 25.0
    assert render.pct(1, 0) is None
    assert render.N(None) == "UNKNOWN"
    assert render.N(0) == "0"
    assert render.N(1234567) == "1,234,567"
    assert render.pill("<b>", "fail") == '<span class="pill fail">&lt;b&gt;</span>'
    assert render.pill("x") == '<span class="pill neutral">x</span>'
    assert render.badge_metric(1, 3) == "33.33%"
    assert render.badge_metric(1, 4, " pp") == "25.00 pp"
    assert render.badge_metric(5, 0) == "UNKNOWN"


def test_closed_open_rail_widths_and_escaping():
    assert render.closed_open_rail(0, 0) == '<div class="rail muted"></div>'
    rail = render.closed_open_rail(3, 1)
    assert 'aria-label="3 closed and 1 open"' in rail
    assert "width:75.000000%" in rail and "width:25.000000%" in rail
    hostile = render.closed_open_rail(1, 1, '"><script>x</script>')
    assert "<script>" not in hostile
    assert "&quot;&gt;&lt;script&gt;" in hostile


def test_chart_svg_custom_values_and_determinism():
    default = render.chart_svg()
    assert default == render.chart_svg((17036, 17046))
    custom = render.chart_svg((17030, 17050))
    assert "17,030" in custom and "17,050" in custom
    assert custom != default
    assert custom.startswith('<svg id="debtChart"') and custom.endswith("</svg>")


def test_coverage_svg_uses_history_values(history):
    svg = render.coverage_svg(history)
    old, green = history["clocks"]["main_coverage"][:2]
    gain = history["next_scenario"]["net_unique_existing_coverage_opportunities"]
    assert f"{100 * old['covered'] / old['eligible']:.3f}%" in svg
    assert f"{100 * green['covered'] / green['eligible']:.3f}%" in svg
    assert f"{100 * (green['covered'] + gain) / green['eligible']:.3f}%*" in svg
    assert f"{green['eligible']:,}" in svg
    assert "UNKNOWN" in svg  # latest main coverage never fabricated
    h2 = copy.deepcopy(history)
    h2["next_scenario"]["net_unique_existing_coverage_opportunities"] = 0
    assert f"{100 * green['covered'] / green['eligible']:.3f}%*" in render.coverage_svg(
        h2
    )


def test_repo_table_escapes_registry(history):
    registry = copy.deepcopy(history["source_registry"])
    table = render.repo_table(registry)
    assert table.count("<tr>") == len(registry)
    hostile = [
        {
            "repo": "GBOGEB/<img src=x>",
            "layer": "<b>layer</b>",
            "url": 'javascript:"x"',
            "path": "<p>",
            "purpose": "&",
            "sha": "<script>alert(1)</script>",
        }
    ]
    out = render.repo_table(hostile)
    assert "<img" not in out and "<script>" not in out and "<p>" not in out
    assert "&lt;img src=x&gt;" in out
    assert "&lt;script&gt;" in out  # first 12 chars of sha, escaped
    assert 'href="javascript:&quot;x&quot;"' in out


# --------------------------------------------------------------------------
# checked_history: tampered / forged history must fail closed
# --------------------------------------------------------------------------


def test_checked_history_accepts_frozen(history):
    assert render.checked_history(history) is history


def _mut(history, fn):
    h = copy.deepcopy(history)
    fn(h)
    return h


@pytest.mark.parametrize(
    "mutate, phrase",
    [
        (
            lambda h: h.update(schema="codepurple.spine.w09.history.v1"),
            "invalid history schema",
        ),
        (lambda h: h.pop("schema"), "invalid history schema"),
        (
            lambda h: h["clocks"]["issues"][-1]["repos"][0].update(issue_open=-1),
            "nonnegative",
        ),
        (
            lambda h: h["clocks"]["issues"][-1]["repos"][1].update(issue_closed=None),
            "nonnegative",
        ),
        (
            lambda h: h["clocks"]["issues"][-1].update(total_closed=372),
            "do not reconcile",
        ),
        (
            lambda h: h["clocks"]["issues"][-1].update(total_issues=477),
            "issue total invalid",
        ),
        (lambda h: h["clocks"]["main_ci"][0].update(other=1), "numerator/denominator"),
        (
            lambda h: h["clocks"]["main_ci"][1].update(failure=-7, success=33),
            "nonnegative",
        ),
        (lambda h: h["clocks"]["pr_ci"][1].update(total=21), "numerator/denominator"),
        (
            lambda h: h["clocks"]["main_coverage"][1].update(
                eligible=0, covered=0, uncovered=0
            ),
            "coverage count error",
        ),
        (
            lambda h: h["clocks"]["main_coverage"][0].update(covered=60000),
            "coverage count error",
        ),
        (lambda h: h["clocks"]["main_coverage"][0].update(covered=-1), "nonnegative"),
        (
            lambda h: h["clocks"]["main_coverage"][1].update(uncovered=17045),
            "uncovered mismatch",
        ),
        (
            lambda h: h["clocks"]["main_coverage"][1].update(uncovered=None),
            "nonnegative",
        ),
    ],
)
def test_checked_history_rejects_forgery(history, mutate, phrase):
    with pytest.raises(ValueError, match=phrase):
        render.checked_history(_mut(history, mutate))


def test_checked_history_null_coverage_is_skipped_not_zeroed(history):
    h = _mut(
        history, lambda x: x["clocks"]["main_coverage"][2].update(eligible="anything")
    )
    # covered is None -> no numeric claim checked, and it stays None.
    assert render.checked_history(h)["clocks"]["main_coverage"][2]["covered"] is None


def test_checked_history_missing_workflow_keys_default_zero(history):
    h = _mut(history, lambda x: x["clocks"]["pr_ci"].append({"success": 0, "total": 0}))
    assert render.checked_history(h) is h


# --------------------------------------------------------------------------
# make_html
# --------------------------------------------------------------------------


def test_make_html_single_footer_and_data_mirror(base, history):
    html = render.make_html(history, "<svg id='net'></svg>")
    assert html.startswith("<!doctype html>")
    assert html.count("<footer>") == 1
    assert "<svg id='net'></svg>" in html
    assert 'id="tileIssueOpen">105<' in html
    assert ">478<" in html
    # Mermaid source is read from BASE (tmp copy) and escaped.
    (base / "CODE_PURPLE_W10_REPO_SPINE.mmd").write_text(
        "graph LR; A-->B<script>", encoding="utf-8"
    )
    html2 = render.make_html(history, "")
    assert "A--&gt;B&lt;script&gt;" in html2


def test_make_html_mirror_neutralises_script_breakout(base, history):
    h = copy.deepcopy(history)
    h["scope"] = "</script><script>alert(1)</script>"
    html = render.make_html(h, "")
    assert "</script><script>alert(1)" not in html
    assert "<\\/script><script>alert(1)<\\/script>" in html


def test_make_html_missing_mermaid_source(base, history):
    (base / "CODE_PURPLE_W10_REPO_SPINE.mmd").unlink()
    with pytest.raises(FileNotFoundError):
        render.make_html(history, "")


def test_make_html_escapes_dod_predicates(base, history):
    h = copy.deepcopy(history)
    h["local_dod"][0]["predicate"] = "<img src=x onerror=1>"
    h["mission_goals"][0]["goal"] = "<iframe>"
    html = render.make_html(h, "")
    # The raw strings legitimately survive inside the inert application/json
    # mirror; the rendered table cells must carry only the escaped form.
    visible = html.replace(
        html[html.index('id="w10data"') :].split("</script>", 1)[0], ""
    )
    assert "<img src=x onerror=1>" not in visible
    assert "<b>&lt;img src=x onerror=1&gt;</b>" in visible
    assert "<iframe>" not in visible
    assert "<b>&lt;iframe&gt;</b>" in visible


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="BUG: make_html interpolates local_dod/mission_goals 'id' without esc(); "
    "a history id is injected verbatim into the HTML",
)
def test_make_html_escapes_dod_identifier(base, history):
    h = copy.deepcopy(history)
    h["local_dod"][0]["id"] = "<img src=x onerror=alert(1)>"
    html = render.make_html(h, "")
    assert "<code><img src=x onerror=alert(1)></code>" not in html


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="BUG: make_html derives the pill CSS class from 'state' without esc(); "
    "a quote in a history state breaks out of the class attribute",
)
def test_make_html_escapes_state_class_attribute(base, history):
    h = copy.deepcopy(history)
    h["mission_goals"][0]["state"] = 'X" onmouseover="alert(1)'
    html = render.make_html(h, "")
    assert 'onmouseover="alert(1)"' not in html


# --------------------------------------------------------------------------
# W11 native main epoch panel
# --------------------------------------------------------------------------


def test_w11_native_main_panel_renders(base, history):
    panel = render.w11_native_main_panel(history)
    assert 'id="w11-main-epoch"' in panel
    assert "Governed admission HOLD" in panel
    assert "16,926" in panel


def test_w11_native_main_panel_missing_epoch(base, history):
    (base / "W11_OBSERVED_MAIN_EPOCH.json").unlink()
    with pytest.raises(ValueError, match="missing"):
        render.w11_native_main_panel(history)


def _bad_epoch(base, history, mutate, phrase):
    path = base / "W11_OBSERVED_MAIN_EPOCH.json"
    epoch = _read_json(path)
    mutate(epoch)
    _write_json(path, epoch)
    with pytest.raises(ValueError, match=phrase):
        render.w11_native_main_panel(history)


@pytest.mark.parametrize(
    "mutate, phrase",
    [
        (
            lambda e: e.update(schema="codepurple.spine.w11.observed-main.v0"),
            "schema invalid",
        ),
        (lambda e: e["measurements"][0].update(source_sha="0" * 40), "does not join"),
        (
            lambda e: e["measurements"][0]["combined"].update(covered=35155),
            "does not join",
        ),
        (
            lambda e: e["measurements"][0]["combined"].update(eligible=52201),
            "does not join",
        ),
        (lambda e: e["governance"].update(security_waiver=True), "governance"),
        (lambda e: e["governance"].update(extra=True), "governance"),
        (
            lambda e: e["measurements"][1]["statements"].update(covered=-1),
            "numerator/denominator",
        ),
        (
            lambda e: e["measurements"][1]["branches"].update(covered=99999),
            "numerator/denominator",
        ),
        (
            lambda e: e["measurements"][1]["statements"].update(eligible="40365"),
            "numerator/denominator",
        ),
        (
            lambda e: e["measurements"][1].update(native_b0_terminal="failure"),
            "inconsistent",
        ),
        (
            lambda e: e["measurements"][1]["combined"].update(uncovered=0),
            "inconsistent",
        ),
        (lambda e: e["measurements"][1].update(source_sha="abc"), "digest invalid"),
        (
            lambda e: e["measurements"][0].update(archive_sha256="0" * 63),
            "digest invalid",
        ),
        (lambda e: e["comparison"].update(eligible_delta=0), "conservation"),
        (lambda e: e["comparison"].update(uncovered_delta=0), "conservation"),
        (lambda e: e["comparison"].update(new_test_ids=-1), "test identity"),
        (lambda e: e["comparison"].update(removed_test_ids=-5), "test identity"),
        (lambda e: e["next_conditional"].update(assumed_eligible=52496), "conditional"),
        (
            lambda e: e["next_conditional"].update(net_new_covered=16927),
            "exceeds uncovered",
        ),
        (
            lambda e: e["measurements"][1]["combined"].update(percent=67.76),
            "percentage invalid",
        ),
    ],
)
def test_w11_native_main_panel_tamper(base, history, mutate, phrase):
    _bad_epoch(base, history, mutate, phrase)


def test_w11_native_main_panel_stale_history_sha_detected(base, history):
    h = copy.deepcopy(history)
    h["clocks"]["main_coverage"][1]["sha"] = "1" * 40
    with pytest.raises(ValueError, match="does not join"):
        render.w11_native_main_panel(h)


def test_w11_native_main_panel_boundary_full_closure_allowed(base, history):
    path = base / "W11_OBSERVED_MAIN_EPOCH.json"
    epoch = _read_json(path)
    epoch["next_conditional"]["net_new_covered"] = epoch["measurements"][1]["combined"][
        "uncovered"
    ]
    _write_json(path, epoch)
    assert 'id="w11-main-epoch"' in render.w11_native_main_panel(history)


# --------------------------------------------------------------------------
# W11 contract / W12 statistics panels (pinned evidence drift)
# --------------------------------------------------------------------------


def test_w11_contract_panel_renders(base, history):
    assert 'id="w11-contract"' in render.w11_contract_panel(history)


@pytest.mark.parametrize(
    "name", ["SPINE_DAG_W11.json", "SPINE_SIPOC_W11.json", "SPINE_CONTRACT_W11.json"]
)
def test_w11_contract_panel_drift_or_missing(base, history, name):
    path = base / name
    data = _read_json(path)
    if isinstance(data, dict):
        data["_forged"] = True
    else:
        data.append("forged")
    _write_json(path, data)
    with pytest.raises(ValueError, match="contract drift: " + name):
        render.w11_contract_panel(history)
    path.unlink()
    with pytest.raises(ValueError, match="contract drift: " + name):
        render.w11_contract_panel(history)


def test_w11_contract_panel_missing_validator_source(base, history):
    (base / "spine_contract.py").unlink()
    with pytest.raises(FileNotFoundError):
        render.w11_contract_panel(history)


def test_w12_panel_renders(base, history):
    panel = render.w12_dependency_statistics_panel(history)
    assert 'id="w12-stats"' in panel
    assert "NOT QUALIFIED" in panel
    assert "DESCRIPTIVE ONLY" in panel


def test_w12_panel_drift_and_missing_pin(base, history):
    pinned = base / "SPINE_STATS_W12.json"
    stats = _read_json(pinned)
    stats["graph"]["directed_density"] = 1.0
    _write_json(pinned, stats)
    with pytest.raises(ValueError, match="drift"):
        render.w12_dependency_statistics_panel(history)
    pinned.unlink()
    with pytest.raises(ValueError, match="drift"):
        render.w12_dependency_statistics_panel(history)


def _stub_provider(base, inference):
    (base / "dependency_metrics.py").write_text(
        "import json\n"
        f"_INF = json.loads({json.dumps(json.dumps(inference))})\n"
        "def build(history, epoch):\n"
        "    return {'graph': {'top_structural_betweenness': []},\n"
        "            'temporal': {'deltas': []}, 'inference': _INF}\n",
        encoding="utf-8",
    )
    _write_json(
        base / "SPINE_STATS_W12.json",
        {
            "graph": {"top_structural_betweenness": []},
            "temporal": {"deltas": []},
            "inference": inference,
        },
    )


@pytest.mark.parametrize(
    "inference",
    [
        {"inference_ready": True, "p_values": None},
        {"inference_ready": False, "p_values": {"ANOVA": 0.01}},
    ],
)
def test_w12_panel_rejects_promoted_inference(base, history, inference):
    _stub_provider(base, inference)
    with pytest.raises(ValueError, match="Unqualified inferential"):
        render.w12_dependency_statistics_panel(history)


# --------------------------------------------------------------------------
# main(): end-to-end render into tmp, determinism, adversarial history
# --------------------------------------------------------------------------


def _outputs(folder):
    return {name: (folder / name).read_bytes() for name in OUTPUTS}


def test_main_defaults_render_into_base_copy(base, monkeypatch, capsys):
    _run_main(monkeypatch)
    out = _outputs(base)
    printed = capsys.readouterr().out
    for name in OUTPUTS:
        assert name in printed
    html = out["CODE_PURPLE_GLOBAL_SPINE_W10.html"]
    assert out["index.html"] == html
    metrics = json.loads(out["CODE_PURPLE_GLOBAL_SPINE_W10_METRICS.json"])
    assert metrics["html_sha256"] == hashlib.sha256(html).hexdigest()
    assert (
        metrics["source_history_sha256"]
        == hashlib.sha256((base / "W10_FROZEN_HISTORY.json").read_bytes()).hexdigest()
    )
    assert metrics["history_source"] == "W10_FROZEN_HISTORY.json"
    assert metrics["current_main_coverage"] is None
    assert metrics["native_main_admission"] == "HOLD"
    text = html.decode("utf-8")
    assert text.count("<footer>") == 1
    # panels injected before the footer, in order
    i_contract = text.index('id="w11-contract"')
    i_epoch = text.index('id="w11-main-epoch"')
    i_stats = text.index('id="w12-stats"')
    assert i_contract < i_epoch < i_stats < text.index("<footer>")
    md = (
        out["CODE_PURPLE_GLOBAL_SPINE_W10_HANDOVER.md"]
        .decode("utf-8")
        .replace("\r\n", "\n")
    )
    assert md.startswith("# CODE PURPLE")
    assert "1122dca15557e4d2b0ec16300fcbf409db678e86" in md
    assert "MERGE_ADMISSION=HOLD" in md
    # committed inputs untouched
    assert (W10_DIR / "W10_FROZEN_HISTORY.json").read_bytes() == (
        base / "W10_FROZEN_HISTORY.json"
    ).read_bytes()


def test_main_render_is_deterministic_and_svg_prolog_stripped(
    base, monkeypatch, tmp_path
):
    svg = base / "CODE_PURPLE_W10_REPO_SPINE.svg"
    svg.write_text(
        '<?xml version="1.0"?>\n<!DOCTYPE svg>\n<svg id="netw"><a href="x">n</a></svg>\n',
        encoding="utf-8",
    )
    hist = base / "W10_FROZEN_HISTORY.json"
    _run_main(monkeypatch, "--history", hist, "--outdir", tmp_path / "a")
    _run_main(monkeypatch, "--history", hist, "--outdir", tmp_path / "b" / "nested")
    first, second = _outputs(tmp_path / "a"), _outputs(tmp_path / "b" / "nested")
    assert first == second
    text = first["index.html"].decode("utf-8")
    assert '<svg id="netw"><a href="x">n</a></svg>' in text
    assert "<?xml" not in text and "<!DOCTYPE svg>" not in text
    # Re-render in place over existing outputs is idempotent.
    _run_main(monkeypatch, "--history", hist, "--outdir", tmp_path / "a")
    assert _outputs(tmp_path / "a") == first


def test_main_history_bytes_change_changes_source_hash_only(
    base, monkeypatch, tmp_path
):
    hist = base / "W10_FROZEN_HISTORY.json"
    _run_main(monkeypatch, "--history", hist, "--outdir", tmp_path / "a")
    reformatted = tmp_path / "reformatted.json"
    reformatted.write_text(json.dumps(_read_json(hist), indent=4), encoding="utf-8")
    _run_main(monkeypatch, "--history", reformatted, "--outdir", tmp_path / "b")
    a = json.loads((tmp_path / "a" / OUTPUTS[3]).read_text(encoding="utf-8"))
    b = json.loads((tmp_path / "b" / OUTPUTS[3]).read_text(encoding="utf-8"))
    assert a["source_history_sha256"] != b["source_history_sha256"]
    assert b["history_source"] == "reformatted.json"
    assert a["html_sha256"] == b["html_sha256"]


def test_main_missing_history_writes_nothing(base, monkeypatch, tmp_path):
    with pytest.raises(FileNotFoundError):
        _run_main(
            monkeypatch,
            "--history",
            tmp_path / "absent.json",
            "--outdir",
            tmp_path / "out",
        )
    assert not (tmp_path / "out").exists()


def test_main_malformed_history_json(base, monkeypatch, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        _run_main(monkeypatch, "--history", bad, "--outdir", tmp_path / "out")


def test_main_forged_history_rejected_before_output(
    base, monkeypatch, tmp_path, history
):
    forged = tmp_path / "forged.json"
    history["clocks"]["main_ci"][1]["success"] = 26
    _write_json(forged, history)
    with pytest.raises(ValueError, match="workflow"):
        _run_main(monkeypatch, "--history", forged, "--outdir", tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_main_missing_spine_svg(base, monkeypatch, tmp_path):
    (base / "CODE_PURPLE_W10_REPO_SPINE.svg").unlink()
    with pytest.raises(FileNotFoundError):
        _run_main(monkeypatch, "--outdir", tmp_path / "out")
    assert not (tmp_path / "out" / OUTPUTS[0]).exists()


def test_main_ambiguous_footer_anchor_rejected(base, monkeypatch, tmp_path, history):
    # A second <footer> smuggled in via the inline SVG would let panels be
    # injected at an attacker-chosen location; the renderer must refuse.
    (base / "CODE_PURPLE_W10_REPO_SPINE.svg").write_text(
        "<svg><footer></footer></svg>", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="footer anchor"):
        _run_main(monkeypatch, "--outdir", tmp_path / "out")
    assert not (tmp_path / "out" / OUTPUTS[0]).exists()


def test_main_footer_in_history_data_rejected(base, monkeypatch, tmp_path, history):
    h = copy.deepcopy(history)
    h["scope"] = "<footer>"
    path = tmp_path / "h.json"
    _write_json(path, h)
    with pytest.raises(ValueError, match="footer anchor"):
        _run_main(monkeypatch, "--history", path, "--outdir", tmp_path / "out")


def test_main_tampered_pin_aborts_without_html(base, monkeypatch, tmp_path):
    stats = _read_json(base / "SPINE_STATS_W12.json")
    stats["schema"] = "forged"
    _write_json(base / "SPINE_STATS_W12.json", stats)
    with pytest.raises(ValueError, match="W12 typed statistics drift"):
        _run_main(monkeypatch, "--outdir", tmp_path / "out")
    assert not (tmp_path / "out" / OUTPUTS[0]).exists()


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="BUG: main() hardcodes the N+1 scenario (+522 coverage, +2 CI recoveries) in the "
    "metrics JSON and handover instead of reading history['next_scenario']; a re-rendered "
    "history with a different scenario publishes stale numbers",
)
def test_main_metrics_follow_history_scenario(base, monkeypatch, tmp_path, history):
    h = copy.deepcopy(history)
    h["next_scenario"]["net_unique_existing_coverage_opportunities"] = 100
    h["next_scenario"]["ci_failures_recovered"] = 1
    _repin(base, h)
    path = base / "W10_FROZEN_HISTORY.json"
    _write_json(path, h)
    _run_main(monkeypatch, "--outdir", tmp_path / "out")
    metrics = _read_json(tmp_path / "out" / OUTPUTS[3])
    green = h["clocks"]["main_coverage"][1]
    ci = h["clocks"]["main_ci"][1]
    assert metrics["future_green_fixed_denominator_scenario"] == pytest.approx(
        100 * (green["covered"] + 100) / green["eligible"]
    )
    assert metrics["future_ci_conditional_share"] == pytest.approx(
        100 * (ci["success"] + 1) / ci["total"]
    )
