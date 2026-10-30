"""Lane A wave 5: myrrha_handover/master utilities, validator and renderer.

The scripts write next to themselves (master/ and the handover root). Tests
point every output at tmp_path so the tracked files stay untouched.
"""

import json
import pathlib
import runpy
import sys

import pytest

from tests.coverage_waves.lane_a._load import REPO, load

HANDOVER = REPO / "myrrha_handover"
VALIDATOR = HANDOVER / "master" / "validate_consistency.py"

cu = load("myrrha_handover/master/compute_utilities.py")
ra = load("myrrha_handover/master/render_all.py")


@pytest.fixture(scope="module")
def icd():
    return cu.load_icd()


def test_hp_linear_laws(icd):
    assert cu.hp_per_unit_power_kW(112.0, icd) == pytest.approx(357)
    assert cu.hp_per_unit_power_kW(56.0, icd) == pytest.approx(178.5)
    assert cu.hp_per_unit_recoverable_kW(112.0, icd) == pytest.approx(229)
    assert cu.hp_frequency_Hz(112.0, icd) == pytest.approx(72.0)
    assert cu.hp_frequency_Hz(56.0, icd) == pytest.approx(36.0)


def test_hp_fleet_feasible_and_infeasible(icd):
    ok = cu.hp_fleet(326, 3, icd)
    assert ok["feasible"] is True and ok["feasibility_note"] == "OK"
    assert ok["flow_per_unit_g_s"] == pytest.approx(108.667)
    assert ok["fleet_input_power_kW"] == pytest.approx(round(357 * 326 / 112, 1))
    assert ok["fleet_residual_heat_kW"] == pytest.approx(
        round((357 - 229) * 326 / 112, 1)
    )
    too_fast = cu.hp_fleet(350, 3, icd)
    assert too_fast["feasible"] is False
    assert "infeasible" in too_fast["feasibility_note"]
    too_many = cu.hp_fleet(100, 5, icd)
    assert too_many["feasible"] is False


def test_pvps_and_qrb_blocks(icd):
    pvps = cu.pvps_fleet(2, icd)
    assert pvps["n_running_ASSUMED"] == 2
    each = icd["pvps"]["motor_power_kW_each"]
    assert pvps["fleet_motor_power_kW"] == pytest.approx(round(each * 2, 1))
    assert "OPEN" in pvps["running_count_status"]
    cc = cu.qrb_cc_block(icd)
    assert (
        cc["sizing_basis_contract_kW"]
        == icd["qrb_cc_electrical"]["contract_envelope_kW_total"]
    )
    assert cc["status"].startswith("OPEN")


def test_cooling_water_flow(icd):
    # 36.75 kW / (3.5 kJ/kgK * 10 K) = 1.05 kg/s = 0.001 m3/s = 3.6 m3/h
    assert cu.cooling_water_flow_m3h(36.75, icd) == pytest.approx(3.6)


def test_build_utilities_structure(icd):
    block = cu.build_utilities(icd)
    assert block["nominal_anchor_mdot_HP_total_g_s"] == 326
    configs = block["hp_configurations_at_anchor"]
    assert set(configs) == {"HP_CFG_3_OF_4", "HP_CFG_4_OF_4"}
    inv = block["hp_config_invariance_check_kW"]
    assert inv["HP_CFG_3_OF_4"] == pytest.approx(inv["HP_CFG_4_OF_4"], abs=0.2)
    rows = {r["mdot_HP_total_g_s"]: r for r in block["hp_flow_power_scaling"]}
    assert rows[350]["3_units"]["feasible"] is False
    assert rows[350]["4_units"]["feasible"] is True
    assert configs["HP_CFG_3_OF_4"]["cw_flow_m3h_from_recoverable"] > 0
    assert block["open_items"] == icd["open_items"]
    assert len(block["_sources"]) == 3


def test_main_prints_json(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["compute_utilities.py"])
    assert cu.main() == 0
    assert (
        json.loads(capsys.readouterr().out)["nominal_anchor_mdot_HP_total_g_s"] == 326
    )


@pytest.mark.parametrize("with_pvps", [True, False])
def test_main_write_patches_data(tmp_path, monkeypatch, capsys, with_pvps):
    data = {"PVPS": {"utilities": {"old": 1}}} if with_pvps else {"other": 1}
    target = tmp_path / "data.json"
    target.write_bytes(json.dumps(data).encode())
    monkeypatch.setattr(cu, "DATA_PATH", target)
    monkeypatch.setattr(sys, "argv", ["compute_utilities.py", "--write"])
    assert cu.main() == 0
    patched = json.loads(target.read_text(encoding="utf-8"))
    assert "icd_bound_utilities" in patched
    assert ("_DEPRECATED" in patched.get("PVPS", {}).get("utilities", {})) is with_pvps
    assert "Patched" in capsys.readouterr().out


def _good_icd_block():
    return {
        "hp_config_invariance_check_kW": {
            "HP_CFG_3_OF_4": 1039.1,
            "HP_CFG_4_OF_4": 1039.1,
        },
        "nominal_anchor_mdot_HP_total_g_s": 326,
        "pvps": {"running_count_status": "OPEN (PVPS-RUN-COUNT)"},
    }


def _run_validator(tmp_path, monkeypatch, data, views):
    """Run validate_consistency.py with its handover root redirected to tmp_path."""
    root = tmp_path / "handover"
    (root / "master").mkdir(parents=True)
    (root / "master" / "data.json").write_bytes(json.dumps(data).encode())
    for name, text in views.items():
        (root / name).write_bytes(text.encode())

    def redirect(path):
        try:
            return root / pathlib.Path(path).relative_to(HANDOVER)
        except ValueError:
            return pathlib.Path(path)

    orig_read, orig_write, orig_glob = (
        pathlib.Path.read_text,
        pathlib.Path.write_text,
        pathlib.Path.glob,
    )
    monkeypatch.setattr(
        pathlib.Path, "read_text", lambda p, *a, **k: orig_read(redirect(p), *a, **k)
    )
    monkeypatch.setattr(
        pathlib.Path, "write_text", lambda p, *a, **k: orig_write(redirect(p), *a, **k)
    )
    monkeypatch.setattr(
        pathlib.Path, "glob", lambda p, *a, **k: orig_glob(redirect(p), *a, **k)
    )
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(VALIDATOR))
    report = json.loads(orig_read(root / "master" / "consistency_report.json"))
    return exc.value.code, report


def test_validator_passes_and_flags_findings(tmp_path, monkeypatch, capsys):
    views = {
        "a.html": "Design baseline 350 g/s here. HP + PVPS = 350 total.",
        "b.html": "Legacy design 350 g/s (superseded).",
        "c.html": "isothermal work / 0.5 gives power",
        "d.html": "nothing to see",
    }
    code, report = _run_validator(
        tmp_path, monkeypatch, {"icd_bound_utilities": _good_icd_block()}, views
    )
    assert code == 0
    assert report["pass"] is True and report["failures"] == []
    kinds = sorted((f["view"], f["kind"]) for f in report["findings"])
    assert kinds == [
        ("a.html", "additive_flow"),
        ("a.html", "stale_anchor_350"),
        ("c.html", "isothermal_basis"),
    ]
    assert "hard failures : 0" in capsys.readouterr().out


def test_validator_missing_block_fails(tmp_path, monkeypatch, capsys):
    code, report = _run_validator(tmp_path, monkeypatch, {}, {})
    assert code == 1
    assert report["failures"] == ["icd_bound_utilities block missing from data.json"]
    assert "FAIL: icd_bound_utilities block missing" in capsys.readouterr().out


def test_validator_inconsistent_block_fails(tmp_path, monkeypatch):
    block = _good_icd_block()
    block["hp_config_invariance_check_kW"]["HP_CFG_4_OF_4"] = 900.0
    block["nominal_anchor_mdot_HP_total_g_s"] = 350
    block["pvps"] = {"running_count_status": "CLOSED"}
    code, report = _run_validator(
        tmp_path, monkeypatch, {"icd_bound_utilities": block}, {}
    )
    assert code == 1
    assert len(report["failures"]) == 3
    assert any("326" in f for f in report["failures"])
    assert any("OPEN" in f for f in report["failures"])


def test_parse_frontmatter_scalars_and_blocks():
    fm = ra.parse_frontmatter(
        "id: s1\ntitle: Hello\nnotes: |\n  line one\n  line two\n"
    )
    assert fm == {"id": "s1", "title": "Hello", "notes": "line one\nline two"}
    fm2 = ra.parse_frontmatter("notes: |\n  a\nunindented\nlayout: x")
    assert fm2 == {"notes": "a\nunindented", "layout": "x"}


def test_md_to_html_constructs():
    md = "\n".join(
        [
            "# Title",
            "### Sub",
            "```",
            "<raw> & code",
            "```",
            "- one",
            "* two",
            "1. first",
            "2. second",
            "",
            "para **bold** and *em*",
            "continues `code`",
            "## Next",
        ]
    )
    out = ra.md_to_html(md)
    assert "<h1>Title</h1>" in out and "<h3>Sub</h3>" in out
    assert '<pre class="ascii"><code>&lt;raw&gt; &amp; code</code></pre>' in out
    assert "<ul><li>one</li><li>two</li></ul>" in out
    assert "<ol><li>first</li><li>second</li></ol>" in out
    assert (
        "<p>para <strong>bold</strong> and <em>em</em> continues <code>code</code></p>"
        in out
    )
    assert out.endswith("<h2>Next</h2>")


def test_parse_slides_and_render():
    md = "preamble\n---\nid: a\ntitle: A & B\nsubtitle: S\ncaption: C\n"
    md += "notes: TODO check\n---\nBody **x**\n---\nlayout: two\n---\n"
    slides = ra.parse_slides(md)
    assert [s.get("id") for s in slides] == ["a", None]
    assert slides[0]["body"] == "Body **x**"
    assert slides[1]["body"] == ""
    html_a = ra.render_slide(slides[0], 0, 2)
    assert 'id="a"' in html_a and "A &amp; B" in html_a
    assert '<div class="sub">S</div>' in html_a
    assert '<div class="caption">C</div>' in html_a
    assert "<b>TODO</b>" in html_a
    html_b = ra.render_slide(slides[1], 1, 2)
    assert 'id="slide-1"' in html_b and "layout-two" in html_b
    assert 'class="sub"' not in html_b and "Slide notes" not in html_b


@pytest.fixture
def render_root(tmp_path, monkeypatch):
    master = tmp_path / "master"
    master.mkdir()
    (master / "config.yaml").write_bytes(b'theme:\n  primary: "#123456"\n  fg: #000\n')
    slides_md = "---\nid: cover\ntitle: Cover\n---\nHello\n---\ntitle: Two\n---\nBye\n"
    (master / "slides.md").write_bytes(slides_md.encode())
    out_dir = tmp_path / "slides"
    out_dir.mkdir()
    monkeypatch.setattr(ra, "ROOT", tmp_path)
    monkeypatch.setattr(ra, "MASTER", master)
    monkeypatch.setattr(ra, "OUT_SLIDES", tmp_path / "slides.html")
    monkeypatch.setattr(ra, "OUT_DIR", out_dir)
    return tmp_path


def test_load_config(render_root):
    cfg = ra.load_config()
    assert cfg["primary"] == "#123456" and cfg["fg"] == "#000"
    assert cfg["accent"] == "#ff8a00"


def _utf8_default_write_text(monkeypatch):
    # main() writes non-ASCII HTML with Path.write_text() and no encoding, which
    # crashes on non-UTF-8 locales such as Windows cp1252 (a production_defect,
    # see WAVE_LEDGER.jsonl). Default the encoding to UTF-8 so the behaviour test
    # is portable; a fix that passes encoding="utf-8" still passes here.
    original = pathlib.Path.write_text

    def write_text(path, data, encoding=None, *args, **kwargs):
        return original(path, data, encoding or "utf-8", *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "write_text", write_text)


def test_main_renders_deck(render_root, capsys, monkeypatch):
    tmp_path = render_root
    out_dir = tmp_path / "slides"
    _utf8_default_write_text(monkeypatch)
    ra.main()
    deck = (tmp_path / "slides.html").read_text(encoding="utf-8")
    assert "--primary:#123456" in deck and deck.count('<section class="slide') == 2
    assert sorted(p.name for p in out_dir.iterdir()) == ["cover.html", "slide-1.html"]
    index = json.loads((tmp_path / "slides.json").read_text(encoding="utf-8"))
    assert [s["id"] for s in index] == ["cover", "slide-1"]
    assert index[1]["layout"] == "text-only"
    assert "Rendered 2 slides" in capsys.readouterr().out
