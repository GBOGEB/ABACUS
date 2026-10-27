"""Behaviour tests for integration/gbogeb_session/governance/engines/SLIDE_ID_ENFORCER.py."""

import json
import sys

import pytest

from tests.coverage_waves.lane_a._load import load

se = load("integration/gbogeb_session/governance/engines/SLIDE_ID_ENFORCER.py")


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_finding_to_dict_and_str():
    f = se.EnforcerFinding("a.md", "x-y-1", True, "ok", 1)
    assert f.to_dict() == {
        "file": "a.md",
        "slide_id": "x-y-1",
        "valid": True,
        "message": "ok",
        "line": 1,
    }
    assert str(f) == "[VALID] a.md:1 — ok"
    g = se.EnforcerFinding("b.md", None, False, "bad")
    assert str(g) == "[INVALID] b.md — bad"


def test_results_summary_json_duplicates():
    res = se.EnforcerResults()
    assert res.passed
    assert "PASS" in res.summary()
    assert "Duplicates" not in res.summary()
    res.add(se.EnforcerFinding("a", "d-s-1", True, "ok"))
    res.add(se.EnforcerFinding("b", "d-s-1", True, "ok"))
    res.add(se.EnforcerFinding("c", None, False, "missing"))
    assert res.all_ids == ["d-s-1", "d-s-1"]
    assert len(res.violations) == 1
    assert not res.passed
    s = res.summary()
    assert "FAIL" in s
    assert "Duplicates: d-s-1" in s
    data = json.loads(res.to_json())
    assert data["duplicates"] == ["d-s-1"]
    assert data["violations"] == 1
    assert data["total"] == 3


@pytest.mark.parametrize(
    "sid, ok",
    [
        ("arch-overview-001", True),
        ("a-b-1", True),
        ("", False),
        ("arch-overview", False),
        ("arch-overview-x01", False),
        ("arch_overview-001", False),
    ],
)
def test_validate_slide_id(sid, ok):
    valid, msg = se.validate_slide_id(sid)
    assert valid is ok
    if not sid:
        assert msg == "Empty slide_id"
    elif not ok:
        assert "does not match pattern" in msg


def test_check_markdown_valid_invalid_missing(tmp_path):
    good = write(tmp_path / "g.md", "---\nslide_id: arch-overview-001\n---\n# T\n")
    res = se.check_markdown_file(str(good))
    assert len(res) == 1 and res[0].valid and res[0].line == 1
    bad = write(tmp_path / "b.md", "---\nslide_id: nope\n---\n")
    res = se.check_markdown_file(str(bad))
    assert not res[0].valid
    assert res[0].slide_id == "nope"
    none = write(tmp_path / "n.md", "---\ntitle: x\n---\n")
    res = se.check_markdown_file(str(none))
    assert res[0].slide_id is None and not res[0].valid
    assert "RULE-110" in res[0].message


def test_check_markdown_bad_yaml_and_non_dict(tmp_path):
    bad = write(tmp_path / "y.md", "---\nkey: [unclosed\n---\n")
    res = se.check_markdown_file(str(bad))
    assert len(res) == 1
    assert "Invalid YAML front matter" in res[0].message
    lst = write(tmp_path / "l.md", "---\n- a\n---\n")
    assert se.check_markdown_file(str(lst)) == []


def test_check_markdown_no_front_matter(tmp_path):
    slide = write(tmp_path / "slide_01.md", "# no front matter\n")
    res = se.check_markdown_file(str(slide))
    assert len(res) == 1
    assert res[0].line is None
    other = write(tmp_path / "readme.md", "# no front matter\n")
    assert se.check_markdown_file(str(other)) == []


def test_check_yaml_dict_with_slides(tmp_path):
    text = (
        "slide_id: deck-intro-001\n"
        "slides:\n"
        "  - slide_id: deck-body-002\n"
        "  - slide_id: bad\n"
        "  - title: no id\n"
        "  - just a string\n"
    )
    p = write(tmp_path / "deck.yaml", text)
    res = se.check_yaml_file(str(p))
    assert [f.slide_id for f in res] == ["deck-intro-001", "deck-body-002", "bad", None]
    assert [f.valid for f in res] == [True, True, False, False]
    assert "index 2" in res[3].message


def test_check_yaml_list_invalid_and_scalar(tmp_path):
    p = write(tmp_path / "l.yml", "- slide_id: a-b-1\n- plain\n- slides: nope\n")
    res = se.check_yaml_file(str(p))
    assert len(res) == 1 and res[0].valid
    bad = write(tmp_path / "bad.yaml", "key: [unclosed\n")
    assert se.check_yaml_file(str(bad)) == []
    scalar = write(tmp_path / "s.yaml", "just text\n")
    assert se.check_yaml_file(str(scalar)) == []


def test_check_lineage_manifest(tmp_path):
    assert se.check_lineage_manifest(str(tmp_path / "missing.json")) == []
    data = {
        "lineage": [
            {"slide_id": "a-b-1"},
            {"slide_id": "bad"},
            {"other": 1},
            {"slide_id": ""},
        ]
    }
    p = write(tmp_path / "lineage_manifest.json", json.dumps(data))
    res = se.check_lineage_manifest(str(p))
    assert [(f.slide_id, f.valid) for f in res] == [("a-b-1", True), ("bad", False)]
    empty = write(tmp_path / "e.json", "{}")
    assert se.check_lineage_manifest(str(empty)) == []


def test_enforce_directory_and_duplicates(tmp_path):
    root = tmp_path / "docs"
    write(root / "a.md", "---\nslide_id: d-s-1\n---\n")
    write(root / "sub" / "b.md", "---\nslide_id: d-s-1\n---\n")
    write(root / "c.yaml", "slide_id: d-s-2\n")
    write(
        root / "lineage_manifest.json", json.dumps({"lineage": [{"slide_id": "d-s-3"}]})
    )
    write(root / "other.json", json.dumps({"lineage": [{"slide_id": "bad"}]}))
    write(root / "node_modules" / "x.md", "---\nslide_id: bad\n---\n")
    write(root / "notes.txt", "slide_id: bad")
    res = se.enforce_directory(str(root))
    ids = [f.slide_id for f in res.findings]
    assert "bad" not in ids
    assert ids.count("d-s-1") == 3
    dup = [f for f in res.findings if "Duplicate" in f.message]
    assert len(dup) == 1
    assert not dup[0].valid
    assert "d-s-2" in ids and "d-s-3" in ids
    assert not res.passed


def test_production_defect_enforce_directory_skips_dotted_root(tmp_path, monkeypatch):
    """A root like '../docs' makes every file look hidden (path.parts, not rel)."""
    # production_defect (see WAVE_LEDGER.jsonl): this test pins the current
    # broken behaviour, so it fails once the defect is fixed. The repo's
    # test-evidence ratchet allows no xfails, hence no xfail marker.
    write(tmp_path / "docs" / "a.md", "---\nslide_id: d-s-1\n---\n")
    (tmp_path / "work").mkdir()
    monkeypatch.chdir(tmp_path / "work")
    res = se.enforce_directory("../docs")
    assert res.findings == []


def call_main(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["SLIDE_ID_ENFORCER.py", *args])
    return se.main()


def test_main_validate_text_and_json(monkeypatch, capsys):
    assert call_main(monkeypatch, "--validate", "arch-overview-001") == 0
    assert capsys.readouterr().out.startswith("VALID")
    assert call_main(monkeypatch, "--validate", "bad", "--format", "json") == 1
    data = json.loads(capsys.readouterr().out)
    assert data == {
        "slide_id": "bad",
        "valid": False,
        "message": se.validate_slide_id("bad")[1],
    }


def test_main_manifest(tmp_path, monkeypatch, capsys):
    p = write(tmp_path / "m.json", json.dumps({"lineage": [{"slide_id": "a-b-1"}]}))
    rc = call_main(monkeypatch, "--manifest", str(p), "--format", "json")
    data = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert data["passed"] is True
    assert data["total"] == 1


def test_main_paths_text(tmp_path, monkeypatch, capsys):
    d = tmp_path / "d"
    write(d / "a.md", "---\nslide_id: d-s-1\n---\n")
    md = write(tmp_path / "f.md", "---\nslide_id: bad\n---\n")
    ym = write(tmp_path / "f.yaml", "slide_id: d-s-9\n")
    lm = write(
        tmp_path / "m" / "lineage_manifest.json",
        json.dumps({"lineage": [{"slide_id": "m-n-7"}]}),
    )
    txt = write(tmp_path / "f.txt", "x")
    rc = call_main(
        monkeypatch,
        str(d),
        str(md),
        str(ym),
        str(lm),
        str(txt),
        str(tmp_path / "missing"),
    )
    out = capsys.readouterr().out
    assert rc == 1
    assert "[INVALID]" in out
    assert "d-s-9" in out
    assert "SLIDE ID ENFORCER: FAIL" in out


def test_main_requires_an_argument(monkeypatch, capsys):
    with pytest.raises(SystemExit):
        call_main(monkeypatch)
