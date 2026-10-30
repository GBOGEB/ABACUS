"""Lane-B wave 11: docs HTML generator, docs export, ledger summary and timeline."""

import builtins
import functools
import json
import sqlite3
import sys
import types

import pytest

from ._l2_loader import load

dh = load("scripts/generate_docs_html.py")
ed = load("scripts/export_docs.py")
es = load("scripts/export_summary_md.py")
at = load("scripts/make_ascii_timeline.py")


# --------------------------------------------------------------------------
# generate_docs_html
# --------------------------------------------------------------------------


@pytest.fixture
def docs(tmp_path, monkeypatch):
    docs_dir = tmp_path / "docs"
    monkeypatch.setattr(dh, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(dh, "DOCS_DIR", docs_dir)
    monkeypatch.setattr(dh, "MANIFEST_FILE", docs_dir / "manifest.yml")
    return docs_dir


def _write_manifest(docs_dir, text):
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "manifest.yml").write_text(text, encoding="utf-8")


MANIFEST = (
    "# comment\n"
    "\n"
    "site:\n"
    "  title: My Docs\n"
    "  version: 1.2\n"
    "articles:\n"
    "  - a.md\n"
    "  - b.md\n"
    "extra:\n"
    "  - ignored\n"
    "  key: ignored\n"
    "smoke_tested_repos:\n"
    "  - GBOGEB/ABACUS\n"
)


def test_parse_manifest_missing(docs):
    assert dh._parse_manifest() == {
        "site": {"title": "ABACUS Docs", "version": "unknown"},
        "articles": [],
        "smoke_tested_repos": [],
    }


def test_parse_manifest_with_yaml(docs):
    _write_manifest(docs, "site:\n  title: My Docs\narticles:\n  - a.md\n")
    assert dh._parse_manifest() == {
        "site": {"title": "My Docs"},
        "articles": ["a.md"],
    }


def test_parse_manifest_empty_yaml(docs):
    _write_manifest(docs, "")
    assert dh._parse_manifest() == {}


def _expected_fallback():
    return {
        "site": {"title": "My Docs", "version": "1.2"},
        "articles": ["a.md", "b.md"],
        "smoke_tested_repos": ["GBOGEB/ABACUS"],
        "extra": {},
    }


def test_parse_manifest_fallback_import_error(docs, monkeypatch):
    _write_manifest(docs, MANIFEST)
    monkeypatch.setitem(sys.modules, "yaml", None)
    assert dh._parse_manifest() == _expected_fallback()


def test_parse_manifest_fallback_on_yaml_error(docs, monkeypatch):
    _write_manifest(docs, "- orphan\n" + MANIFEST)

    def boom(text):
        raise ValueError("bad yaml")

    monkeypatch.setitem(sys.modules, "yaml", types.SimpleNamespace(safe_load=boom))
    assert dh._parse_manifest() == _expected_fallback()


def test_safe_read_json(tmp_path):
    assert dh._safe_read_json(tmp_path / "none.json") == {}
    bad = tmp_path / "bad.json"
    bad.write_text("{nope", encoding="utf-8")
    assert dh._safe_read_json(bad) == {}
    good = tmp_path / "good.json"
    good.write_text('{"a": 1}', encoding="utf-8")
    assert dh._safe_read_json(good) == {"a": 1}


def test_build_index_html_populated():
    html = dh._build_index_html(
        {
            "site": {"title": "T", "version": "9"},
            "articles": ["x.md"],
            "smoke_tested_repos": ["o/r"],
        }
    )
    assert "<title>T - Entry</title>" in html
    assert "<strong>Version:</strong> 9" in html
    assert '<li><a href="x.md">x.md</a></li>' in html
    assert 'href="https://github.com/o/r"' in html


def test_build_index_html_defaults_and_non_dict():
    html = dh._build_index_html({})
    assert "<title>ABACUS Project Docs - Entry</title>" in html
    assert "No articles listed" in html
    assert "No repositories listed" in html
    html2 = dh._build_index_html(["not", "a", "dict"])
    assert "No articles listed" in html2


def test_build_dashboard_html_reads_state(docs, tmp_path):
    (tmp_path / "maturity_assessment.json").write_text(
        '{"overall_score": 77}', encoding="utf-8"
    )
    state = tmp_path / "DMAIC_V3" / "state"
    state.mkdir(parents=True)
    (state / "convergence_status.json").write_text(
        '{"status": "CONVERGED"}', encoding="utf-8"
    )
    html = dh._build_dashboard_html(
        {"articles": ["a", "b"], "smoke_tested_repos": ["r"]}
    )
    assert '<div class="value">CONVERGED</div>' in html
    assert '<div class="value">77</div>' in html
    assert '<div class="value">2</div>' in html
    assert '<div class="value">1</div>' in html


def test_build_dashboard_html_non_dict_inputs(docs, tmp_path):
    (tmp_path / "maturity_assessment.json").write_text("[1]", encoding="utf-8")
    state = tmp_path / "DMAIC_V3" / "state"
    state.mkdir(parents=True)
    (state / "convergence_status.json").write_text("[2]", encoding="utf-8")
    html = dh._build_dashboard_html(["x"])
    assert '<div class="value">unknown</div>' in html
    assert '<div class="value">n/a</div>' in html
    assert html.count('<div class="value">0</div>') == 2


def test_docs_main(docs, capsys):
    _write_manifest(docs, MANIFEST)
    assert dh.main() == 0
    assert "My Docs" in (docs / "index.html").read_text(encoding="utf-8")
    assert "ABACUS System Dashboard" in (docs / "dashboard.html").read_text(
        encoding="utf-8"
    )
    assert "[OK] Generated" in capsys.readouterr().out


# --------------------------------------------------------------------------
# export_docs
# --------------------------------------------------------------------------


def test_export_docs_copies_sources(tmp_path, monkeypatch, capsys):
    src = tmp_path / "src"
    (src / "sub").mkdir(parents=True)
    (src / "a.md").write_text("A", encoding="utf-8")
    (src / "sub" / "d.MMD").write_text("D", encoding="utf-8")
    (src / "sub" / "e.mermaid").write_text("E", encoding="utf-8")
    (src / "skip.txt").write_text("S", encoding="utf-8")
    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["prog", "--src", str(src), "--out", str(out)])
    ed.main()
    assert (out / "a.md").read_text(encoding="utf-8") == "A"
    assert (out / "sub" / "d.MMD").read_text(encoding="utf-8") == "D"
    assert (out / "sub" / "e.mermaid").exists()
    assert not (out / "skip.txt").exists()
    assert capsys.readouterr().out.count("[COPY]") == 3


def test_export_docs_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])
    ed.main()
    assert (tmp_path / "out").is_dir()


# --------------------------------------------------------------------------
# ledger helpers
# --------------------------------------------------------------------------


def _make_db(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE runs (run_id TEXT, started_at TEXT, finished_at TEXT,"
        " status TEXT, git_sha TEXT, total_metrics_json TEXT)"
    )
    conn.executemany("INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?)", rows)
    conn.commit()
    conn.close()


_utf8_open = functools.partial(builtins.open, encoding="utf-8")

ROWS = [
    ("r1", "2026-01-01", "2026-01-02", "ok", "abc", json.dumps({"score_sigma": 4.5})),
    ("r2", "2026-01-03", None, "running", "def", "{broken"),
    ("r3", "2026-01-04", "2026-01-05", "ok", "ghi", None),
    ("r4", "2026-01-06", "2026-01-07", "ok", "jkl", "{}"),
]


# --------------------------------------------------------------------------
# export_summary_md
# --------------------------------------------------------------------------


@pytest.fixture
def summary_paths(tmp_path, monkeypatch):
    db = tmp_path / "ledger" / "runs.sqlite"
    out = tmp_path / "artifacts" / "markdown" / "summary.md"
    # The script opens its output with the locale encoding; pin UTF-8 so the
    # sigma glyph is writable on non-UTF-8 hosts (CI on Linux is UTF-8 anyway).
    monkeypatch.setattr(es, "open", _utf8_open, raising=False)
    monkeypatch.setattr(es, "DB_PATH", db)
    monkeypatch.setattr(es, "OUTPUT_PATH", out)
    return db, out


def test_summary_missing_db(summary_paths, capsys):
    db, out = summary_paths
    assert es.main() is None
    assert "Database not found" in capsys.readouterr().out
    assert not out.exists()


def test_summary_renders_runs(summary_paths, capsys):
    db, out = summary_paths
    _make_db(db, ROWS)
    es.main()
    text = out.read_text(encoding="utf-8")
    assert "Total runs: 4" in text
    assert "| `r1` | 2026-01-01 | ok | `abc` | σ=4.5 |" in text
    assert "| `r2` | 2026-01-03 | running | `def` | invalid metrics JSON |" in text
    assert "| `r3` | 2026-01-04 | ok | `ghi` |  |" in text
    assert "| `r4` | 2026-01-06 | ok | `jkl` | σ=N/A |" in text
    assert text.index("`r4`") < text.index("`r1`")
    printed = capsys.readouterr().out
    assert "failed to parse metrics JSON for run r2" in printed
    assert "Summary written to" in printed


# --------------------------------------------------------------------------
# make_ascii_timeline
# --------------------------------------------------------------------------


@pytest.fixture
def timeline_paths(tmp_path, monkeypatch):
    db = tmp_path / "ledger" / "runs.sqlite"
    out = tmp_path / "artifacts" / "ascii" / "timeline.txt"
    monkeypatch.setattr(at, "open", _utf8_open, raising=False)
    monkeypatch.setattr(at, "DB_PATH", db)
    monkeypatch.setattr(at, "OUTPUT_PATH", out)
    return db, out


def test_timeline_missing_db(timeline_paths, capsys):
    with pytest.raises(SystemExit) as exc:
        at.main()
    assert exc.value.code == 1
    assert "Database not found" in capsys.readouterr().err


def test_timeline_empty(timeline_paths, capsys):
    db, out = timeline_paths
    _make_db(db, [])
    at.main()
    assert out.read_text(encoding="utf-8") == "# DMAIC Timeline\n\nNo runs found.\n"
    assert "Timeline written" not in capsys.readouterr().out


def test_timeline_rows(timeline_paths, capsys):
    db, out = timeline_paths
    _make_db(db, ROWS)
    at.main()
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[2] == "- 2026-01-01 → 2026-01-02 | r1 | ok"
    assert lines[3] == "- ongoing | r2 | running"
    assert len(lines) == 6
    assert "Timeline written to" in capsys.readouterr().out
