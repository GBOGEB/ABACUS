"""Source binding — Line S RTM-292 envelope vs contract Addendum II rev 146.

The vendored JSON holds verbatim RTM-292, RTM-293, RTM-061 and Table 7 from
the cryoplant-project W365 contract extraction. These tests bind the Line S
inputs that cite those requirements to the contract text, so a hand edit or
a new contract revision fails here.
"""

import hashlib
import json
import re
from pathlib import Path

import yaml

from models.qps_line_s import contract_tables

ROOT = Path(__file__).resolve().parent.parent
LINE_S_DOCS = ROOT / "docs" / "qps_line_s_recovery"
CONTRACT_SHA256 = "16b56d57a70034614a8b95ddb92e47aafb0d3328d99a6d9b7e46aa8729ee2779"


def _vendored() -> dict:
    return contract_tables.load_vendored(contract_tables.RTM_VENDORED_PATH)


def _requirement(rtm_id: str) -> dict:
    matches = [r for r in _vendored()["requirements"] if r["id"] == rtm_id]
    assert len(matches) == 1, f"expected one {rtm_id}"
    return matches[0]


def _bullet(rtm_id: str, prefix: str) -> str:
    matches = [b for b in _requirement(rtm_id)["bullets"] if b.startswith(prefix)]
    assert len(matches) == 1, f"expected one {rtm_id} bullet {prefix!r}"
    return matches[0]


def _numbers(text: str) -> list[float]:
    return [float(n) for n in re.findall(r"\d+(?:\.\d+)?", text)]


def rtm_292_envelope() -> dict:
    """The RTM-292 values in the shape of ssot_heat_loads.yaml."""
    nominal = _numbers(_bullet("RTM-292", "Nominal return pressure:"))
    minimum = _numbers(_bullet("RTM-292", "Minimum allowable pressure:"))
    residual = _numbers(_bullet("RTM-292", "Residual/erratic return flow:"))
    reheating = _numbers(_bullet("RTM-292", "Uncontrolled reheating"))
    qve = _numbers(_bullet("RTM-292", "Sudden and total break"))
    return {
        "nominal_return_bar": {"value": nominal[0], "tol_mbar": nominal[1]},
        "min_allowable_bar": minimum[0],
        "use_cases": {
            "residual_g_s": residual[0],
            "reheating_nominal_g_s": reheating[0],
            "reheating_spike_g_s": reheating[1],
            "reheating_duration_h": reheating[2:4],
            "qve_break_spike_g_s": qve[0],
            "qve_break_duration_s": qve[1],
        },
        "source": "RTM_292",
    }


def _yaml(name: str) -> dict:
    return yaml.safe_load((LINE_S_DOCS / name).read_text(encoding="utf-8"))


# --- vendored file provenance ---


def test_vendored_rtm_file_records_contract_source():
    data = _vendored()
    assert data["source"]["sha256"] == CONTRACT_SHA256
    assert data["source"]["contract_docx_revision"] == 146
    assert data["requirement_ids"] == ["RTM-292", "RTM-293", "RTM-061"]
    assert [r["id"] for r in data["requirements"]] == data["requirement_ids"]


def test_vendored_rtm_records_unedited():
    data = _vendored()
    sha = contract_tables.tables_sha256
    assert sha(data["requirements"]) == data["requirements_sha256"]
    assert sha(data["tables"]) == data["tables_sha256"]


def test_upstream_requirement_edit_reports_drift(tmp_path):
    vendored = _vendored()
    requirements = {r["id"]: dict(r) for r in vendored["requirements"]}
    requirements["RTM-292"]["bullets"] = ["Minimum allowable pressure: 1.10 bar"]
    doc = {
        "source": {"docx_core": {"revision": 146}},
        "requirements": requirements,
        "tables": vendored["tables"],
    }
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    vendored["source"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    assert contract_tables.upstream_drift(path, vendored) == [
        "requirements RTM-292, RTM-293, RTM-061 differ from the vendored records"
    ]


# --- RTM-292: QRB.S flow conditions ---


def test_rtm_292_location():
    rtm = _requirement("RTM-292")
    assert rtm["text"] == "The flow conditions at QRB.S shall be:"
    assert rtm["page"] == 68
    assert rtm["section"].endswith("Specificities for Line S interface")


def test_ssot_heat_loads_rtm_292_envelope_matches_contract():
    assert _yaml("ssot_heat_loads.yaml")["rtm_292_envelope"] == rtm_292_envelope()


def test_rtm_293_holds_the_rtm_292_minimum():
    text = _requirement("RTM-293")["text"]
    assert "dropping below the minimum allowable pressure specified in RTM-292" in text


def test_rtm_292_states_no_pressure_ceiling():
    # RTM-292 gives a nominal and a minimum pressure only, so the 1.30 bar
    # ASSUM-PLIMIT ceiling cannot be sourced to it.
    pressures = [
        b for b in _requirement("RTM-292")["bullets"] if re.search(r"\bbar\b", b)
    ]
    assert [b.split(":")[0] for b in pressures] == [
        "Nominal return pressure",
        "Minimum allowable pressure",
    ]
    plimit = next(
        b
        for b in _yaml("assumptions_register.yaml")["blockers"]
        if b["id"] == "ASSUM-PLIMIT"
    )
    components = plimit["components"]
    assert components[plimit["binding_component"]]["source"] != "RTM-292"
    rtm_sourced = {
        name: c["value"] for name, c in components.items() if c["source"] == "RTM-292"
    }
    assert rtm_sourced == {"nominal_return": 1.10, "min_allowable": 1.05}


def test_scenario_flows_outside_rtm_292_use_cases():
    # 112 g/s (pre-HP) and 30 g/s (shield-mitigated) are not RTM-292 use cases.
    use_cases = rtm_292_envelope()["use_cases"]
    rtm_flows = {
        use_cases["residual_g_s"],
        use_cases["reheating_nominal_g_s"],
        use_cases["reheating_spike_g_s"],
        use_cases["qve_break_spike_g_s"],
    }
    scenarios = json.loads(
        (ROOT / "models" / "qps_line_s" / "scenarios.json").read_text(encoding="utf-8")
    )
    inflows = {float(c["m_in_g_s"]) for c in scenarios["cases"]}
    assert inflows - rtm_flows == {112.0, 30.0}


# --- RTM-061: failure classes behind REQ-130 / REQ-131 ---


def test_req_130_131_are_rtm_061_class_a_and_b():
    bullets = _requirement("RTM-061")["bullets"]
    limit = [i for i, b in enumerate(bullets) if "Thermal Shield temperature" in b]
    class_a = bullets.index("Class A – Failure of sustaining 2 K Operation")
    class_b = bullets.index("Class B – Failure of sustaining 2 K refrigeration")
    class_c = next(i for i, b in enumerate(bullets) if b.startswith("Class C"))
    assert class_a < limit[0] < class_b < limit[1] < class_c < limit[2]
    assert "may exceed" in bullets[limit[2]]
    qplant = json.loads(
        (
            ROOT / "qplant" / "canonical_master" / "attributes" / "requirements.json"
        ).read_text(encoding="utf-8")
    )
    texts = {r["id"]: r["text"] for r in qplant if r["id"] in ("REQ-130", "REQ-131")}
    assert texts == {"REQ-130": bullets[limit[0]], "REQ-131": bullets[limit[1]]}


def test_rtm_061_defines_no_numeric_shield_limit():
    bullets = _requirement("RTM-061")["bullets"]
    limits = [b for b in bullets if "Thermal Shield temperature limit" in b]
    assert len(limits) == 3
    assert not any(re.search(r"\d", b) for b in limits)


def test_table_7_ts_sb_shield_band():
    rows = _vendored()["tables"][0]["rows"]
    ts_sb = [r for r in rows if r[0] == "TS-SB" and r[1].startswith("T (K)")]
    assert len(ts_sb) == 1
    header = rows[0]
    line = dict(zip(header[2:], ts_sb[0][2:]))
    assert line["D"] == "~40 ‡ | ±5"
    assert line["E"] == "~60 ‡ | ±10"


# --- the HTML entry page mirrors the RTM statuses ---


def test_index_html_statuses_match_rtm_traceability():
    rtm = (LINE_S_DOCS / "rtm_traceability.md").read_text(encoding="utf-8")
    statuses = dict(re.findall(r"^### (.+) status\n\n`([A-Z_]+)`", rtm, re.M))
    page = (LINE_S_DOCS / "index.html").read_text(encoding="utf-8")
    rows = re.findall(
        r"<tr><td>([^<]+)</td><td>.*?</td>\s*<td><span class=\"chip \w+\">"
        r"([A-Z_]+)</span>",
        page,
        re.S,
    )
    shown = {item.replace(" / 131", " / REQ-131"): s for item, s in rows}
    assert shown == statuses
