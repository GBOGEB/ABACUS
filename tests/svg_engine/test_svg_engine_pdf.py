"""SVG-ENGINE layered PDF: nested OCG builder (W2), flat baseline (W1) and the fidelity ladder."""

from __future__ import annotations

import json

import pytest

from tests.svg_engine.conftest import require

require("lxml", "numpy", "fitz", "cairosvg")
import fitz  # noqa: E402

from svg_engine import fidelity, fixtures, ingress, pdf_ocg  # noqa: E402
from svg_engine.__main__ import main as cli  # noqa: E402


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("pdf")
    root = ingress.parse_svg(fixtures.synthetic_layered_svg())
    nested = pdf_ocg.build_nested_ocg_pdf(
        root,
        out / "nested.pdf",
        page_presets=fixtures.SYNTHETIC_PAGE_PRESETS,
        source_bytes=fixtures.synthetic_layered_svg(),
    )
    flat = pdf_ocg.build_flat_ocg_pdf(root, out / "flat.pdf")
    return root, out, nested, flat


def test_nested_build_report(built):
    _, out, nested, _ = built
    assert nested["ocg_count"] == 8 and nested["paint_runs"] == 9
    assert nested["source_svg_sha256"] == ingress.sha(fixtures.synthetic_layered_svg())
    assert nested["pages"][1]["runs_skipped"] == 0
    assert nested["pages"][2]["runs_skipped"] == 2  # the "annot" subtree
    assert nested["pages"][1]["max_nesting_depth"] == 2
    with fitz.open(out / "nested.pdf") as d:
        assert len(d) == 2
        assert d.xref_get_key(d.pdf_catalog(), "PageMode")[1] == "/UseOC"
        content = d[0].read_contents().decode("ascii")
        assert "/OC /L_base BDC" in content and "/OC /L_base_detail_on BDC" in content


def test_nested_build_is_deterministic(built, tmp_path):
    root, _, nested, _ = built
    again = pdf_ocg.build_nested_ocg_pdf(
        root, tmp_path / "again.pdf", page_presets=fixtures.SYNTHETIC_PAGE_PRESETS
    )
    assert again["sha256"] == nested["sha256"]


def test_order_tree_mirrors_hierarchy(built):
    root, out, nested, _ = built
    layers = ingress.layer_items(root)
    ocg = nested["ocg_xref_by_layer"]
    with fitz.open(out / "nested.pdf") as d:
        parent_of = fidelity.parse_order(d)
    for layer in layers:
        assert parent_of[ocg[layer["id"]]] == (
            ocg[layer["parent_id"]] if layer["parent_id"] else None
        )
    assert pdf_ocg.order_array(layers, ocg).startswith("[ ")


def test_fidelity_ladder_passes_on_synthetic_source(built):
    root, out, nested, _flat = built
    receipt = fidelity.check_pdf_fidelity(
        out / "nested.pdf", nested, root, baseline_pdf=out / "flat.pdf"
    )
    results = {c["id"]: c["result"] for c in receipt["checks"]}
    assert receipt["summary"]["FAIL"] == 0, [
        c for c in receipt["checks"] if c["result"] == "FAIL"
    ]
    for kid in (
        "K4001",
        "K4102",
        "K4111",
        "K4201",
        "K4105",
        "K4106",
        "K4112",
        "K4113",
        "K4114",
        "K4304",
        "K5001",
    ):
        assert results["SVG-W2:" + kid] == "PASS", kid
    per = {p["id"]: p for p in receipt["per_layer"]}
    assert (
        per["hidden_root_child"]["pixels_changed_vs_default"] == 0
    )  # its parent is hidden: inert by design
    assert per["base"]["pixels_changed_vs_default"] > 0


def test_flat_baseline_does_not_cascade(built):
    _, out, _, flat = built
    assert flat["ocg_count"] == 8 and flat["default_hidden_root_ids"] == [
        "hidden_root",
        "alt_scope",
    ]
    with fitz.open(out / "flat.pdf") as d:
        states = {v["name"]: v["on"] for v in d.get_ocgs().values()}
    # W1 default = ancestor-combined: a visible child of a hidden root starts OFF.
    assert states["Hidden root/Child of hidden root [hidden_root_child]"] is False


def test_wrong_ocg_default_is_caught(built, tmp_path):
    root, out, nested, _ = built
    broken = tmp_path / "broken.pdf"
    with fitz.open(out / "nested.pdf") as d:
        d.set_layer(-1, off=[nested["ocg_xref_by_layer"]["base_detail_on"]])
        d.save(broken)
    bad_build = {**nested, "sha256": ingress.sha(broken.read_bytes())}
    receipt = fidelity.check_pdf_fidelity(
        broken, bad_build, root, cascade_ids=[], hidden_parent_ids=[]
    )
    results = {c["id"]: c["result"] for c in receipt["checks"]}
    # K4102 reads the stored defaults; the render checks set every switch explicitly and stay green.
    assert results["SVG-W2:K4102"] == "FAIL" and results["SVG-W2:K4201"] == "PASS"


def test_presets_with_unknown_ids_fail_closed(built, tmp_path):
    root = built[0]
    with pytest.raises(ValueError, match="PRESET_UNKNOWN_LAYER_IDS"):
        pdf_ocg.build_nested_ocg_pdf(
            root, tmp_path / "x.pdf", page_presets={1: {"skip_subtrees": ["nope"]}}
        )


def test_paint_outside_layers_fails_closed(tmp_path):
    root = ingress.parse_svg(
        b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="5" height="5"/></svg>'
    )
    with pytest.raises(ValueError, match="PAINT_OUTSIDE_LAYERS"):
        pdf_ocg.build_nested_ocg_pdf(root, tmp_path / "x.pdf")


def test_font_family_normalisation():
    root = ingress.parse_svg(
        b'<svg xmlns="http://www.w3.org/2000/svg"><text font-family="Arial">a</text>'
        b"<text style=\"font-family:'Times New Roman', serif\">b</text></svg>"
    )
    assert fidelity.requested_font_families(root) == {"arial", "timesnewroman", "serif"}
    assert fidelity.font_family_of("ABCDEF+Arial-BoldMT") == "arial"
    assert fidelity.font_family_of("TimesNewRomanPSMT") == "timesnewroman"


def test_cli_round_trip(tmp_path):
    svg = tmp_path / "s.svg"
    svg.write_bytes(fixtures.synthetic_layered_svg())
    presets = tmp_path / "presets.json"
    presets.write_text(json.dumps(fixtures.SYNTHETIC_PAGE_PRESETS), encoding="utf-8")
    pdf = tmp_path / "s.pdf"
    assert (
        cli(
            [
                "nested-pdf",
                str(svg),
                str(pdf),
                "--presets",
                str(presets),
                "--previews",
                str(tmp_path),
            ]
        )
        == 0
    )
    assert (tmp_path / "s_p2_preview.png").exists()
    assert (
        cli(
            [
                "fidelity",
                str(svg),
                str(pdf),
                str(tmp_path / "receipt.json"),
                "--cascade-ids",
                "base",
            ]
        )
        == 0
    )
    rec = json.loads((tmp_path / "receipt.json").read_text(encoding="utf-8"))
    assert rec["summary"]["FAIL"] == 0
