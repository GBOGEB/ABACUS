"""Lane-B wave 12: qplant handover dashboard triage verifier.

verify_triage.ROOT is redirected to a tmp project tree. A "complete" tree is
synthesised from the module's own requirement tables so every search pattern,
key and required file is present.
"""

import json
import sys

import pytest

from ._l2_loader import load

vt = load("qplant/handover_dashboard/src/verify_triage.py")

BAD_FACTOR = "CONTRACTUAL_ALIGNMENT_FACTOR"


def _all_patterns():
    pats = set()
    for sec in vt.ADDENDUM_SECTIONS:
        for req in sec["requirements"]:
            if req.get("evidence_search"):
                pats.add(req["evidence_search"])
    for cat in vt.FEATURE_CATEGORIES.values():
        pats.update(cat.get("check_keys", []))
        pats.update(p for _, p in cat.get("check_patterns", []))
    return pats


def _all_files():
    files = set(vt.REQUIRED_FILES)
    for sec in vt.ADDENDUM_SECTIONS:
        for req in sec["requirements"]:
            files.update(req.get("evidence_files", []))
    for cat in vt.FEATURE_CATEGORIES.values():
        files.update(cat.get("check_files", []))
        if "check_file" in cat:
            files.add(cat["check_file"])
        files.update(f for f, _ in cat.get("check_patterns", []))
    return files


def _complete_tree(root):
    universal = "\n".join(sorted(_all_patterns()))
    clean = "\n".join(p for p in sorted(_all_patterns()) if p != BAD_FACTOR)
    for rel in _all_files():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        body = clean if rel == "src/calc_leak_rate.py" else universal
        p.write_text(body + "\n", encoding="utf-8")


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(vt, "ROOT", tmp_path)
    return tmp_path


def _req(logic, files=(), search=None, **extra):
    req = {
        "id": "R",
        "text": "t",
        "evidence_files": list(files),
        "evidence_search": search,
        "status_logic": logic,
    }
    req.update(extra)
    return req


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def test_sha256_file(root):
    p = root / "a.txt"
    p.write_bytes(b"abc")
    assert vt.sha256_file(p) == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_search_in_file_hits_missing_and_unreadable(root):
    p = root / "f.txt"
    p.write_text("Alpha\nbeta\nALPHA beta\n", encoding="utf-8")
    assert vt._search_in_file(p, "alpha") == (True, [1, 3])
    assert vt._search_in_file(p, "gamma") == (False, [])
    assert vt._search_in_file(root / "nope.txt", "x") == (False, [])
    d = root / "adir"
    d.mkdir()
    assert vt._search_in_file(d, "x") == (False, [])


# --------------------------------------------------------------------------
# verify_requirement
# --------------------------------------------------------------------------


def test_requirement_not_in_scope_note_and_default():
    res = vt.verify_requirement(_req("not_in_scope", note="elsewhere"))
    assert (res["status"], res["completion_pct"], res["verification"]) == (
        "NOT_IN_SCOPE",
        100,
        "N/A",
    )
    assert res["evidence"] == [{"note": "elsewhere"}]
    res = vt.verify_requirement(_req("not_in_scope"))
    assert res["evidence"] == [{"note": "Outside dashboard scope"}]


def test_requirement_file_exists_pass(root):
    (root / "x.csv").write_text("a", encoding="utf-8")
    res = vt.verify_requirement(_req("file_exists", ["x.csv"]))
    assert res["status"] == "COMPLETE" and res["verification"] == "PASS"
    assert res["evidence"][0]["file"] == "x.csv"
    assert res["evidence"][0]["size_bytes"] == 1


@pytest.mark.parametrize(
    "files, gap", [(["missing.csv"], "File missing: missing.csv"), ([], "unknown")]
)
def test_requirement_file_exists_gap(root, files, gap):
    res = vt.verify_requirement(_req("file_exists", files))
    assert res["status"] == "GAP"
    assert res["gaps"] == [gap if files else "File missing: unknown"]


def test_requirement_default_logic_is_file_exists(root):
    req = _req("file_exists", ["m.txt"])
    del req["status_logic"]
    assert vt.verify_requirement(req)["status"] == "GAP"


@pytest.mark.parametrize(
    "present, status, pct, verdict",
    [
        (["a", "b"], "COMPLETE", 100, "PASS"),
        (["a"], "PARTIAL", 50, "FAIL"),
        ([], "GAP", 0, "FAIL"),
    ],
)
def test_requirement_all_files_exist(root, present, status, pct, verdict):
    for name in present:
        (root / name).write_text(name, encoding="utf-8")
    res = vt.verify_requirement(_req("all_files_exist", ["a", "b"]))
    assert (res["status"], res["completion_pct"], res["verification"]) == (
        status,
        pct,
        verdict,
    )
    assert len(res["evidence"]) == len(present)
    assert len(res["gaps"]) == 2 - len(present)


def test_requirement_all_files_exist_empty_list(root):
    res = vt.verify_requirement(_req("all_files_exist", []))
    assert res["status"] == "GAP" and res["completion_pct"] == 0


def test_requirement_search(root):
    (root / "a.txt").write_text("x\nNeedle here\n", encoding="utf-8")
    res = vt.verify_requirement(_req("search", ["missing.txt", "a.txt"], "needle"))
    assert res["status"] == "COMPLETE"
    assert res["evidence"] == [
        {
            "file": "a.txt",
            "pattern": "needle",
            "matching_lines": [2],
            "sha256": vt.sha256_file(root / "a.txt"),
        }
    ]


def test_requirement_search_gap_and_no_pattern(root):
    res = vt.verify_requirement(_req("search", ["a.txt"], "needle"))
    assert res["status"] == "GAP"
    assert res["gaps"] == ["Pattern 'needle' not found in ['a.txt']"]
    res = vt.verify_requirement(_req("search", ["a.txt"], None))
    assert res["gaps"] == ["No search pattern defined"]


def test_requirement_search_hit_on_vanished_file(root, monkeypatch):
    monkeypatch.setattr(vt, "_search_in_file", lambda p, pat: (True, [1]))
    res = vt.verify_requirement(_req("search", ["ghost.txt"], "x"))
    assert res["evidence"][0]["sha256"] is None


def test_requirement_absent(root):
    (root / "ok.py").write_text("clean", encoding="utf-8")
    res = vt.verify_requirement(_req("absent", ["ok.py"], "BAD"))
    assert res["status"] == "COMPLETE"
    assert res["evidence"] == [{"note": "Pattern 'BAD' correctly absent"}]
    (root / "bad.py").write_text("a\nBAD = 1\n", encoding="utf-8")
    res = vt.verify_requirement(_req("absent", ["ok.py", "bad.py"], "BAD"))
    assert res["status"] == "GAP"
    assert res["gaps"] == ["Pattern 'BAD' still present in bad.py at lines [2]"]


def test_requirement_unknown_logic_stays_not_started():
    res = vt.verify_requirement(_req("mystery"))
    assert res["status"] == "NOT_STARTED" and res["verification"] == "FAIL"


# --------------------------------------------------------------------------
# inventory / features
# --------------------------------------------------------------------------


def test_file_inventory(root, monkeypatch):
    monkeypatch.setattr(vt, "REQUIRED_FILES", ["here.txt", "gone.txt"])
    (root / "here.txt").write_text("hi", encoding="utf-8")
    here, gone = vt.verify_file_inventory()
    assert here["status"] == "OK" and here["size_bytes"] == 2
    assert here["last_modified"].endswith("+00:00")
    assert gone == {
        "required_file": "gone.txt",
        "exists": False,
        "size_bytes": None,
        "sha256": None,
        "last_modified": None,
        "status": "MISSING",
    }


def test_features_all_kinds(root, monkeypatch):
    monkeypatch.setattr(
        vt,
        "FEATURE_CATEGORIES",
        {
            "Files": {"required": ["A", "B"], "check_files": ["a.txt", "b.txt"]},
            "Keys": {
                "required": ["K1", "K2"],
                "check_file": "k.json",
                "check_keys": ["one", "two"],
            },
            "KeysMissingFile": {
                "required": ["Z"],
                "check_file": "nope.json",
                "check_keys": ["z"],
            },
            "Patterns": {
                "required": ["P1", "P2"],
                "check_patterns": [("a.txt", "hello"), ("a.txt", "absent")],
            },
            "Unchecked": {"required": ["U"]},
        },
    )
    (root / "a.txt").write_text("HELLO", encoding="utf-8")
    (root / "k.json").write_text('{"ONE": 1}', encoding="utf-8")
    res = {r["category"]: r for r in vt.verify_features()}
    assert res["Files"]["implemented_list"] == ["A"] and res["Files"]["missing"] == [
        "B"
    ]
    assert res["Keys"]["implemented_list"] == ["K1"] and res["Keys"]["missing"] == [
        "K2"
    ]
    assert res["KeysMissingFile"]["missing"] == ["Z"]
    assert res["Patterns"]["completion_pct"] == 50
    assert res["Unchecked"] == {
        "category": "Unchecked",
        "total_required": 1,
        "implemented": 0,
        "implemented_list": [],
        "completion_pct": 0,
        "missing": [],
    }


# --------------------------------------------------------------------------
# run_verification
# --------------------------------------------------------------------------


def test_run_verification_complete_tree(root):
    _complete_tree(root)
    report = vt.run_verification()
    es = report["executive_summary"]
    assert es["overall_status"] == "COMPLETE"
    assert es["overall_completion_pct"] == 100
    assert es["file_coverage_pct"] == 100
    assert es["feature_coverage_pct"] == 100
    assert es["compliance_score"] == 10.0
    assert es["requirements_not_in_scope"] == 2
    assert es["requirements_gap"] == 0
    assert report["project_root"] == str(root)


def test_run_verification_empty_tree(root):
    report = vt.run_verification()
    es = report["executive_summary"]
    assert es["overall_status"] == "INSUFFICIENT"
    assert es["files_found"] == 0
    # Only the "absent" check (REQ-04.2) passes when its file does not exist.
    assert es["requirements_met"] == 1
    assert es["requirements_gap"] == es["in_scope_requirements"] - 1


@pytest.mark.parametrize(
    "present, inventory, status, partial",
    [
        (4, ["f0"], "COMPLETE", 0),
        (4, ["missing"], "SUBSTANTIAL", 0),
        (3, ["f0"], "SUBSTANTIAL", 0),
        (2, ["f0"], "PARTIAL", 1),
        (1, ["f0"], "INSUFFICIENT", 1),
    ],
)
def test_run_verification_status_bands(
    root, monkeypatch, present, inventory, status, partial
):
    reqs = [_req("file_exists", [f"f{i}"]) for i in range(3)]
    reqs.append(_req("all_files_exist", ["f3", "g3"] if partial else ["f3"]))
    reqs.append(_req("not_in_scope"))
    monkeypatch.setattr(
        vt, "ADDENDUM_SECTIONS", [{"id": "S", "title": "T", "requirements": reqs}]
    )
    monkeypatch.setattr(vt, "REQUIRED_FILES", inventory)
    monkeypatch.setattr(vt, "FEATURE_CATEGORIES", {})
    names = [f"f{i}" for i in range(4)]
    if partial:
        names = names[:3][:present] + ["f3"]
    else:
        names = names[:present]
    for n in names:
        (root / n).write_text(n, encoding="utf-8")
    es = vt.run_verification()["executive_summary"]
    assert es["overall_status"] == status
    assert es["requirements_partial"] == partial
    assert es["requirements_not_in_scope"] == 1
    assert es["features_required"] == 0 and es["feature_coverage_pct"] == 0


# --------------------------------------------------------------------------
# generators
# --------------------------------------------------------------------------


def _crafted_report(sha=None):
    return {
        "verification_timestamp": "2026-01-01T00:00:00+00:00",
        "project_root": "/proj",
        "executive_summary": {
            "total_requirements": 3,
            "requirements_met": 1,
            "requirements_partial": 1,
            "requirements_gap": 0,
            "requirements_not_in_scope": 1,
            "in_scope_requirements": 2,
            "overall_completion_pct": 50,
            "files_required": 2,
            "files_found": 1,
            "file_coverage_pct": 50,
            "features_required": 2,
            "features_implemented": 1,
            "feature_coverage_pct": 50,
            "compliance_score": 5.0,
            "overall_status": "WEIRD",
        },
        "section_analysis": [
            {
                "id": "S1",
                "title": "Sec",
                "requirements": [
                    {
                        "id": "R1",
                        "text": "search req",
                        "status": "COMPLETE",
                        "completion_pct": 100,
                        "verification": "PASS",
                        "evidence": [
                            {"file": "a.py", "matching_lines": [3, 4]},
                            {"file": "b.bin", "size_bytes": 7, "sha256": "f" * 64},
                            {"file": "c.txt"},
                            {"other": 1},
                        ],
                        "gaps": [],
                    },
                    {
                        "id": "R2",
                        "text": "partial req",
                        "status": "PARTIAL",
                        "completion_pct": 50,
                        "verification": "FAIL",
                        "evidence": [{"file": "d.txt", "matching_lines": []}],
                        "gaps": ["Missing: e.txt"],
                    },
                    {
                        "id": "R3",
                        "text": "nis",
                        "status": "NOT_IN_SCOPE",
                        "completion_pct": 100,
                        "verification": "N/A",
                        "evidence": [{"note": "outside"}],
                        "gaps": [],
                    },
                    {
                        "id": "R4",
                        "text": "odd",
                        "status": "ODD",
                        "completion_pct": 0,
                        "verification": "FAIL",
                        "evidence": [],
                        "gaps": [],
                    },
                ],
            }
        ],
        "file_inventory": [
            {
                "required_file": "a.py",
                "exists": True,
                "size_bytes": 10,
                "sha256": "a" * 64,
                "last_modified": "T",
                "status": "OK",
            },
            {
                "required_file": "z.py",
                "exists": False,
                "size_bytes": None,
                "sha256": sha,
                "last_modified": None,
                "status": "MISSING",
            },
        ],
        "feature_matrix": [
            {
                "category": "C1",
                "total_required": 2,
                "implemented": 1,
                "completion_pct": 50,
                "missing": ["X", "Y"],
            },
            {
                "category": "C2",
                "total_required": 1,
                "implemented": 1,
                "completion_pct": 100,
                "missing": [],
            },
        ],
    }


def test_generate_markdown_sections():
    md = vt.generate_markdown(_crafted_report())
    assert md.startswith("# TRIAGE ADDENDUM GAP ANALYSIS")
    assert "| **Overall Status** | **WEIRD** |" in md
    assert "- **Status:** ✅ COMPLETE (100%)" in md
    assert "- **Status:** 🟡 PARTIAL (50%)" in md
    assert "- **Status:** ⬜ NOT_IN_SCOPE (100%)" in md
    assert "- **Status:** ❓ ODD (0%)" in md
    assert "  - `a.py` (lines: [3, 4])" in md
    assert "  - `b.bin` (7 bytes, sha256: `ffffffffffffffff...`)" in md
    assert "  - `c.txt` \n" in md
    assert "  - outside" in md
    assert "  - Missing: e.txt" in md
    assert "| `a.py` | YES | 10 | `aaaaaaaaaaaaaaaa...` | ✅ |" in md
    assert "| `z.py` | NO | — | — | ❌ |" in md
    assert "| C1 | 2 | 1 | 50% | X, Y |" in md
    assert "| C2 | 1 | 1 | 100% | None |" in md
    assert "| R1 | `a.py` | 3, 4 | PASS |" in md
    assert "| R1 | `b.bin` | 7 bytes | PASS |" in md
    assert "| R2 | `d.txt` | — bytes | FAIL |" in md
    assert "| R3 | — | outside | N/A |" in md
    assert md.endswith("## Overall Compliance Score: 5.0/10.0\n")


def test_generate_html_with_hashes():
    html = vt.generate_html(_crafted_report(sha="b" * 64))
    assert "background:#95a5a6" in html
    assert "<code>a.py</code> <code>b.bin</code> <code>c.txt</code>" in html
    assert "<em>outside</em>" in html
    assert '<span class="gap-item">Missing: e.txt</span>' in html
    assert 'class="req-row not-in-scope"' in html
    assert "50% (2/4)" in html
    assert '<tr class="missing">' in html
    assert "<td>—</td>" in html
    assert "<td>X, Y</td>" in html and "<td>None</td>" in html


def test_generate_html_missing_file_crashes():
    """production_defect: generate_html slices f["sha256"][:16] without a None
    guard, so any report with a missing required file raises TypeError (and
    ``--all`` aborts); this test fails once fixed."""
    with pytest.raises(TypeError, match="not subscriptable"):
        vt.generate_html(_crafted_report(sha=None))


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------


def test_main_plain_fails_on_empty_tree(root, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["verify_triage.py"])
    assert vt.main() == 1
    out = capsys.readouterr().out
    assert '"overall_status": "INSUFFICIENT"' in out
    assert "FAIL: 2% compliance (INSUFFICIENT)" in out
    assert not (root / "TRIAGE_GAP_ANALYSIS.md").exists()


def test_main_md_only(root, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["verify_triage.py", "--md"])
    assert vt.main() == 1
    assert (root / "TRIAGE_GAP_ANALYSIS.md").exists()
    assert not (root / "TRIAGE_COMPLIANCE_REPORT.json").exists()
    assert "Written: TRIAGE_GAP_ANALYSIS.md" in capsys.readouterr().out


def test_main_all_on_complete_tree(root, monkeypatch, capsys):
    _complete_tree(root)
    monkeypatch.setattr(sys, "argv", ["verify_triage.py", "--all"])
    assert vt.main() == 0
    out = capsys.readouterr().out
    assert "PASS: 100% compliance (COMPLETE)" in out
    report = json.loads(
        (root / "TRIAGE_COMPLIANCE_REPORT.json").read_text(encoding="utf-8")
    )
    assert report["executive_summary"]["overall_status"] == "COMPLETE"
    assert (
        (root / "TRIAGE_GAP_ANALYSIS.md")
        .read_text(encoding="utf-8")
        .startswith("# TRIAGE ADDENDUM GAP ANALYSIS")
    )
    html = (root / "docs" / "triage_compliance.html").read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html or "<!doctype html>" in html.lower()
