"""SVG-ENGINE W1 ingress and paint-run splitter on the synthetic layered SVG."""
from __future__ import annotations

import zipfile

import pytest

from tests.svg_engine.conftest import require

require("lxml")
from lxml import etree  # noqa: E402

from svg_engine.fixtures import synthetic_layered_svg  # noqa: E402
from svg_engine.ingress import (  # noqa: E402
    assert_operating_state_evidence,
    layer_items,
    layer_tree_report,
    load_svg,
    parse_svg,
    sha,
    validate_native_svg,
)
from svg_engine.paint_runs import ROOT_OWNER, isolated_svg, paint_atoms  # noqa: E402


def test_layer_items_keep_native_ids_hierarchy_and_own_visibility(synthetic_root):
    layers = layer_items(synthetic_root)
    byid = {x["id"]: x for x in layers}
    assert [x["id"] for x in layers] == ["base", "base_detail_on", "base_detail_off", "annot", "annot_nested",
                                         "hidden_root", "hidden_root_child", "alt_scope"]
    # Two layers share the label "Detail": identity must be the id, never the label.
    assert [x["id"] for x in layers if x["label"] == "Detail"] == ["base_detail_on", "base_detail_off"]
    assert byid["annot_nested"]["parent_id"] == "annot"  # nested through an ordinary <g>
    assert byid["hidden_root"]["source_visible"] is False
    assert byid["hidden_root_child"]["source_visible"] is True  # own style, not ancestor-combined
    assert byid["hidden_root_child"]["path"] == ["Hidden root", "Child of hidden root"]


def test_paint_runs_split_at_nested_layers_in_source_order(synthetic_root):
    atoms, runs = paint_atoms(synthetic_root)
    assert [r["owner"] for r in runs] == ["base", "base_detail_on", "base", "base_detail_off", "annot",
                                          "annot_nested", "hidden_root", "hidden_root_child", "alt_scope"]
    assert not any(r["owner"] == ROOT_OWNER for r in runs)
    assert len(atoms) == sum(len(r["atoms"]) for r in runs) == 9


def test_paint_outside_layers_is_owned_by_root():
    root = parse_svg(b'<svg xmlns="http://www.w3.org/2000/svg"><rect id="loose" width="1" height="1"/></svg>')
    _, runs = paint_atoms(root)
    assert [r["owner"] for r in runs] == [ROOT_OWNER]


def test_isolated_svg_keeps_only_the_run_and_unhides_its_layers(synthetic_root):
    _, runs = paint_atoms(synthetic_root)
    hidden_child = next(r for r in runs if r["owner"] == "hidden_root_child")
    iso = etree.fromstring(isolated_svg(synthetic_root, hidden_child))
    ids = {e.get("id") for e in iso.iter() if isinstance(e.tag, str) and e.get("id")}
    assert "r_hidden_child" in ids and "r_hidden_root" not in ids and "r_base" not in ids
    assert "grad1" in ids  # defs are context, always kept
    for e in iso.iter():
        if e.get("id") in ("hidden_root", "hidden_root_child"):
            assert "display:none" not in (e.get("style") or "")


def test_load_svg_from_zip_and_hash(tmp_path):
    z = tmp_path / "source.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("drawing.svg", synthetic_layered_svg())
        zf.writestr("notes.txt", "x")
    root, raw = load_svg(z)
    assert raw == synthetic_layered_svg() and sha(raw) == sha(synthetic_layered_svg())
    assert len(layer_items(root)) == 8
    with zipfile.ZipFile(z, "a") as zf:
        zf.writestr("second.svg", synthetic_layered_svg())
    with pytest.raises(ValueError, match="SVG_MEMBER_AMBIGUOUS"):
        load_svg(z)
    assert len(layer_items(load_svg(z, member="second.svg")[0])) == 8


@pytest.mark.parametrize("svg, code", [
    (b'<svg><g id="twice"/><g id="twice"/></svg>', "SVG_DUPLICATE_ID"),
    (b'<svg><script id="x">bad</script></svg>', "SVG_UNSAFE_ELEMENT"),
    (b'<svg><image href="https://attacker.invalid/a.svg"/></svg>', "SVG_EXTERNAL_RESOURCE"),
    (b'<svg><rect onclick="alert(1)"/></svg>', "SVG_EVENT_HANDLER"),
])
def test_unsafe_svg_fails_closed(svg, code):
    with pytest.raises(ValueError, match=code):
        validate_native_svg(etree.fromstring(svg))


def test_entities_are_not_resolved():
    xxe = b'<?xml version="1.0"?><!DOCTYPE s [<!ENTITY e SYSTEM "file:///etc/hostname">]><svg><text>&e;</text></svg>'
    root = parse_svg(xxe)
    # The external entity stays an unresolved reference; no file content is read.
    assert "".join(root.itertext()) in ("", "&e;")


@pytest.mark.parametrize("record, code", [
    ({"valve_id": "demo", "state": "OPEN", "colour": "green", "evidence_refs": []}, "VALVE_STATE_WITHOUT_EVIDENCE"),
    ({"state": "CLOSED", "evidence_refs": ["ref"], "owner_accepted": False}, "VALVE_STATE_NOT_OWNER_ACCEPTED"),
    ({"state": "AJAR"}, "INVALID_VALVE_STATE"),
])
def test_operating_state_guard_rejects_unsupported_states(record, code):
    with pytest.raises(ValueError, match=code):
        assert_operating_state_evidence(record)


def test_operating_state_guard_accepts_unknown_and_evidenced_states():
    assert assert_operating_state_evidence({"state": "UNKNOWN"})
    assert assert_operating_state_evidence({"state": "OPEN", "evidence_refs": ["r"], "owner_accepted": True})


def test_layer_tree_report_flags_ordinary_group_nesting(synthetic_root):
    rows = {r["id"]: r for r in layer_tree_report(synthetic_root)}
    assert rows["annot_nested"]["via_ordinary_groups"] == 1
    assert rows["base_detail_on"]["via_ordinary_groups"] == 0
