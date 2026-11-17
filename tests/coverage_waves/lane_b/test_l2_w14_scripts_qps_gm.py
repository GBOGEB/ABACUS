"""Lane-B wave 14: QPS SSOT views builder (openpyxl faked so the logic runs in CI).

Shared QPS M05 and GM-I-A modules are owned by #2533 (lane_ab_next).
"""

import hashlib
import json
import re
import sys
import types

import pytest

from ._l2_loader import load

# ------------------------------------------------------- build_qps_ssot_views


def _col_letter(index):
    letters = ""
    while index:
        index, rem = divmod(index - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


class _Dims(dict):
    def __init__(self):
        super().__init__()
        self.groups = []

    def __eq__(self, other):
        return dict.__eq__(self, other) and self.groups == getattr(
            other, "groups", None
        )

    __hash__ = None

    def __missing__(self, key):
        value = types.SimpleNamespace(width=None, height=None)
        self[key] = value
        return value

    def group(self, start, end, hidden=False):
        self.groups.append((start, end, hidden))


class _Sheet:
    def __init__(self, title):
        self.title = title
        self.cells = {}
        self.max_row = 0
        self.column_dimensions = _Dims()
        self.row_dimensions = _Dims()
        self.freeze_panes = None
        self.auto_filter = types.SimpleNamespace(ref=None)
        self.sheet_state = "visible"

    def cell(self, row, column):
        if (row, column) not in self.cells:
            self.cells[(row, column)] = types.SimpleNamespace(
                value=None, column=column, font=None, fill=None, alignment=None
            )
        return self.cells[(row, column)]

    def append(self, values):
        self.max_row += 1
        for col, value in enumerate(values, 1):
            self.cell(self.max_row, col).value = value

    def __setitem__(self, ref, value):
        match = re.fullmatch(r"([A-Z]+)(\d+)", ref)
        col = 0
        for ch in match.group(1):
            col = col * 26 + ord(ch) - 64
        row = int(match.group(2))
        self.max_row = max(self.max_row, row)
        self.cell(row, col).value = value

    @property
    def dimensions(self):
        width = max((c for _, c in self.cells), default=1)
        return "A1:" + _col_letter(width) + str(max(self.max_row, 1))

    def iter_rows(self):
        for row in sorted({r for r, _ in self.cells}):
            yield [self.cells[k] for k in sorted(self.cells) if k[0] == row]

    def values(self):
        rows = []
        for row in self.iter_rows():
            rows.append([cell.value for cell in row])
        return rows


class _Workbook:
    saved = {}

    def __init__(self):
        self.sheets = {"Sheet": _Sheet("Sheet")}

    @property
    def active(self):
        return next(iter(self.sheets.values()))

    def remove(self, sheet):
        del self.sheets[sheet.title]

    def create_sheet(self, name):
        self.sheets[name] = _Sheet(name)
        return self.sheets[name]

    def __getitem__(self, name):
        return self.sheets[name]

    def save(self, path):
        _Workbook.saved[str(path)] = self
        path.write_bytes(b"fake-xlsx")


def _style_obj(*args, **kwargs):
    return types.SimpleNamespace(args=args, **kwargs)


def _fake_openpyxl():
    root = types.ModuleType("openpyxl")
    root.Workbook = _Workbook
    styles = types.ModuleType("openpyxl.styles")
    styles.Alignment = styles.Font = styles.PatternFill = _style_obj
    utils = types.ModuleType("openpyxl.utils")
    utils.get_column_letter = _col_letter
    root.styles, root.utils = styles, utils
    return {"openpyxl": root, "openpyxl.styles": styles, "openpyxl.utils": utils}


bq = load(
    "scripts/build_qps_ssot_views.py",
    name="l2_w14_build_qps_ssot_views_fake",
    deps=_fake_openpyxl(),
)

ROWS = [
    {
        "Global_ID": "G-1",
        "Agenda_ID": "A1",
        "Compliance_State": "PARTIAL",
        "NEG_ID": "NEG-1",
        "RFI_ID": None,
        "OFFER_IDs": ["O1", "O2"],
        "Reentry_State": "closed",
        "Exact_Finding": "x" * 120,
        "Source_Page_Table_Section": "p3",
        "extra": {"k": 1},
    },
    {
        "Global_ID": "G-2",
        "Compliance_State": "NOK",
        "RFI_ID": "RFI-2",
        "Reentry_State": "OPEN",
        "Short_Topic": "</script>",
    },
]


def test_load_rows_accepts_list_and_object(tmp_path):
    path = tmp_path / "rows.json"
    path.write_text(json.dumps({"rows": ROWS}), encoding="utf-8")
    assert [r["Global_ID"] for r in bq.load_rows(path)] == ["G-1", "G-2"]
    path.write_text(json.dumps(ROWS), encoding="utf-8")
    assert len(bq.load_rows(path)) == 2


@pytest.mark.parametrize(
    "payload,message",
    [
        ({"rows": {"a": 1}}, "JSON list"),
        ([1], "Row 1 is not an object"),
        ([{"Global_ID": "  "}], "Row 1 has no Global_ID"),
        ([{"Global_ID": "X"}, {"Global_ID": "X"}], "Duplicate Global_ID: X"),
    ],
)
def test_load_rows_rejects(tmp_path, payload, message):
    path = tmp_path / "rows.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        bq.load_rows(path)


def test_scalar_and_hex6():
    assert bq.scalar(None) == ""
    assert bq.scalar(("a", 1)) == "a; 1"
    assert bq.scalar({"b": 2, "a": "é"}) == '{"a": "é", "b": 2}'
    assert bq.scalar(3.5) == "3.5"
    assert bq.hex6("#abcdef", "#000000") == "ABCDEF"
    assert bq.hex6(None, "#123456") == "123456"
    assert bq.hex6("#abc", "#654321") == "654321"


def test_load_style_variants(tmp_path):
    fallback = bq.load_style(None)
    assert fallback["typography"]["body"] == "Aptos"
    assert bq.load_style(tmp_path / "missing.json") == fallback
    good = tmp_path / "good.json"
    good.write_text('{"palette": {}}', encoding="utf-8")
    assert bq.load_style(good) == {"palette": {}}
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert bq.load_style(bad) == fallback


def test_apply_sheet_small_without_global_id():
    sheet = _Sheet("S")
    bq.apply_sheet(sheet, ["Owner", "Note"], [{"Owner": "me"}], {})
    assert sheet.freeze_panes == "A2"
    assert sheet.column_dimensions.groups == []
    assert sheet.values() == [["Owner", "Note"], ["me", ""]]
    assert sheet.row_dimensions[2].height == 18
    assert sheet.column_dimensions["A"].width == 13
    assert sheet.column_dimensions["B"].width == 14
    header = sheet.cell(1, 1)
    assert header.fill.fgColor == "562873" and header.font.color == "FFFFFF"


def test_apply_sheet_master_groups_and_widths():
    sheet = _Sheet("M")
    style = {"palette": {"tokens": {"define": "#111111"}}, "typography": {"body": "X"}}
    bq.apply_sheet(sheet, bq.MASTER, ROWS, style)
    assert sheet.freeze_panes == "D2"
    assert sheet.column_dimensions.groups == [("K", _col_letter(len(bq.MASTER)), True)]
    sck = _col_letter(bq.MASTER.index("SCK_Position") + 1)
    topic = _col_letter(bq.MASTER.index("Short_Topic") + 1)
    assert sheet.column_dimensions[sck].width == 44
    assert sheet.column_dimensions[topic].width == 24
    assert sheet.cell(1, 1).fill.fgColor == "111111"
    assert sheet.cell(2, 1).font.name == "X"
    assert sheet.values()[1][bq.MASTER.index("OFFER_IDs")] == "O1; O2"


def test_main_builds_all_outputs(tmp_path, monkeypatch, capsys):
    src = tmp_path / "in.json"
    src.write_text(json.dumps({"rows": ROWS}), encoding="utf-8")
    style = tmp_path / "style.json"
    style.write_text(
        json.dumps({"palette": {"tokens": {"define": "#AA00AA"}}}), encoding="utf-8"
    )
    out_dir = tmp_path / "out"
    argv = ["prog", str(src), "--out-dir", str(out_dir), "--style", str(style)]
    monkeypatch.setattr(sys, "argv", argv)
    bq.main()
    stem = "QPS_SUPPLIER_B_NEGO_RFI_COMPLIANCE_SSOT_v1.0"
    source_hash = hashlib.sha256(src.read_bytes()).hexdigest()

    manifest = json.loads((out_dir / (stem + ".build.json")).read_text("utf-8"))
    assert manifest["row_count"] == 2
    assert manifest["source_sha256"] == source_hash
    assert manifest["formal_credit"] == 0
    assert json.loads(capsys.readouterr().out) == manifest

    wb = _Workbook.saved[str(out_dir / (stem + ".xlsx"))]
    assert list(wb.sheets) == bq.VISIBLE_SHEETS + bq.HIDDEN_SHEETS
    assert all(wb[name].sheet_state == "hidden" for name in bq.HIDDEN_SHEETS)
    assert wb["START_HERE"].cell(3, 2).value == source_hash
    dash = dict(row for row in wb["DASHBOARD"].values()[1:])
    assert dash == {
        "Canonical actionable rows": 2,
        "Rows with NEG": 1,
        "Rows with RFI": 1,
        "Rows unresolved": 1,
        "Rows with source locator": 1,
    }
    assert wb["SOURCE_HASHES"].values() == [["source_row_sha256", source_hash]]
    assert wb["RAW_RELATIONS"].values()[2][0] == "G-2"

    html = (out_dir / (stem + ".html")).read_text(encoding="utf-8")
    assert source_hash in html
    assert "--purple:#AA00AA" in html
    assert "<\\/script>" in html
    assert "const ROWS=" in html


@pytest.mark.TEST_BLOCKED_DEPENDENCY
def test_build_xlsx_with_real_openpyxl(tmp_path):
    openpyxl = pytest.importorskip(
        "openpyxl", reason="TEST_BLOCKED_DEPENDENCY: openpyxl not installed"
    )
    real = load("scripts/build_qps_ssot_views.py", name="l2_w14_build_qps_real")
    out = tmp_path / "x" / "v.xlsx"
    real.build_xlsx(ROWS, out, "abc", real.load_style(None))
    wb = openpyxl.load_workbook(out)
    assert wb.sheetnames == real.VISIBLE_SHEETS + real.HIDDEN_SHEETS
    assert wb["RAW_RELATIONS"].sheet_state == "hidden"
    assert wb["MASTER_REVIEW"].max_row == 3
