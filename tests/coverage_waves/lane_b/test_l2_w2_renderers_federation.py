"""Lane-B wave 2: renderers package and runtime/federation DOW consumers."""

import json
import math
import sys
import xml.etree.ElementTree as ET

import pytest

from renderers import MathMLRenderer, ProcessFlowRenderer, SVGRenderer, qplant_equation_definitions

from ._l2_loader import load

SVG_NS = "{http://www.w3.org/2000/svg}"
MML_NS = "{http://www.w3.org/1998/Math/MathML}"


# --- SVGRenderer ------------------------------------------------------------

def test_svg_renderer_rejects_non_positive_scale():
    with pytest.raises(ValueError, match="scale"):
        SVGRenderer(scale=0)


def test_svg_renderer_nodes_edges_and_lineage():
    renderer = SVGRenderer(scale=2, style_hooks={"node_class": "n"})
    svg = renderer.render(
        nodes=[{"id": "a", "label": "Alpha"}, {"id": "b"}],
        edges=[{"from": "a", "to": "b"}, {"from": "a", "to": "ghost"}],
        title="Flow",
        lineage={"wave": "W999", "extra": 1},
    )
    root = ET.fromstring(svg)
    assert root.get("data-scale") == "2.0"
    # 2 nodes: 40*2*2 + 2*(160*2+80*2) - 80*2 = 160 + 960 - 160 = 960
    assert root.get("width") == "960"
    rects = root.findall(SVG_NS + "rect")
    assert [r.get("class") for r in rects] == ["n", "n"]
    labels = [t.text for t in root.findall(SVG_NS + "text")]
    assert labels == ["Flow", "Alpha", "b"]
    lines = root.findall(SVG_NS + "line")
    assert len(lines) == 1 and lines[0].get("data-edge-to") == "b"
    meta = json.loads(root.find(SVG_NS + "metadata").text)
    assert meta == {"wave": "W999", "renderer": "process_flow", "runtime_evidence": True, "extra": 1}
    assert root.find(SVG_NS + "defs/" + SVG_NS + "marker").get("id") == "abacus-arrowhead"


def test_svg_renderer_empty_graph_placeholder():
    root = ET.fromstring(SVGRenderer().render(nodes=[], edges=[]))
    assert root.get("width") == "300" and root.get("height") == "200"
    assert [t.text for t in root.findall(SVG_NS + "text")] == ["No process nodes defined"]
    assert json.loads(root.find(SVG_NS + "metadata").text)["wave"] == "W003"


def test_svg_to_html_wraps():
    html = SVGRenderer().to_html("<svg/>", title="T")
    assert html.startswith("<!DOCTYPE html>") and "<title>T</title>" in html and "<svg/>" in html


# --- ProcessFlowRenderer ----------------------------------------------------

def _schema(**overrides):
    schema = {
        "type": "process_flow",
        "title": "Plant",
        "nodes": [{"id": "a", "label": "A"}, {"id": "b"}],
        "edges": [{"from": "a", "to": "b"}],
    }
    schema.update(overrides)
    return schema


def test_process_flow_validate_normalizes_labels():
    normalized = ProcessFlowRenderer().validate_schema(_schema())
    assert normalized["nodes"] == [{"id": "a", "label": "A"}, {"id": "b", "label": "b"}]
    assert normalized["edges"] == [{"from": "a", "to": "b"}]


@pytest.mark.parametrize(
    "schema,message",
    [
        ([], "schema must be a mapping"),
        ({"type": "process_flow"}, "missing required fields: title, nodes, edges"),
        (_schema(type="other"), "type must be 'process_flow'"),
        (_schema(title="  "), "title must be a non-empty string"),
        (_schema(nodes={}), "nodes must be a list"),
        (_schema(edges=None), "edges must be a list"),
        (_schema(nodes=["x"]), "each node must be a mapping"),
        (_schema(nodes=[{"id": ""}]), "node.id must be a non-empty string"),
        (_schema(nodes=[{"id": "a"}, {"id": "a"}], edges=[]), "duplicate node id: a"),
        (_schema(nodes=[{"id": "a", "label": 3}], edges=[]), "node.label must be a string"),
        (_schema(edges=["x"]), "each edge must be a mapping"),
        (_schema(edges=[{"from": "a", "to": 1}]), "string 'from' and 'to'"),
        (_schema(edges=[{"from": "a", "to": "z"}]), "edge references unknown node"),
    ],
)
def test_process_flow_validate_errors(schema, message):
    with pytest.raises(ValueError, match=message.replace("(", r"\(").replace(")", r"\)")):
        ProcessFlowRenderer().validate_schema(schema)


def test_process_flow_render_and_html():
    renderer = ProcessFlowRenderer()
    svg = renderer.render(_schema(), scale=1.5, lineage={"run": 7})
    meta = json.loads(ET.fromstring(svg).find(SVG_NS + "metadata").text)
    assert meta["run"] == 7 and meta["renderer"] == "process_flow"
    html = renderer.render_html(_schema(), style_hooks={"svg_class": "custom"})
    assert "<title>Plant</title>" in html and 'class="custom"' in html
    assert "<metadata>" in renderer.render(_schema())


# --- MathMLRenderer ---------------------------------------------------------

def test_mathml_renders_all_qplant_definitions():
    renderer = MathMLRenderer(style_hooks={"math_class": "m"})
    defs = qplant_equation_definitions()
    assert set(defs) == {"carnot_efficiency", "cop", "heat_balance"}
    carnot = ET.fromstring(renderer.render(defs["carnot_efficiency"], lineage={"k": "v"}))
    assert carnot.get("class") == "m"
    row = carnot.find(MML_NS + "semantics/" + MML_NS + "mrow")
    assert row.find(MML_NS + "mtext").text == "Carnot Efficiency"
    texts = [e.text for e in carnot.iter() if e.text]
    assert "η" in texts
    assert carnot.find(".//" + MML_NS + "mfrac") is not None
    assert len(carnot.findall(".//" + MML_NS + "msub")) == 2
    meta = json.loads(carnot.find(".//" + MML_NS + "annotation").text)
    assert meta == {"wave": "W003", "renderer": "mathml", "runtime_evidence": True, "k": "v"}
    assert "Δ" in renderer.render(defs["heat_balance"])
    assert "COP" in renderer.render(defs["cop"])


def test_mathml_superscript_and_number():
    expr = {
        "type": "superscript",
        "base": {"type": "identifier", "value": "x"},
        "sup": {"type": "number", "value": "2"},
    }
    root = ET.fromstring(MathMLRenderer().render({"name": "sq", "expression": expr}))
    sup = root.find(".//" + MML_NS + "msup")
    assert [c.text for c in sup] == ["x", "2"]


@pytest.mark.parametrize(
    "definition,message",
    [
        ("x", "must be a mapping"),
        ({"name": "n"}, "missing required field: expression"),
        ({"name": " ", "expression": {}}, "name must be a non-empty string"),
        ({"name": "n", "expression": "x"}, "equation node must be a mapping"),
        ({"name": "n", "expression": {"type": "matrix"}}, "unsupported node type: matrix"),
        ({"name": "n", "expression": {"type": "number", "value": ""}}, "number node requires"),
        ({"name": "n", "expression": {"type": "greek", "symbol": "xi"}}, "supported symbol"),
        ({"name": "n", "expression": {"type": "row", "items": "x"}}, "list 'items'"),
        ({"name": "n", "expression": {"type": "fraction", "numerator": {"type": "number", "value": "1"}}},
         "numerator and denominator"),
        ({"name": "n", "expression": {"type": "subscript", "base": {"type": "number", "value": "1"}}},
         "subscript node requires base and script"),
    ],
)
def test_mathml_validation_errors(definition, message):
    with pytest.raises(ValueError, match=message):
        MathMLRenderer().validate_definition(definition)


def test_mathml_render_node_rejects_unknown_type():
    with pytest.raises(ValueError, match="unsupported node type: bogus"):
        MathMLRenderer()._render_node({"type": "bogus"})


# --- runtime/federation/qps_debug_dow_consumer -----------------------------

qps = load("runtime/federation/qps_debug_dow_consumer.py")


def test_qps_load_binding_sources(tmp_path, monkeypatch):
    path = tmp_path / "b.json"
    path.write_text('{"a": 1}', encoding="utf-8")
    assert qps.load_binding(path) == {"a": 1}
    monkeypatch.setenv("CODEX_QPS_DEBUG_BINDING_JSON", '{"b": 2}')
    assert qps.load_binding(tmp_path / "missing.json") == {"b": 2}
    assert qps.load_binding(None) == {"b": 2}
    monkeypatch.delenv("CODEX_QPS_DEBUG_BINDING_JSON")
    assert qps.load_binding(None) is None


@pytest.mark.parametrize(
    "binding,expected",
    [
        (None, ("NONE", False)),
        ({"checks": {"runtime_steps_gt_zero": True, "recursive_audit_pass": True}}, ("QPS_REPO_LOCAL", True)),
        ({"checks": {"runtime_steps_gt_zero": True}}, ("QPS_REPO_LOCAL", False)),
        (
            {
                "evidence_mode": "FEDERATED_EXACT_PAYLOAD",
                "checks": {
                    "runtime_steps_gt_zero": True,
                    "source_payload_hash_match": True,
                    "adapter_surface_ready": True,
                    "repo_local_runner_recovered": False,
                },
            },
            ("FEDERATED_EXACT_PAYLOAD", True),
        ),
        (
            {
                "evidence_mode": "FEDERATED_EXACT_PAYLOAD",
                "checks": {
                    "runtime_steps_gt_zero": True,
                    "source_payload_hash_match": True,
                    "adapter_surface_ready": True,
                    "repo_local_runner_recovered": None,
                },
            },
            ("FEDERATED_EXACT_PAYLOAD", False),
        ),
        ({"evidence_mode": "OTHER", "checks": {"runtime_steps_gt_zero": True}}, ("OTHER", False)),
    ],
)
def test_qps_evidence_modes(binding, expected):
    mode, ok, _ = qps.evidence_ok_for_mode(binding)
    assert (mode, ok) == expected


def _qps_main(monkeypatch, tmp_path, binding):
    monkeypatch.setattr(qps, "OUT", tmp_path / "gen")
    monkeypatch.delenv("CODEX_QPS_DEBUG_BINDING_JSON", raising=False)
    argv = ["prog"]
    if binding is not None:
        bpath = tmp_path / "binding.json"
        bpath.write_text(json.dumps(binding), encoding="utf-8")
        argv += ["--binding", str(bpath)]
    monkeypatch.setattr(sys, "argv", argv)
    assert qps.main() == 0
    return json.loads((tmp_path / "gen" / "qps_debug_dow_binding.json").read_text(encoding="utf-8"))


def test_qps_main_accepts_exact_binding(tmp_path, monkeypatch, capsys):
    receipt = _qps_main(
        monkeypatch,
        tmp_path,
        {
            "semantic_owner": "CODEX/KEB",
            "status": "ACCEPT",
            "producer_exact_head_sha": "abc123",
            "binding_sha256": "f00",
            "checks": {"runtime_steps_gt_zero": True, "recursive_audit_pass": True},
        },
    )
    assert receipt["status"] == "ACCEPT"
    assert receipt["reason"] == "EXACT_KEB_QPS_REPO_LOCAL_RUNTIME_BINDING_ACCEPT"
    assert receipt["emit_for_child_disposition"] is True
    assert receipt["source_binding_sha256"] == "f00"
    assert len(receipt["receipt_sha256"]) == 64
    assert '"status": "ACCEPT"' in capsys.readouterr().out


def test_qps_main_defers_without_binding_or_unknown_sha(tmp_path, monkeypatch):
    absent = _qps_main(monkeypatch, tmp_path, None)
    assert absent["status"] == "DEFER" and absent["evidence_mode"] == "NONE"
    assert absent["checks"]["exact_producer_sha_present"] is False
    unknown = _qps_main(
        monkeypatch,
        tmp_path,
        {
            "semantic_owner": "CODEX/KEB",
            "status": "ACCEPT",
            "producer_exact_head_sha": "UNKNOWN",
            "checks": {"runtime_steps_gt_zero": True, "recursive_audit_pass": True},
        },
    )
    assert unknown["status"] == "DEFER"
    assert unknown["reason"] == "KEB_QPS_REPO_LOCAL_RUNTIME_BINDING_NOT_ACCEPTABLE_OR_ABSENT"


# --- runtime/federation/w259_method_cards_independent_dow -------------------

w259 = load("runtime/federation/w259_method_cards_independent_dow.py")


def test_w259_require_and_acyclic():
    w259.require(True, "ok")
    with pytest.raises(SystemExit, match="FAIL: boom"):
        w259.require(False, "boom")
    nodes = {"a", "b", "c"}
    assert w259.acyclic(nodes, [["a", "b", "REQUIRES"], ["b", "c", "FEEDS"], ["c", "a", "CHALLENGES"]])
    assert not w259.acyclic(nodes, [["a", "b", "REQUIRES"], ["b", "a", "CALIBRATES"]])


def _w259_main(monkeypatch, tmp_path, sha, blob):
    out = tmp_path / "w259" / "receipt.json"
    monkeypatch.setattr(sys, "argv", ["prog", "--codex-sha", sha, "--codex-receipt-blob", blob, "--out", str(out)])
    rc = w259.main()
    return rc, json.loads(out.read_text(encoding="utf-8"))


def test_w259_main_passes_on_pinned_fixtures(tmp_path, monkeypatch):
    rc, receipt = _w259_main(monkeypatch, tmp_path, w259.EXPECTED_CODEX_MERGE, w259.EXPECTED_CODEX_RECEIPT_BLOB)
    failed = [k for k, v in receipt["checks"].items() if not v]
    assert failed == []
    assert rc == 0 and receipt["status"] == "PASS"
    assert receipt["kpi"]["semantic_parity"] == 1.0
    assert receipt["kpi"]["authority_inversion_count"] == 0


def test_w259_main_fails_on_wrong_pins(tmp_path, monkeypatch):
    rc, receipt = _w259_main(monkeypatch, tmp_path, "0" * 40, "1" * 40)
    assert rc == 1 and receipt["status"] == "FAIL"
    assert receipt["checks"]["codex_merge_exact"] is False
    assert receipt["checks"]["codex_receipt_blob_exact"] is False
    assert receipt["kpi"]["check_pass_count"] == receipt["kpi"]["check_total"] - 2


# --- runtime/federation/gg_math_temporal_pca_independent_challenge ----------

pca = load("runtime/federation/gg_math_temporal_pca_independent_challenge.py")


def test_pca_run_challenges_all_pass():
    results, numeric = pca.run_challenges()
    assert set(results) == set(pca.CHALLENGES)
    assert all(results.values())
    assert numeric["C04_max_expected_delta"] <= 1e-7


def test_pca_component_alignment_rejects_mismatched_counts():
    with pytest.raises(ValueError, match="component counts differ"):
        pca.component_alignment([[1.0], [0.0]], [[1.0, 0.0], [0.0, 1.0]], [1.0], [1.0, 0.5])


def test_pca_component_alignment_zero_column():
    result = pca.component_alignment([[0.0, 0.0], [0.0, 1.0]], [[1.0, 0.0], [0.0, 1.0]], [3.0, 1.0], [3.0, 1.0])
    assert result["classification"] == "COMPONENT_LEVEL_CHANGE_OR_DEGENERACY"
    assert result["any_component_identity_ambiguous"] is False


@pytest.mark.parametrize(
    "prev,cur,threshold,transition,crossing",
    [
        (0.1, 0.5, 0.3, "STRENGTHENING_SAME_DIRECTION", "FAIL_TO_PASS"),
        (0.4, 0.4, 0.3, "UNCHANGED_MAGNITUDE", "NONE"),
        (0.4, -0.4, 0.3, "DIRECTION_REVERSAL", "NONE"),
        (0.0, 0.2, 0.3, "STRENGTHENING_SAME_DIRECTION", "NONE"),
    ],
)
def test_pca_signed_effect_transition(prev, cur, threshold, transition, crossing):
    result = pca.signed_effect_transition(prev, cur, threshold)
    assert result["transition"] == transition and result["threshold_crossing"] == crossing


def test_pca_temporal_path_zero_displacement():
    metrics = pca.temporal_path_metrics(
        [
            {"k": 0, "t": 0.0, "a": 0.0, "value": [0.0]},
            {"k": 1, "t": 1.0, "a": 1.0, "value": [1.0]},
            {"k": 2, "t": 2.0, "a": 2.0, "value": [0.0]},
        ]
    )
    assert metrics["cumulative_path_length"] == 2.0
    assert metrics["path_to_displacement_ratio"] == math.inf


def _pca_binding(**overrides):
    binding = {
        "schema": "codex.keb.gg_math_temporal_pca_binding.v2",
        "status": "ACCEPT",
        "semantic_owner": "CODEX/KEB",
        "source_sha": pca.EXPECTED_PROVIDER_HEAD,
        "source_merge_sha": pca.EXPECTED_PROVIDER_MERGE,
        "source_artifact_digest": pca.EXPECTED_ARTIFACT,
        "provider_runtime_result": "PASS",
        "provider_challenges": list(pca.CHALLENGES),
        "authority_transfer": False,
        "hard_gate_compensation_allowed": False,
        "downstream_consumer": "GBOGEB/ABACUS/DOW",
    }
    binding.update(overrides)
    return binding


def test_pca_validate_binding():
    assert all(pca.validate_binding(_pca_binding(), pca.EXPECTED_CODEX_MERGE).values())
    checks = pca.validate_binding(_pca_binding(provider_challenges=["C01_SIGN_FLIP"]), "deadbeef")
    assert checks["codex_revision_pinned"] is False and checks["challenge_set"] is False


@pytest.mark.parametrize("good", [True, False])
def test_pca_main(tmp_path, monkeypatch, good):
    bpath = tmp_path / "binding.json"
    bpath.write_text(json.dumps(_pca_binding(status="ACCEPT" if good else "DEFER")), encoding="utf-8")
    out = tmp_path / "o" / "r.json"
    monkeypatch.setattr(
        sys, "argv", ["prog", "--binding", str(bpath), "--codex-sha", pca.EXPECTED_CODEX_MERGE, "--out", str(out)]
    )
    rc = pca.main()
    receipt = json.loads(out.read_text(encoding="utf-8"))
    assert rc == (0 if good else 1)
    assert receipt["status"] == ("PASS" if good else "FAIL")
    assert receipt["kpi"]["schema_parity"] == (1.0 if good else 0.0)
    assert receipt["kpi"]["independent_reproduction_pass_ratio"] == 1.0
