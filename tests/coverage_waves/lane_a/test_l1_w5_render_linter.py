"""Behaviour tests for integration/gbogeb_session/governance/engines/RENDER_LINTER.py."""

import json
import sys

from tests.coverage_waves.lane_a._load import load

rl = load("integration/gbogeb_session/governance/engines/RENDER_LINTER.py")

FRONT_OK = (
    "---\n"
    "slide_id: arch-overview-001\n"
    "purpose: explain\n"
    "audience: engineers\n"
    "speaker_notes: " + "".join("n" for _ in range(60)) + "\n"
    "---\n"
    "# Title\n"
)


def run(rule, content, filepath="deck.md"):
    results = rl.LintResults()
    rl.RULES[rule](content, filepath, results)
    return results


def test_finding_to_dict_and_str():
    f = rl.LintFinding("r", rl.Severity.ERROR, "a.md", 3, "msg", "ctx")
    d = f.to_dict()
    assert d["severity"] == "ERROR"
    assert d["line"] == 3
    assert d["context"] == "ctx"
    assert str(f) == "[ERROR] a.md:3 — r: msg"
    g = rl.LintFinding("r", rl.Severity.INFO, "a.md", None, "m")
    assert str(g) == "[INFO] a.md — r: m"


def test_results_properties_summary_json():
    res = rl.LintResults()
    assert res.passed
    assert "PASS" in res.summary()
    res.add(rl.LintFinding("a", rl.Severity.ERROR, "f", 1, "e"))
    res.add(rl.LintFinding("b", rl.Severity.WARNING, "f", 2, "w"))
    res.add(rl.LintFinding("c", rl.Severity.INFO, "f", None, "i"))
    assert len(res.errors) == 1
    assert len(res.warnings) == 1
    assert not res.passed
    s = res.summary()
    assert "FAIL" in s
    assert "Info:     1" in s
    data = json.loads(res.to_json())
    assert data["passed"] is False
    assert data["total"] == 3
    assert data["errors"] == 1
    assert data["warnings"] == 1
    assert len(data["findings"]) == 3


def test_no_overflow_long_line_and_hidden():
    content = "".join("x" for _ in range(201)) + "\nshort\ndiv { overflow : HIDDEN; }"
    res = run("no_overflow", content)
    sev = [(f.line, f.severity) for f in res.findings]
    assert (1, rl.Severity.WARNING) in sev
    assert (3, rl.Severity.ERROR) in sev
    assert len(res.findings) == 2
    assert res.findings[0].context.endswith("...")


def test_no_overflow_clean():
    assert run("no_overflow", "fine\nlines").findings == []


def test_orphan_bullets_unordered_and_ordered():
    content = "\n".join(
        [
            "- only one",
            "",
            "* a",
            "+ b",
            "",
            "1. single",
            "",
            "1. one",
            "2. two",
            "text",
        ]
    )
    res = run("no_orphan_bullets", content)
    lines = sorted(f.line for f in res.findings)
    assert lines == [1, 6]
    msgs = " ".join(f.message for f in res.findings)
    assert "Orphan bullet" in msgs
    assert "Orphan numbered" in msgs


def test_heading_skip_and_multiple_h1_md():
    content = "# A\n### C\n## B\n# D\nnot#heading"
    res = run("stable_heading_hierarchy", content, "x.md")
    errs = [f for f in res.findings if f.severity == rl.Severity.ERROR]
    infos = [f for f in res.findings if f.severity == rl.Severity.INFO]
    assert len(errs) == 1
    assert errs[0].line == 2
    assert "H1" in errs[0].message and "H3" in errs[0].message
    assert len(infos) == 1
    assert "(2)" in infos[0].message


def test_heading_multiple_h1_non_md_no_info():
    res = run("stable_heading_hierarchy", "# A\n## B\n# C", "x.html")
    assert res.findings == []


def test_figure_reference_rules():
    content = (
        'fig-id="arch"\n'
        "![flow](flow.png)\n"
        "![](blank.png)\n"
        "See Figure arch and Fig. missing and Figure 3.\n"
    )
    res = run("figure_reference_required", content)
    warn = {f.message for f in res.findings if f.severity == rl.Severity.WARNING}
    err = {f.message for f in res.findings if f.severity == rl.Severity.ERROR}
    assert any("'flow'" in m for m in warn)
    assert not any("'arch'" in m for m in warn)
    assert len(warn) == 1
    assert len(err) == 1
    assert "'missing'" in next(iter(err))


def test_speaker_notes_front_matter_short_and_ok():
    short = "---\nspeaker_notes: hi\n---\nbody"
    res = run("speaker_notes_required", short)
    assert len(res.findings) == 1
    assert "(2 chars" in res.findings[0].message
    missing = "---\ntitle: x\n---\nbody"
    res = run("speaker_notes_required", missing)
    assert "(0 chars" in res.findings[0].message
    assert run("speaker_notes_required", FRONT_OK).findings == []


def test_speaker_notes_comment_and_fallbacks():
    with_comment = "# T\n<!-- speaker_notes: talk about it -->\n"
    assert run("speaker_notes_required", with_comment, "slide1.md").findings == []
    res = run("speaker_notes_required", "# T\n", "my_slide.md")
    assert len(res.findings) == 1
    assert res.findings[0].line is None
    assert run("speaker_notes_required", "# T\n", "notes.md").findings == []
    assert run("speaker_notes_required", "# T\n", "slide.html").findings == []
    # invalid YAML front matter falls through to comment search
    bad = "---\nkey: [unclosed\n---\n"
    assert len(run("speaker_notes_required", bad, "slide.md").findings) == 1
    # non-dict front matter falls through as well
    lst = "---\n- a\n- b\n---\n<!-- speaker-notes: x -->"
    assert run("speaker_notes_required", lst, "slide.md").findings == []


def test_semantic_card_rules():
    assert run("semantic_card_required", FRONT_OK, "slide.md").findings == []
    partial = "---\nslide_id: a-b-1\n---\n"
    res = run("semantic_card_required", partial, "slide.md")
    assert len(res.findings) == 1
    assert "purpose, audience" in res.findings[0].message
    res = run("semantic_card_required", "# none", "slide.md")
    assert res.findings[0].line is None
    assert run("semantic_card_required", "# none", "readme.md").findings == []
    bad = "---\nkey: [unclosed\n---\n"
    assert len(run("semantic_card_required", bad, "slide.md").findings) == 1
    lst = "---\n- a\n---\n"
    assert run("semantic_card_required", lst, "other.html").findings == []


def test_low_contrast():
    content = "p { color: #777; background-color: rgb(255,255,255); }\ncolor: #000\n"
    res = run("no_low_contrast", content)
    assert len(res.findings) == 1
    assert res.findings[0].line == 1
    assert res.findings[0].severity == rl.Severity.INFO


def test_lint_file_missing(tmp_path):
    res = rl.lint_file(str(tmp_path / "nope.md"))
    assert res.findings[0].rule == "file_access"
    assert not res.passed


def test_lint_file_unlintable_suffix(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("- orphan\n", encoding="utf-8")
    assert rl.lint_file(str(p)).findings == []


def test_lint_file_decode_error(tmp_path):
    p = tmp_path / "bad.md"
    p.write_bytes(b"\xff\xfe\xfa bad")
    res = rl.lint_file(str(p))
    assert res.findings[0].rule == "file_access"
    assert "Cannot read file" in res.findings[0].message


def test_lint_file_all_and_selected_rules(tmp_path):
    p = tmp_path / "slide_one.md"
    p.write_text("- orphan\n# A\n### C\n", encoding="utf-8")
    res = rl.lint_file(str(p))
    rules = {f.rule for f in res.findings}
    assert {"no_orphan_bullets", "stable_heading_hierarchy"} <= rules
    assert "semantic_card_required" in rules
    res = rl.lint_file(str(p), ["no_orphan_bullets", "unknown_rule"])
    assert {f.rule for f in res.findings} == {"no_orphan_bullets"}


def test_lint_directory(tmp_path):
    root = tmp_path / "docs"
    (root / "sub").mkdir(parents=True)
    (root / "node_modules").mkdir()
    (root / "sub" / "a.md").write_text("- orphan\n", encoding="utf-8")
    (root / "node_modules" / "b.md").write_text("- orphan\n", encoding="utf-8")
    (root / "c.txt").write_text("- orphan\n", encoding="utf-8")
    res = rl.lint_directory(str(root), ["no_orphan_bullets"])
    assert len(res.findings) == 1
    assert res.findings[0].file.endswith("a.md")


def test_lint_directory_missing(tmp_path):
    res = rl.lint_directory(str(tmp_path / "missing"))
    assert res.findings[0].rule == "directory_access"


def check_production_defect_lint_directory_skips_dotted_root(tmp_path, monkeypatch):
    """A root like '../docs' makes every file look hidden (path.parts, not rel)."""
    # Reproduction of a production_defect (see WAVE_LEDGER.jsonl). Named check_*
    # so the governed suite does not collect it: a pinned defect must never block
    # the fix. Run on demand: pytest -o python_functions=check_* <this file>
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.md").write_text("- orphan\n", encoding="utf-8")
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    res = rl.lint_directory("../docs", ["no_orphan_bullets"])
    assert res.findings == []


def call_main(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["RENDER_LINTER.py", *args])
    return rl.main()


def test_main_text_dir_file_and_missing(tmp_path, monkeypatch, capsys):
    d = tmp_path / "d"
    d.mkdir()
    (d / "x.md").write_text("ok\n", encoding="utf-8")
    f = tmp_path / "y.md"
    f.write_text("fine\n", encoding="utf-8")
    rc = call_main(
        monkeypatch,
        "--rules",
        "no_orphan_bullets",
        str(d),
        str(f),
        str(tmp_path / "zzz"),
    )
    out = capsys.readouterr().out
    assert rc == 1
    assert "path_access" in out
    assert "FAIL" in out


def test_main_json_pass(tmp_path, monkeypatch, capsys):
    f = tmp_path / "y.md"
    f.write_text("- a\n- b\n", encoding="utf-8")
    rc = call_main(
        monkeypatch, "--format", "json", "--rules", "no_orphan_bullets", str(f)
    )
    data = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert data["passed"] is True


def test_main_strict_promotes_warnings(tmp_path, monkeypatch, capsys):
    f = tmp_path / "y.md"
    f.write_text("- only\n", encoding="utf-8")
    assert call_main(monkeypatch, "--rules", "no_orphan_bullets", str(f)) == 0
    capsys.readouterr()
    rc = call_main(
        monkeypatch,
        "--strict",
        "--format",
        "json",
        "--rules",
        "no_orphan_bullets",
        str(f),
    )
    data = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert data["findings"][0]["severity"] == "ERROR"
