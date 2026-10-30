"""Behaviour tests for governance/engines/WCAG_CONTRAST_CHECKER.py."""

import json

import pytest

from tests.coverage_waves.lane_a._load import load

mod = load("integration/gbogeb_session/governance/engines/WCAG_CONTRAST_CHECKER.py")


def test_hex_to_rgb_variants():
    assert mod.hex_to_rgb("#ffffff") == (255, 255, 255)
    assert mod.hex_to_rgb("abc") == (170, 187, 204)
    assert mod.hex_to_rgb("#11223344") == (17, 34, 51)


def test_hex_to_rgb_invalid_length():
    with pytest.raises(ValueError):
        mod.hex_to_rgb("#12345")


def test_luminance_and_ratio_extremes():
    assert mod.relative_luminance(0, 0, 0) == 0.0
    assert mod.relative_luminance(255, 255, 255) == pytest.approx(1.0)
    # low channel value goes through the linear branch
    assert mod.relative_luminance(5, 5, 5) == pytest.approx(5 / 255 / 12.92)
    ratio = mod.contrast_ratio((0, 0, 0), (255, 255, 255))
    assert ratio == pytest.approx(21.0)
    assert mod.contrast_ratio((255, 255, 255), (0, 0, 0)) == pytest.approx(21.0)
    assert mod.contrast_ratio((10, 20, 30), (10, 20, 30)) == pytest.approx(1.0)


def test_rgb_to_hex():
    assert mod.rgb_to_hex(255, 0, 16) == "#ff0010"


def test_finding_to_dict_and_str():
    f = mod.check_color_pair("#000000", "#FFFFFF")
    d = f.to_dict()
    assert d["ratio"] == 21.0
    assert d["passed"] is True
    assert d["required_ratio"] == mod.CONTRAST_AA_NORMAL
    assert d["level"] == "AA"
    assert str(f).startswith("[PASS] inline check")
    bad = mod.check_color_pair("#777777", "#888888", context="large_text")
    assert bad.required_ratio == mod.CONTRAST_AA_LARGE
    assert not bad.passed
    assert str(bad).startswith("[FAIL]")


def test_results_summary_and_json():
    res = mod.ContrastResults()
    assert res.passed
    assert "PASS" in res.summary()
    res.add(mod.check_color_pair("#000000", "#FFFFFF"))
    res.add(mod.check_color_pair("#EEEEEE", "#FFFFFF"))
    assert not res.passed
    assert len(res.failures) == 1
    summary = res.summary()
    assert "FAIL" in summary
    assert "Total:   2" in summary
    data = json.loads(res.to_json())
    assert data["total"] == 2
    assert data["failures"] == 1
    assert data["passed"] is False


def test_check_theme_missing(tmp_path, capsys):
    res = mod.check_theme_file(str(tmp_path / "nope.yaml"))
    assert res.findings == []
    assert "not found" in capsys.readouterr().err


THEME = """\
themes:
  light:
    surface:
      primary: "#FFFFFF"
    text:
      body: "#000000"
      faint: "#EEEEEE"
      overlay: "rgba(0,0,0,0.5)"
      count: 5
      broken: "#12345"
    intent:
      danger: "#CC0000"
      danger_text: "#000000"
      pale: "#FAFAFA"
      tint: "rgba(1,1,1,1)"
      bad: "#zz"
    data_viz:
      series_1: "#003366"
      grid_line: "#EEEEEE"
      axis_label: "#EEEEEE"
      shade: "rgba(1,1,1,1)"
      oops: "#1234"
  bare: {}
"""


def test_check_theme_file(tmp_path):
    p = tmp_path / "theme.yaml"
    p.write_text(THEME, encoding="utf-8")
    res = mod.check_theme_file(str(p))
    locs = {f.location: f for f in res.findings}
    assert len(res.findings) == 5
    body = locs["themes.light.text.body on surface.primary"]
    assert body.passed and body.context_type == "normal_text"
    assert not locs["themes.light.text.faint on surface.primary"].passed
    danger = locs["themes.light.intent.danger on surface.primary"]
    assert danger.passed and danger.required_ratio == mod.CONTRAST_AA_LARGE
    assert not locs["themes.light.intent.pale on surface.primary"].passed
    assert locs["themes.light.data_viz.series_1 on surface.primary"].passed
    assert not any("grid_line" in loc for loc in locs)
    assert not any("danger_text" in loc for loc in locs)
    assert not res.passed


CSS = """\
.a { color: #000000; background-color: #FFFFFF; }
.b { color: #EEEEEE; background: #FFFFFF; }
.c { color: #000; }
.d { color: #12345; background: #FFFFFF; }
"""


def test_scan_css_file(tmp_path):
    p = tmp_path / "style.css"
    p.write_text(CSS, encoding="utf-8")
    res = mod.scan_css_file(str(p))
    assert len(res.findings) == 2
    assert res.findings[0].passed
    assert not res.findings[1].passed
    assert all(f.location == str(p) for f in res.findings)


def test_scan_css_missing(tmp_path):
    assert mod.scan_css_file(str(tmp_path / "x.css")).findings == []


def _run(monkeypatch, *argv):
    monkeypatch.setattr("sys.argv", ["wcag", *argv])
    return mod.main()


def test_main_check_text_pass(monkeypatch, capsys):
    assert _run(monkeypatch, "--check", "#000000", "#FFFFFF") == 0
    out = capsys.readouterr().out
    assert "Contrast ratio: 21.00:1" in out
    assert "WCAG AA: PASS" in out


def test_main_check_json_fail(monkeypatch, capsys):
    rc = _run(monkeypatch, "--check", "#EEEEEE", "#FFFFFF", "--format", "json")
    assert rc == 1
    assert json.loads(capsys.readouterr().out)["passed"] is False


def test_main_theme_json(tmp_path, monkeypatch, capsys):
    p = tmp_path / "theme.yaml"
    p.write_text(THEME, encoding="utf-8")
    assert _run(monkeypatch, "--theme", str(p), "--format", "json") == 1
    assert json.loads(capsys.readouterr().out)["total"] == 5


def test_main_css_text_pass(tmp_path, monkeypatch, capsys):
    p = tmp_path / "ok.css"
    p.write_text(".a { color: #000; background: #fff; }", encoding="utf-8")
    assert _run(monkeypatch, "--css", str(p), "--level", "AAA") == 0
    out = capsys.readouterr().out
    assert "[PASS]" in out
    assert "WCAG CONTRAST CHECK: PASS" in out


def test_main_requires_input(monkeypatch):
    with pytest.raises(SystemExit):
        _run(monkeypatch)
