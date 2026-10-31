"""Behaviour tests for the improved QPLANT RTM generator (I/O redirected)."""

import builtins
import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load(
    "rtm_integration/automation/scripts/automation/improved_rtm_generator.py",
    name="abn_w6_improved_rtm_generator",
)

PDF_PATH = "/home/ubuntu/Uploads/cryoplant_requirements.pdf"
REAL_OPEN = builtins.open


@pytest.fixture
def gen():
    return mod.ImprovedCryoplantRTMGenerator()


@pytest.fixture
def redirect(monkeypatch, tmp_path):
    """Serve the hard-coded PDF from memory and send /home/ubuntu writes to tmp."""

    def fake_open(path, mode="r", *args, **kwargs):
        text = str(path)
        if text == PDF_PATH:
            return io.StringIO("pdf text")
        if text.startswith("/home/ubuntu/"):
            path = tmp_path / Path(text).name
        return REAL_OPEN(path, mode, *args, **kwargs)

    monkeypatch.setattr(mod, "open", fake_open, raising=False)
    return tmp_path


@pytest.fixture
def fake_excel(monkeypatch):
    """Replace pandas Excel output and global display options with recorders."""
    record = SimpleNamespace(options=[], sheets={}, paths=[])

    class FakeWriter:
        def __init__(self, path, engine=None):
            record.paths.append((path, engine))

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_to_excel(frame, writer, sheet_name="Sheet1", index=True):
        record.sheets[sheet_name] = frame

    proxy = SimpleNamespace(
        DataFrame=mod.pd.DataFrame,
        ExcelWriter=FakeWriter,
        set_option=lambda *a: record.options.append(a),
    )
    monkeypatch.setattr(mod, "pd", proxy)
    monkeypatch.setattr(mod.pd.DataFrame, "to_excel", fake_to_excel)
    return record


def _req(req_id, **kw):
    base = {
        "req_id": req_id,
        "description": "desc " + req_id,
        "full_description": "desc " + req_id,
        "sbs_l0": "QSYS",
        "sbs_l1": "QPLANT",
        "sbs_l2": "WCS",
        "sbs_l3": "",
        "requirement_type": "Functional",
        "verification_method": "Test",
        "acceptance_criteria": "ok",
        "priority": "Medium",
        "source_section": "1",
        "parent_requirements": [],
        "child_requirements": [],
        "status": "Active",
        "rationale": "why",
    }
    base.update(kw)
    return base


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("overall wcs piping", ("QSYS-PR", "QPLANT", "WCS", "PVPS")),
        ("warm compressor hp unit", ("QSYS", "QPLANT", "WCS", "HP")),
        ("header plumbing", ("QSYS", "QDIST", "", "")),
        ("cryomodule in cold box with turbine", ("QSYS", "QCELL", "QRB", "TURBINES")),
        ("utility refrigeration at 4.5k", ("QSYS", "QINFRA", "QRB", "BATH-4K")),
        ("refrigeration 2k bath", ("QSYS", "QPLANT", "QRB", "BATH-2K")),
        ("qrb cc stage", ("QSYS", "QPLANT", "QRB", "CC")),
        ("qrb plain", ("QSYS", "QPLANT", "QRB", "")),
        ("plain words", ("QSYS", "QPLANT", "WCS", "")),
    ],
)
def test_assign_to_sbs(gen, text, expected):
    res = gen._assign_to_sbs("RTM-X", text)
    assert (res["l0"], res["l1"], res["l2"], res["l3"]) == expected


@pytest.mark.parametrize(
    ("text", "method"),
    [
        ("acceptance test", "Test"),
        ("by calculation", "Analysis"),
        ("document review", "Inspection"),
        ("functional demo", "Demonstration"),
        ("xyz", "Test"),
    ],
)
def test_verification_method(gen, text, method):
    assert gen._determine_verification_method(text) == method


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("high flow", "Performance"),
        ("purge it", "Safety"),
        ("interface spec", "Interface"),
        ("control mode", "Functional"),
        ("material choice", "Design"),
        ("xyz", "Functional"),
    ],
)
def test_requirement_type(gen, text, kind):
    assert gen._determine_requirement_type(text) == kind


@pytest.mark.parametrize(
    ("text", "prio"),
    [("it shall", "High"), ("it should", "Medium"), ("xyz", "High")],
)
def test_priority(gen, text, prio):
    assert gen._determine_priority(text) == prio


@pytest.mark.parametrize(
    ("text", "needle"),
    [
        ("purge line", "safe operation"),
        ("capacity", "performance targets"),
        ("lifetime", "project lifetime"),
        ("scenario a", "operational flexibility"),
        ("xyz", "system functionality"),
    ],
)
def test_rationale(gen, text, needle):
    assert needle in gen._generate_rationale(text)


def test_acceptance_criteria_units_and_limit(gen):
    res = gen._generate_acceptance_criteria("at 4.5k and 3 kw and 7 bar and 9 mw")
    assert (
        res == "Temperature condition: 4.5K; Value shall meet 3 kw; Value shall meet 7 "
    )
    assert gen._generate_acceptance_criteria("no numbers") == (
        "Compliance with requirement as specified"
    )


def test_production_defect_acceptance_criteria_unit_regex_never_matches_days(gen):
    """production_defect: acceptance-criteria unit regex matches an empty unit before days/years/cycles/%; this test fails once fixed"""
    res = gen._generate_acceptance_criteria("run 90 days, 50% load, 20 years")
    assert "Duration" not in res
    assert "Lifetime" not in res
    assert "Performance" not in res
    assert res.startswith("Value shall meet 90 ;")


def test_extract_requirements(gen, redirect):
    reqs = gen.extract_requirements_from_pdf_text()
    assert len(reqs) == 16
    first = reqs[0]
    assert first["req_id"] == "RTM-01"
    assert first["status"] == "Active"
    assert first["category"] == "Operational"
    assert first["sbs_l1"] in gen.sbs_structure
    assert {r["category"] for r in reqs} >= {"Maintenance", "Lifetime", "Safety"}


def test_parent_child_relationships(gen):
    reqs = [_req(i) for i in ("RTM-01", "RTM-03", "RTM-05", "RTM-06", "RTM-012")]
    reqs.append(_req("OTHER"))
    out = gen.establish_parent_child_relationships(reqs)
    by_id = {r["req_id"]: r for r in out}
    assert by_id["RTM-01"]["child_requirements"] == ["RTM-02", "RTM-03", "RTM-04"]
    assert by_id["RTM-03"]["parent_requirements"] == ["RTM-01"]
    assert by_id["RTM-012"]["parent_requirements"] == ["RTM-06"]
    assert by_id["RTM-05"]["parent_requirements"] == []
    assert by_id["OTHER"]["parent_requirements"] == []


def test_dataframes(gen):
    reqs = [
        _req("A", parent_requirements=["P"], category="Safety"),
        _req("B", child_requirements=["C", "D"], numerical_value="5 bar"),
    ]
    df = gen.create_rtm_dataframe(reqs)
    assert list(df["Category"]) == ["Safety", "General"]
    assert list(df["Numerical Value"]) == ["N/A", "5 bar"]
    assert list(df["Child Requirements"]) == ["", "C, D"]
    sbs = gen.create_sbs_dataframe()
    assert len(sbs) == len(gen.sbs_structure)
    row = sbs[sbs["SBS ID"] == "QSYS"].iloc[0]
    assert row["Parent"] == ""
    assert row["Children"] == "QSYS-PR"


def test_generate_rtm_excel(gen, fake_excel, capsys):
    reqs = [
        _req("A", priority="High", requirement_type="Safety", category="Operational"),
        _req("B", requirement_type="Performance", verification_method="Analysis"),
    ]
    out = gen.generate_rtm_excel(reqs, "rtm.xlsx")
    assert out == "rtm.xlsx"
    assert fake_excel.paths == [("rtm.xlsx", "openpyxl")]
    assert set(fake_excel.sheets) == {
        "Navigation",
        "RTM",
        "SBS",
        "Summary",
        "BySystem",
        "ByType",
    }
    summary = fake_excel.sheets["Summary"].set_index("Metric")["Count"]
    assert summary["Total Requirements"] == 2
    assert summary["High Priority Requirements"] == 1
    assert summary["Requirements Needing Analysis Verification"] == 1
    assert len(fake_excel.options) == 3
    assert "RTM Excel workbook created: rtm.xlsx" in capsys.readouterr().out


def test_generate_rtm_excel_empty(gen, fake_excel):
    gen.generate_rtm_excel([], "empty.xlsx")
    assert "BySystem" not in fake_excel.sheets
    assert fake_excel.sheets["Summary"]["Count"].sum() == 0


def test_create_markdown_document(gen, tmp_path, capsys):
    reqs = [
        _req(
            "A",
            sbs_l3="PVPS",
            priority="High",
            requirement_type="Safety",
            parent_requirements=["P1"],
            category="Safety",
        ),
        _req("B", child_requirements=["C1", "C2"], sbs_l1="QDIST"),
        _req("C", sbs_l1="QDIST", priority="High"),
    ]
    out = tmp_path / "rtm.md"
    assert gen.create_markdown_document(reqs, str(out)) == str(out)
    text = out.read_text(encoding="utf-8")
    assert "**Total Requirements:** 3" in text
    assert "### Safety Requirements" in text
    assert "### General Requirements" in text
    assert "QSYS → QPLANT → WCS → PVPS" in text
    assert "**Parent Requirements:** P1" in text
    assert "**Child Requirements:** C1, C2" in text
    assert "| QPLANT | 1 | 1 | 1 |" in text
    assert "| QDIST | 2 | 1 | 0 |" in text
    assert "Markdown document created" in capsys.readouterr().out


def test_main_end_to_end(redirect, fake_excel, capsys):
    reqs, excel_path, md_path = mod.main()
    assert len(reqs) == 16
    assert excel_path.endswith("QPLANT_Requirements_Traceability_Matrix_v2.xlsx")
    assert (redirect / "QPLANT_RTM_Engineering_Handover.md").is_file()
    data = json.loads((redirect / "qplant_requirements_v2.json").read_text())
    assert data[0]["child_requirements"] == ["RTM-02", "RTM-03", "RTM-04"]
    out = capsys.readouterr().out
    assert "Total Requirements: 16" in out
    assert "RTM Generation Complete!" in out
