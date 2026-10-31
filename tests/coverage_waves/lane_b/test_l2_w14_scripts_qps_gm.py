"""Lane-B wave 14: QPS M05 consumers, GM-I-A CoolProp bridges and QPS SSOT views."""

import copy
import hashlib
import json
import re
import sys
import types

import pytest

from ._l2_loader import load

va = load("scripts/qps_m05_verify_attestation_return.py")
g5 = load("scripts/qps_m05_g5_dow_readiness.py")
gm = load("scripts/validate_gm_i_a_coolprop_runtime_bridge.py")
gp = load("scripts/validate_gm_i_a_coolprop_runtime_bridge_p002.py")


# ------------------------------------------------------------------ helpers


class _Resp:
    def __init__(self, raw):
        self._raw = raw

    def read(self):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _install_urlopen(monkeypatch, mod, routes):
    """Route URLs to canned payloads; records each requested URL."""
    seen = []

    def fake_urlopen(req, timeout=None):
        url = req if isinstance(req, str) else req.full_url
        seen.append(url)
        payload = routes[url]
        raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        return _Resp(raw)

    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)
    return seen


# ------------------------------------------------- qps_m05_verify_attestation


def _va_routes():
    receipt = {
        "schema": "qps.m05.attestation_return_receipt.v1",
        "authority": va.AUTHORITY,
        "action": {"sha": va.EXPECTED_ACTION_SHA},
        "automatic_control_vector": {
            "run_id": va.RUN_ID,
            "job_id": va.EXPECTED_JOB_ID,
            "source_head_sha": va.EXPECTED_HEAD,
            "carrier_sha": va.EXPECTED_HEAD,
            "subject_sha256": va.EXPECTED_SUBJECT_SHA256,
            "attestation_id": va.EXPECTED_ATTESTATION_ID,
            "artifact": {
                "id": va.EXPECTED_ARTIFACT_ID,
                "digest": va.EXPECTED_ARTIFACT_DIGEST,
            },
            "result": "PASS",
        },
    }
    api = "https://api.github.com/repos/GBOGEB/CODEX/actions/runs/" + str(va.RUN_ID)
    run = {
        "status": "completed",
        "conclusion": "success",
        "head_sha": va.EXPECTED_HEAD,
        "event": "push",
        "head_branch": "main",
    }
    jobs = {
        "jobs": [
            {"id": 1, "status": "queued"},
            {
                "id": va.EXPECTED_JOB_ID,
                "status": "completed",
                "conclusion": "success",
                "steps": [{"conclusion": "success"}, {"conclusion": "success"}],
            },
        ]
    }
    artifacts = {
        "artifacts": [
            {"id": 2},
            {
                "id": va.EXPECTED_ARTIFACT_ID,
                "digest": va.EXPECTED_ARTIFACT_DIGEST,
                "expired": False,
            },
        ]
    }
    return {
        va.RECEIPT_URL: receipt,
        api: run,
        api + "/jobs": jobs,
        api + "/artifacts": artifacts,
    }


def test_va_main_pass_writes_receipt(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    routes = _va_routes()
    seen = _install_urlopen(monkeypatch, va, routes)
    assert va.main() == 0
    assert len(seen) == 4
    out_path = tmp_path / "artifacts" / "m05" / "dow_m05_consumer_receipt.json"
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data["status"] == "PASS"
    assert data["live_job_steps_verified_gt_zero"] == 2
    expected = hashlib.sha256(json.dumps(routes[va.RECEIPT_URL]).encode()).hexdigest()
    assert data["source_receipt_sha256"] == expected
    digest = hashlib.sha256(out_path.read_bytes()).hexdigest()
    sha_file = tmp_path / "artifacts" / "m05" / "dow_m05_consumer_receipt.sha256"
    assert sha_file.read_text(encoding="utf-8").strip() == digest
    printed = capsys.readouterr().out
    assert "DOW_M05_CONSUMER_RECEIPT_SHA256=" + digest in printed


def _mutate(routes, key, path, value):
    target = routes[key]
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value


@pytest.mark.parametrize(
    "suffix,path,value,message",
    [
        (None, ["schema"], "x", "receipt schema mismatch"),
        (None, ["authority"], "x", "authority boundary mismatch"),
        (None, ["automatic_control_vector", "result"], "FAIL", "not PASS"),
        ("", ["conclusion"], "failure", "live run is not successful"),
        ("", ["event"], "workflow_dispatch", "automatic main push"),
        ("/jobs", ["jobs"], [], "expected job not found"),
        ("/artifacts", ["artifacts"], [], "expected artifact not found"),
    ],
)
def test_va_main_fails_closed(tmp_path, monkeypatch, suffix, path, value, message):
    monkeypatch.chdir(tmp_path)
    routes = _va_routes()
    api = "https://api.github.com/repos/GBOGEB/CODEX/actions/runs/" + str(va.RUN_ID)
    key = va.RECEIPT_URL if suffix is None else api + suffix
    _mutate(routes, key, path, value)
    _install_urlopen(monkeypatch, va, routes)
    with pytest.raises(SystemExit, match=message):
        va.main()
    assert not (tmp_path / "artifacts").exists()


def test_va_zero_steps_and_expired_artifact(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    api = "https://api.github.com/repos/GBOGEB/CODEX/actions/runs/" + str(va.RUN_ID)
    routes = _va_routes()
    routes[api + "/jobs"]["jobs"][1]["steps"] = None
    _install_urlopen(monkeypatch, va, routes)
    with pytest.raises(SystemExit, match="zero-step"):
        va.main()
    routes = _va_routes()
    routes[api + "/artifacts"]["artifacts"][1]["expired"] = True
    _install_urlopen(monkeypatch, va, routes)
    with pytest.raises(SystemExit, match="already expired"):
        va.main()


def test_va_require_passes_silently():
    assert va.require(True, "never") is None


# ---------------------------------------------------- qps_m05_g5_dow_readiness


G5_API = "https://api.github.com/repos/GBOGEB/Q_engineering_tools/actions"


def _g5_routes():
    contract = {
        "schema": "qps.g5.keb_challenge.v1",
        "mission": "MISSION_H2_KEB",
        "local_mission": "M05_PROVENANCE_ATTESTATION",
        "authority": "SEMANTIC_PROVENANCE_CHALLENGE_ONLY_NOT_ENGINEERING_ACCEPTANCE",
        "challenge_predicate": {"promotion_authority": False},
        "semantic_contract": {
            "actual_numeric_cost_release": "WITHHELD_SOURCE_VALUES",
            "actual_numeric_cost_rows_ready": "0_of_3",
            "unknown_numeric_semantics": "NULL_NOT_ZERO",
            "source_value_gates": [974, 981],
        },
        "execution": {
            "run": g5.H1_RUN_ID,
            "job": g5.H1_JOB_ID,
            "runner_id": g5.H1_RUNNER_ID,
            "result": "PASS_EXECUTED_EXACT_PAYLOAD",
        },
    }
    run_url = G5_API + "/runs/" + str(g5.H2_RUN_ID)
    run = {
        "status": "completed",
        "conclusion": "success",
        "head_sha": g5.H2_HEAD,
        "event": "push",
        "head_branch": "main",
    }
    jobs = {
        "jobs": [
            {
                "id": g5.H2_JOB_ID,
                "status": "completed",
                "conclusion": "success",
                "runner_id": g5.H2_RUNNER_ID,
                "steps": [{"conclusion": "success"}],
            }
        ]
    }
    artifacts = {
        "artifacts": [
            {
                "id": g5.H2_ARTIFACT_ID,
                "digest": g5.H2_ARTIFACT_DIGEST,
                "expired": False,
                "workflow_run": {"head_sha": g5.H2_HEAD},
            }
        ]
    }
    return {
        g5.CONTRACT_URL: contract,
        run_url: run,
        run_url + "/jobs": jobs,
        run_url + "/artifacts": artifacts,
    }


def test_g5_main_pass(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _install_urlopen(monkeypatch, g5, _g5_routes())
    assert g5.main() == 0
    out_path = (
        tmp_path / "artifacts" / "m05" / "g5_dow_independent_consumer_receipt.json"
    )
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data["status"] == "PASS"
    assert data["promotion_authority"] is False
    assert data["h2_semantic_provenance"]["steps_verified_gt_zero"] == 1
    digest = hashlib.sha256(out_path.read_bytes()).hexdigest()
    assert "G5_DOW_INDEPENDENT_CONSUMER_SHA256=" + digest in capsys.readouterr().out


@pytest.mark.parametrize(
    "suffix,path,value,message",
    [
        (None, ["challenge_predicate", "promotion_authority"], True, "promotion"),
        (None, ["semantic_contract", "source_value_gates"], [1], "gate drift"),
        (None, ["execution", "runner_id"], 1, "H1 runner identity"),
        ("", ["head_sha"], "0" * 40, "H2 live head mismatch"),
        ("/jobs", ["jobs", 0, "runner_id"], 7, "H2 runner identity"),
        ("/jobs", ["jobs", 0, "steps"], [], "zero-step"),
        ("/jobs", ["jobs", 0, "steps"], [{"conclusion": "x"}], "steps passed"),
        ("/artifacts", ["artifacts", 0, "digest"], "sha256:0", "digest mismatch"),
        ("/artifacts", ["artifacts", 0, "workflow_run"], {}, "artifact head"),
    ],
)
def test_g5_main_fails_closed(tmp_path, monkeypatch, suffix, path, value, message):
    monkeypatch.chdir(tmp_path)
    routes = _g5_routes()
    run_url = G5_API + "/runs/" + str(g5.H2_RUN_ID)
    key = g5.CONTRACT_URL if suffix is None else run_url + suffix
    _mutate(routes, key, path, value)
    _install_urlopen(monkeypatch, g5, routes)
    with pytest.raises(SystemExit, match=message):
        g5.main()
    assert not (tmp_path / "artifacts").exists()


def test_g5_fetch_json_sends_user_agent(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["ua"] = req.get_header("User-agent")
        captured["timeout"] = timeout
        return _Resp(b'{"a": 1}')

    monkeypatch.setattr(g5.urllib.request, "urlopen", fake_urlopen)
    raw, value = g5.fetch_json("https://example.invalid/x")
    assert raw == b'{"a": 1}' and value == {"a": 1}
    assert captured == {"ua": "QPS-M05-G5-DOW-independent-consumer", "timeout": 30}


# ------------------------------------------------ GM-I-A CoolProp bridge (v1)


def _gm_fixture(pulse=None, merge=None):
    attestation = {
        "schema": "qps.gm_i_a.fast_heavy.federation_attestation.v1",
        "provider_repo": "GBOGEB/CoolProp",
        "source_head_sha": "a" * 40,
        "workflow": {"run_id": 42, "conclusion": "success"},
        "heavy": {"conclusion": "success", "artifact": {"digest": "sha256:h"}},
        "fast": {
            "conclusion": "success",
            "artifact": {"digest": "sha256:f"},
            "build_invoked": False,
            "source_checkout_performed": False,
            "calculations_passed": 17,
        },
        "authority": {"authority_transfer": False, "engineering_promotion": "WITHHELD"},
        "runtime_economics": {"fast_s": 1.5},
    }
    if pulse:
        attestation["pulse_id"] = pulse
        attestation["source_merge_sha"] = merge
    raw = json.dumps(attestation).encode()
    manifest = {
        "schema": "abacus.gm_i_a.coolprop_runtime_bridge.v1",
        "consumer_repo": "GBOGEB/ABACUS",
        "authority_transfer": False,
        "engineering_promotion_forbidden": True,
        "provider": {
            "repo": "GBOGEB/CoolProp",
            "attestation_commit_sha": "c" * 40,
            "attestation_path": "att/attestation.json",
            "attestation_sha256": hashlib.sha256(raw).hexdigest(),
            "source_head_sha": "a" * 40,
            "workflow_run_id": 42,
            "heavy_artifact_digest": "sha256:h",
            "fast_artifact_digest": "sha256:f",
        },
    }
    if pulse:
        manifest["pulse_id"] = pulse
        manifest["provider"]["source_merge_sha"] = merge
    url = "https://raw.githubusercontent.com/GBOGEB/CoolProp/" + "c" * 40
    url += "/att/attestation.json"
    return manifest, attestation, raw, url


def _write_manifest(monkeypatch, mod, tmp_path, manifest):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(mod, "MANIFEST", path)


def test_gm_canonical_and_sha():
    assert gm.canonical_bytes({"b": 1, "a": 2}) == b'{\n  "a": 2,\n  "b": 1\n}\n'
    assert gm.sha256_bytes(b"") == hashlib.sha256(b"").hexdigest()


def test_gm_main_writes_receipt(tmp_path, monkeypatch):
    manifest, _, raw, url = _gm_fixture()
    _write_manifest(monkeypatch, gm, tmp_path, manifest)
    seen = _install_urlopen(monkeypatch, gm, {url: raw})
    receipt_path = tmp_path / "receipt.json"
    monkeypatch.setattr(sys, "argv", ["prog", "--receipt", str(receipt_path)])
    gm.main()
    assert seen == [url]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["status"] == "PASS"
    assert receipt["fast_calculation_count"] == 17
    assert receipt["provider_attestation_sha256"] == hashlib.sha256(raw).hexdigest()
    assert receipt_path.read_bytes() == gm.canonical_bytes(receipt)


def test_gm_load_manifest_rejects_authority_transfer(tmp_path, monkeypatch):
    manifest, *_ = _gm_fixture()
    manifest["authority_transfer"] = True
    _write_manifest(monkeypatch, gm, tmp_path, manifest)
    with pytest.raises(AssertionError):
        gm.load_manifest()


def test_gm_fetch_provider_digest_mismatch(monkeypatch):
    manifest, _, raw, url = _gm_fixture()
    manifest["provider"]["attestation_sha256"] = "0" * 64
    _install_urlopen(monkeypatch, gm, {url: raw})
    with pytest.raises(ValueError, match="digest mismatch"):
        gm.fetch_provider(manifest)


def test_gm_validate_provider_rejects_build(monkeypatch):
    manifest, attestation, *_ = _gm_fixture()
    gm.validate_provider(manifest, attestation)
    bad = copy.deepcopy(attestation)
    bad["fast"]["build_invoked"] = True
    with pytest.raises(AssertionError):
        gm.validate_provider(manifest, bad)


# ------------------------------------------------ GM-I-A CoolProp bridge P002


def test_gp_main_writes_receipt(tmp_path, monkeypatch):
    manifest, _, raw, url = _gm_fixture(pulse="GM-I-A-MCLOCK-P002", merge="m" * 40)
    _write_manifest(monkeypatch, gp, tmp_path, manifest)
    _install_urlopen(monkeypatch, gp, {url: raw})
    receipt_path = tmp_path / "r.json"
    monkeypatch.setattr(sys, "argv", ["prog", "--receipt", str(receipt_path)])
    gp.main()
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["pulse_id"] == "GM-I-A-MCLOCK-P002"
    assert receipt["provider_workflow_run_id"] == 42
    assert receipt["runtime_economics"] == {"fast_s": 1.5}
    assert receipt_path.read_bytes() == gp.canonical_bytes(receipt)


def test_gp_main_rejects_digest_mismatch(tmp_path, monkeypatch):
    manifest, _, raw, url = _gm_fixture(pulse="GM-I-A-MCLOCK-P002", merge="m" * 40)
    manifest["provider"]["attestation_sha256"] = "f" * 64
    _write_manifest(monkeypatch, gp, tmp_path, manifest)
    _install_urlopen(monkeypatch, gp, {url: raw})
    receipt_path = tmp_path / "r.json"
    monkeypatch.setattr(sys, "argv", ["prog", "--receipt", str(receipt_path)])
    with pytest.raises(AssertionError):
        gp.main()
    assert not receipt_path.exists()


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
