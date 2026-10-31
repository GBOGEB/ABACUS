"""Behaviour tests for tools/everred_v3/scripts/upgrade_dashboard.py.

The script does all of its work at import time against
``<parent of scripts>/dashboard/template.html``. Each test executes the real
file with ``__file__`` pointing into a tmp_path replica, so the repository
template is never touched. Text I/O defaults are pinned per test because the
script relies on the platform locale encoding.
"""

import importlib.util
import pathlib

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT

SCRIPT = REPO_ROOT / "tools/everred_v3/scripts/upgrade_dashboard.py"

OLD_BUTTON = '<button data-scroll="data"><span>⤴</span> Data exchange</button>'
SVG_SCRIPT = '<script id="svg-data" type="application/json">@@SVGJSON@@</script>'
VISUALS = "const visuals=JSON.parse(document.getElementById('svg-data').textContent);"
TEMPLATE = "\n".join(
    [
        "<nav>" + OLD_BUTTON + "</nav>",
        '<section id="data" class="section">data</section>',
        SVG_SCRIPT,
        "<script>",
        VISUALS,
        "function renderRoots(){return 1;}",
        "function renderAll(){",
        " renderRoots();",
        "}",
        "</script>",
        "",
    ]
)


def _pin_encoding(monkeypatch, default):
    original_read = pathlib.Path.read_text
    original_write = pathlib.Path.write_text

    def read_text(self, encoding=None, errors=None):
        return original_read(self, encoding=encoding or default, errors=errors)

    def write_text(self, data, encoding=None, errors=None, newline=None):
        return original_write(
            self,
            data,
            encoding=encoding or default,
            errors=errors,
            newline=newline,
        )

    monkeypatch.setattr(pathlib.Path, "read_text", read_text)
    monkeypatch.setattr(pathlib.Path, "write_text", write_text)


def _template(tmp_path, text=TEMPLATE):
    path = tmp_path / "everred" / "dashboard" / "template.html"
    path.parent.mkdir(parents=True)
    path.write_bytes(text.encode("utf-8"))
    return path


def _run(tmp_path):
    spec = importlib.util.spec_from_file_location("abn_w4_upgrade_dashboard", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    # A distinct basename keeps coverage attributing lines to the real script.
    module.__file__ = str(tmp_path / "everred" / "scripts" / "relocated.py")
    spec.loader.exec_module(module)
    return module


def test_upgrade_inserts_control_panel(tmp_path, monkeypatch):
    _pin_encoding(monkeypatch, "utf-8")
    path = _template(tmp_path)

    module = _run(tmp_path)

    out = path.read_text(encoding="utf-8")
    assert module.p == path
    assert module.P == tmp_path / "everred"
    assert '<button data-scroll="control">' in out
    assert out.index('data-scroll="control"') < out.index('data-scroll="data"')
    assert out.index('<section id="control"') < out.index('<section id="data"')
    assert '<script id="pulse-data" type="application/json">@@PULSES@@</script>' in out
    assert '<script id="alerts-data" type="application/json">@@ALERTS@@</script>' in out
    assert "const pulses=JSON.parse(" in out
    assert "const nativeAlerts=JSON.parse(" in out
    assert out.index("function renderControl(){") < out.index("function renderRoots(){")
    assert " renderRoots();renderControl();\n}" in out


def test_upgrade_is_idempotent(tmp_path, monkeypatch):
    _pin_encoding(monkeypatch, "utf-8")
    path = _template(tmp_path)
    _run(tmp_path)
    once = path.read_bytes()
    _run(tmp_path)
    assert path.read_bytes() == once
    assert path.read_text(encoding="utf-8").count('id="control"') == 1


def test_already_upgraded_template_is_left_unchanged(tmp_path, monkeypatch):
    _pin_encoding(monkeypatch, "utf-8")
    text = '<section id="control" class="section">done</section>\n'
    path = _template(tmp_path, text)
    module = _run(tmp_path)
    assert module.s == text
    assert path.read_text(encoding="utf-8") == text


def test_missing_template_raises(tmp_path, monkeypatch):
    _pin_encoding(monkeypatch, "utf-8")
    with pytest.raises(FileNotFoundError):
        _run(tmp_path)


def test_production_defect_locale_encoding_breaks_upgrade(tmp_path, monkeypatch):
    """production_defect: upgrade_dashboard reads/writes template.html with the locale encoding, so a cp1252 locale (Windows default) crashes and truncates the template; this test fails once fixed"""
    _pin_encoding(monkeypatch, "cp1252")
    path = _template(tmp_path)
    before = path.stat().st_size
    with pytest.raises(UnicodeEncodeError):
        _run(tmp_path)
    assert path.stat().st_size < before
