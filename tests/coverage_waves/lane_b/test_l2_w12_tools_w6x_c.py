"""Lane-B wave 12: W83 semantic-basis probe and synthetic Office style examples.

python-docx and openpyxl are not in requirements-test.txt, so the Office
builders are exercised against recording MagicMock stand-ins injected through
``sys.modules`` for the duration of each test.
"""

import json
import sys
from unittest import mock

import pytest

from ._l2_loader import load

w72 = load("tools/w72_semantic_census.py")
probe = load("tools/w83_semantic_basis_probe.py", deps={"w72_semantic_census": w72})
office = load("tools/build_office_style_examples.py")


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# w83_semantic_basis_probe
# --------------------------------------------------------------------------

SSOT_ITEMS = """preamble: ignored
- id: DOM-A
  owner: team
  status: draft-review
  source: docs/dom_a.md#anchor
  unrelated: value
- id: "DOM-B"
  status: active
- id: ''
  status: draft-review
"""

GAPS = """- id: GAP-1
  severity: high
  status: open
  review_gate: Contract Review
- id: GAP-2
  severity: critical
  status: closed
  review_gate: Technical Review
- id: GAP-3
  severity: low
  review_gate: Procurement Review
"""

MANIFEST = """- logical_id: AUTH-1
  path: docs/auth1.md
  state: AUTHORITATIVE_CANDIDATE
  migration: none
- logical_id: AUTH-2
  path: docs/auth2.md
  state: REGISTRY_CANDIDATE
- logical_id: STYLE-1
  state: AUTHORITATIVE_STYLE_CANDIDATE
"""

TRACE = """questions:
  Q1:
    ssot: AUTH-1
    gaps: [GAP-1, GAP-2, MISSING-9]
  Q2:
    ssot: DOM-A
    gaps: []
  # comment:
"""

POLICY = {
    "rules": [
        {"cluster": "c1", "disposition": "keep", "lifecycle": "pr_fast"},
        {"cluster": "c1", "disposition": "canonical", "lifecycle": "pr_domain"},
        {"cluster": "c2", "disposition": "retire", "lifecycle": "post_merge"},
        {"cluster": "c3", "lifecycle": "scheduled"},
        "junk",
    ]
}


def _probe_tree(root, policy=POLICY):
    _write(root / "ssot/ssot_items.yaml", SSOT_ITEMS)
    _write(root / "ssot/contractual_gap_register.yaml", GAPS)
    _write(root / "ssot/manifest.yaml", MANIFEST)
    _write(root / "ssot/semantic_traceability.yaml", TRACE)
    _write(
        root / "ssot/index.json",
        json.dumps(
            {
                "authorities": [
                    {"logical_id": "AUTH-1", "path": "docs/auth1.md"},
                    {"logical_id": "IDX-ONLY", "path": "docs/idx.md"},
                ]
            }
        ),
    )
    if policy is not None:
        _write(root / "ci/governance/workflow_policy.json", json.dumps(policy))
    _write(root / "docs/auth1.md", "self reference AUTH-1")
    _write(root / "docs/dom_a.md", "domain source")
    for i in range(5):
        _write(root / "src/use{0}.py".format(i), "AUTH-1 docs/dom_a.md")
    _write(root / "src/gap.md", "GAP-1 and DOM-B")


def test_canonical_sha256_is_order_independent():
    assert probe.canonical_sha256({"a": 1, "b": 2}) == probe.canonical_sha256(
        {"b": 2, "a": 1}
    )
    assert len(probe.canonical_sha256([])) == 64


def test_parse_records(tmp_path):
    path = _write(tmp_path / "items.yaml", SSOT_ITEMS)
    rows = probe.parse_records(path, "id", ("owner", "status", "source"))
    assert rows == [
        {
            "id": "DOM-A",
            "owner": "team",
            "status": "draft-review",
            "source": "docs/dom_a.md#anchor",
        },
        {"id": "DOM-B", "status": "active"},
        {"id": "", "status": "draft-review"},
    ]
    assert probe.parse_records(tmp_path / "missing.yaml", "id", ()) == []


def test_count_values():
    counts = probe.count_values([{"s": "a"}, {"s": "a"}, {}], "s")
    assert counts == {"a": 2, "MISSING": 1}


def test_workflow_features_variants(tmp_path):
    absent = probe.workflow_features(tmp_path)
    assert absent["policy_present"] == 0 and set(absent.values()) == {0}
    _write(tmp_path / "ci/governance/workflow_policy.json", json.dumps(POLICY))
    present = probe.workflow_features(tmp_path)
    assert present == {
        "policy_present": 1,
        "rule_count": 4,
        "cluster_count": 3,
        "keep_rules": 1,
        "canonical_rules": 1,
        "retire_rules": 1,
        "pr_fast_rules": 1,
        "pr_domain_rules": 1,
        "post_merge_rules": 1,
        "scheduled_rules": 1,
    }
    _write(tmp_path / "ci/governance/workflow_policy.json", "{broken")
    broken = probe.workflow_features(tmp_path)
    assert broken["policy_present"] == 1 and broken["rule_count"] == 0
    _write(tmp_path / "ci/governance/workflow_policy.json", "")
    assert probe.workflow_features(tmp_path)["rule_count"] == 0


def test_semantic_fanout(tmp_path):
    assert probe.semantic_fanout(tmp_path) == (0, 0, 0)
    _write(tmp_path / "ssot/semantic_traceability.yaml", TRACE)
    assert probe.semantic_fanout(tmp_path) == (2, 3, 3)


def test_probe_measures_tree(tmp_path):
    _probe_tree(tmp_path)
    result = probe.probe(tmp_path, "a" * 40, "s01")
    sc = result["blocks"]["semantic_composition"]
    assert sc["authority_ids"] == 3
    assert sc["domain_item_ids"] == 3
    assert sc["gap_ids"] == 3
    assert sc["known_ids"] == 8
    assert sc["manifest_bindings"] == 2
    assert sc["manifest_index_symmetric_diff"] == 2
    assert sc["domain_draft_review"] == 2
    assert sc["gap_open"] == 1 and sc["gap_high"] == 1 and sc["gap_critical"] == 1
    assert sc["gap_contract_review"] == 1
    assert sc["gap_technical_review"] == 1
    assert sc["gap_procurement_review"] == 1
    assert sc["manifest_authoritative_candidate"] == 1
    assert sc["manifest_registry_candidate"] == 1
    assert sc["manifest_style_candidate"] == 1
    assert sc["traceability_question_count"] == 2
    assert sc["traceability_max_gap_fanout"] == 3
    cg = result["blocks"]["consumer_graph_distribution"]
    assert cg["consumer_entities"] == 8
    assert cg["consumer_entities_five_plus_files"] == 2
    assert cg["max_consumer_files_per_entity"] == 5
    assert cg["graph_isolated_nodes"] >= 1
    wf = result["blocks"]["workflow_governance_composition"]
    assert wf["rule_count"] == 4
    fv = result["feature_vector"]
    assert fv["semantic_composition.gap_ids"] == 3
    assert result["feature_vector_sha256"] == probe.canonical_sha256(fv)
    assert result["block_sha256"]["semantic_composition"] == probe.canonical_sha256(sc)
    assert result["matrix_label"] == "s01"
    assert result["formal_credit_delta"] == 0


def test_probe_empty_root(tmp_path):
    result = probe.probe(tmp_path, "b" * 40, "p1281-pass")
    cg = result["blocks"]["consumer_graph_distribution"]
    assert cg["max_consumer_files_per_entity"] == 0
    assert cg["graph_max_degree"] == 0
    assert result["blocks"]["workflow_governance_composition"]["policy_present"] == 0


def test_probe_main(tmp_path, monkeypatch, capsys):
    _probe_tree(tmp_path, policy=None)
    out = tmp_path / "out" / "nested" / "probe.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "probe",
            "--root",
            str(tmp_path),
            "--source-sha",
            "c" * 40,
            "--matrix-label",
            "s02",
            "--out",
            str(out),
        ],
    )
    probe.main()
    data = json.loads(out.read_text())
    assert data["schema_version"] == probe.SCHEMA
    assert data["source_sha"] == "c" * 40
    assert json.loads(capsys.readouterr().out)["matrix_label"] == "s02"


# --------------------------------------------------------------------------
# build_office_style_examples
# --------------------------------------------------------------------------

DOCX_MODULES = (
    "docx",
    "docx.shared",
    "docx.enum.text",
    "docx.enum.table",
    "docx.enum.style",
    "docx.oxml",
    "docx.oxml.ns",
)
XLSX_MODULES = (
    "openpyxl",
    "openpyxl.chart",
    "openpyxl.styles",
    "openpyxl.formatting.rule",
    "openpyxl.worksheet.table",
    "openpyxl.workbook.properties",
)


def _install(monkeypatch, names):
    fakes = {}
    for name in names:
        fakes[name] = mock.MagicMock(name=name)
        monkeypatch.setitem(sys.modules, name, fakes[name])
    return fakes


def test_create_docx_with_fake_python_docx(tmp_path, monkeypatch):
    fakes = _install(monkeypatch, DOCX_MODULES)
    doc = fakes["docx"].Document.return_value
    run = mock.MagicMock(name="run")
    para = mock.MagicMock(name="para", runs=[run])
    header_cells = [
        mock.MagicMock(name="h{0}".format(i), paragraphs=[para]) for i in range(4)
    ]
    table = doc.add_table.return_value
    table.rows = [mock.MagicMock(name="header_row", cells=header_cells)]
    target = tmp_path / "x.docx"
    office.create_docx(target)
    doc.save.assert_called_once_with(target)
    assert [c.text for c in header_cells] == [
        "ID",
        "Input family",
        "Control",
        "Example state",
    ]
    assert table.add_row.call_count == 3
    assert run.bold is True
    assert doc.core_properties.title == "CODE PURPLE | Office Style Input"
    shd = fakes["docx.oxml"].OxmlElement
    shd.assert_called_with("w:shd")
    shd.return_value.set.assert_called_with(
        fakes["docx.oxml.ns"].qn.return_value, office.NAVY
    )
    headings = [c.args for c in doc.add_heading.call_args_list]
    assert headings[0] == ("Format, style & evidence", 0)
    assert len(headings) == 5


def test_create_xlsx_with_fake_openpyxl(tmp_path, monkeypatch):
    fakes = _install(monkeypatch, XLSX_MODULES)
    wb = fakes["openpyxl"].Workbook.return_value
    runs_sheet = mock.MagicMock(name="runs")
    guide = mock.MagicMock(name="guide")
    header_cells = [mock.MagicMock(name="g{0}".format(i)) for i in range(5)]
    cells = {}

    def guide_item(key):
        if key == 4:
            return header_cells
        return cells.setdefault(key, mock.MagicMock(name=str(key)))

    guide.__getitem__.side_effect = guide_item
    wb.create_sheet.side_effect = [runs_sheet, guide]
    target = tmp_path / "x.xlsx"
    office.create_xlsx(target)
    wb.save.assert_called_once_with(target)
    titles = [c.args[0] for c in wb.create_sheet.call_args_list]
    assert titles == ["Test Runs", "Style Guide"]
    assert runs_sheet.cell.call_count == 7 + 6 * 7
    assert runs_sheet.freeze_panes == "B5" and guide.freeze_panes == "B4"
    guide.__setitem__.assert_any_call("B2", "STYLE SYSTEM / INPUT CONTRACT")
    fill = fakes["openpyxl.styles"].PatternFill.return_value
    assert [c.fill is fill for c in header_cells] == [False, True, True, True, False]
    fakes["openpyxl.worksheet.table"].Table.assert_called_once_with(
        displayName="SyntheticRuns", ref="A4:G10"
    )
    chart = fakes["openpyxl.chart"].BarChart.return_value
    assert chart.title == "Passed tests per revision"
    assert wb.properties.creator == "CODE PURPLE synthetic fixtures"


def _fake_builders(monkeypatch):
    def fake_docx(path):
        path.write_bytes(b"docx-bytes")

    def fake_xlsx(path):
        path.write_bytes(b"xlsx")

    monkeypatch.setattr(office, "create_docx", fake_docx)
    monkeypatch.setattr(office, "create_xlsx", fake_xlsx)


def test_office_main_no_deck(tmp_path, monkeypatch, capsys):
    _fake_builders(monkeypatch)

    def no_subprocess(*a, **k):
        raise AssertionError("deck builder must not run")

    monkeypatch.setattr(office.subprocess, "run", no_subprocess)
    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["b", "--out", str(out), "--no-deck"])
    office.main()
    manifest = json.loads((out / "office_input_manifest.json").read_text())
    assert manifest["source_class"] == "SYNTHETIC_DEMONSTRATION"
    assert [f["name"] for f in manifest["files"]] == [
        "CODE_PURPLE_Office_Style_Sample.docx",
        "CODE_PURPLE_Office_Style_Sample.xlsx",
    ]
    assert manifest["files"][0]["bytes"] == len(b"docx-bytes")
    assert json.loads(capsys.readouterr().out)["authority_transfer"] is False


def test_office_main_with_deck(tmp_path, monkeypatch):
    _fake_builders(monkeypatch)
    calls = []

    def fake_run(cmd, check):
        calls.append(cmd)
        assert check is True
        _write(tmp_path / "out" / "CODE_PURPLE_Office_Style_Sample.pptx", "pptx")

    monkeypatch.setattr(office.subprocess, "run", fake_run)
    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["b", "--out", str(out)])
    office.main()
    assert calls[0][0] == "node"
    assert calls[0][1].endswith("build_office_style_deck.js")
    manifest = json.loads((out / "office_input_manifest.json").read_text())
    assert len(manifest["files"]) == 3
    assert manifest["files"][2]["name"].endswith(".pptx")


@pytest.mark.parametrize("name", ["NAVY", "BLUE", "TEAL", "AMBER", "LIGHT"])
def test_palette_tokens_are_hex(name):
    value = getattr(office, name)
    assert len(value) == 6 and int(value, 16) >= 0
