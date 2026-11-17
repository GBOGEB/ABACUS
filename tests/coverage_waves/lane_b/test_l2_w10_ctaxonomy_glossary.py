"""Lane-B wave 10: CTaxonomy glossary renderer (HTML projection and CLI)."""

import sys

from ._l2_loader import load

gl = load("tools/ctaxonomy/render_ctaxonomy_glossary.py")


def _registry():
    return {
        "terms": {
            "CT-002": {"canonical_term": "Beam <line>", "definition": "A & B"},
            "CT-001": {"definition": "no friendly name"},
        },
        "aliases": {
            "zeta": {"resolves_to": "CT-002"},
            "alpha": {"resolves_to": "CT-002"},
            "orphan": {},
        },
    }


def test_render_sorts_terms_escapes_html_and_joins_sorted_aliases():
    out = gl.render(_registry())
    assert out.startswith("<!doctype html>")
    assert out.endswith("</tbody></table></body></html>\n")
    assert out.index("CT-001") < out.index("CT-002")
    assert "<td>Beam &lt;line&gt;</td>" in out
    assert "<td>A &amp; B</td>" in out
    assert "<td>alpha, zeta</td>" in out
    # Missing canonical_term falls back to the ID; no aliases renders empty.
    assert (
        "<tr><td><code>CT-001</code></td><td>CT-001</td>"
        "<td>no friendly name</td><td></td></tr>"
    ) in out
    assert "orphan" not in out


def test_render_empty_registry_has_no_rows():
    out = gl.render({})
    assert "<tr><td>" not in out
    assert "<tbody>\n\n</tbody>" in out


def test_main_writes_output_and_prints_counts(tmp_path, monkeypatch, capsys):
    reg = tmp_path / "reg.yaml"
    reg.write_text(
        "terms:\n  CT-9:\n    canonical_term: Nine\n    definition: d\n"
        "aliases:\n  nine:\n    resolves_to: CT-9\n",
        encoding="utf-8",
    )
    out = tmp_path / "nested" / "glossary.html"
    monkeypatch.setattr(sys, "argv", ["render", str(reg), str(out)])
    assert gl.main() == 0
    text = out.read_text(encoding="utf-8")
    assert "<td>Nine</td>" in text and "<td>nine</td>" in text
    lines = capsys.readouterr().out.splitlines()
    assert lines == ["CTAXONOMY_RENDER=PASS terms=1", "engineering_credit_delta=0"]


def test_main_with_registry_without_terms(tmp_path, monkeypatch, capsys):
    reg = tmp_path / "reg.yaml"
    reg.write_text("aliases: {}\n", encoding="utf-8")
    out = tmp_path / "g.html"
    monkeypatch.setattr(sys, "argv", ["render", str(reg), str(out)])
    assert gl.main() == 0
    assert "terms=0" in capsys.readouterr().out
    assert out.exists()
