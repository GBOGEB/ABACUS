"""Drift guard — ssot_tables.py Tables 27/28/29 vs the vendored contract rows.

ssot_tables.py holds hand-typed copies of contract Addendum II rev 146
App. 11.2 Tables 27-29. The vendored JSON is the cryoplant-project W365
extraction of the same tables, so any edit on either side fails here.
"""

import hashlib
import json
from pathlib import Path

from models.qps_line_s import ssot_tables

VENDORED = (
    Path(__file__).resolve().parent.parent
    / "docs"
    / "qps_line_s_recovery"
    / "addendum2_rev146_tables_27_29.json"
)
CONTRACT_SHA256 = "16b56d57a70034614a8b95ddb92e47aafb0d3328d99a6d9b7e46aa8729ee2779"

# Table 28 (heat load direction, heat load type) -> ssot_tables.HeatLoadAValues field
TABLE_28_FIELDS = {
    ("From the TS Mass to the Cold Mass", "Conduction"): "q1_cond_a_m",
    ("From the TS Mass to the Cold Mass", "Radiation"): "q1_rad_a_w_per_k4",
    ("From ambient to the TS Mass", "Conduction"): "q2_cond_a_m",
    ("From ambient to the TS Mass", "Radiation"): "q2_rad_a_w_per_k4",
}


def _vendored() -> dict:
    return json.loads(VENDORED.read_text(encoding="utf-8"))


def _table(number: int) -> dict:
    prefix = f"Table {number}."
    matches = [t for t in _vendored()["tables"] if t["caption"].startswith(prefix)]
    assert len(matches) == 1, f"expected one {prefix} in {VENDORED.name}"
    return matches[0]


def _number(cell: str) -> float:
    """Contract cell to float: '9 885 kg' -> 9885.0, 'a = 1.82 E-05' -> 1.82e-05."""
    text = cell.strip().removeprefix("a =").removesuffix("kg")
    return float(text.replace(" ", ""))


def contract_table_27() -> dict[str, ssot_tables.LumpedMassKg]:
    rows = _table(27)["rows"]
    assert rows[0] == ["LINAC Configuration", "Cold Mass", "TS Mass"]
    return {
        name: ssot_tables.LumpedMassKg(
            cold_mass_kg=_number(cold), ts_mass_kg=_number(ts)
        )
        for name, cold, ts in rows[1:]
    }


def contract_table_28() -> dict[str, ssot_tables.HeatLoadAValues]:
    rows = _table(28)["rows"]
    header = rows[0]
    assert header[:2] == ["Heat load direction", "Heat load type"]
    configs = header[3:]
    values: dict[str, dict[str, float]] = {c: {} for c in configs}
    for row in rows[1:]:
        direction = " ".join(row[0].split())
        field = TABLE_28_FIELDS[(direction, row[1])]
        for config, cell in zip(configs, row[3:]):
            values[config][field] = _number(cell)
    return {c: ssot_tables.HeatLoadAValues(**v) for c, v in values.items()}


def contract_table_29() -> tuple[tuple[float, float, float], ...]:
    rows = _table(29)["rows"]
    assert rows[0] == [
        "Temperature (K)",
        "Cold Mass Enthalpy (J/kg)",
        "TS Mass Enthalpy (J/kg)",
    ]
    return tuple(tuple(_number(cell) for cell in row) for row in rows[1:])


def table_29_mismatches(mirror, contract) -> list[str]:
    """Row-level differences between a Table 29 mirror and the contract."""
    problems = []
    if len(mirror) != len(contract):
        problems.append(f"row count {len(mirror)} != {len(contract)}")
    for got, want in zip(mirror, contract):
        if got != want:
            problems.append(f"T={want[0]:g} K: mirror {got} != contract {want}")
    return problems


# --- vendored file provenance ---


def test_vendored_file_records_contract_sha256():
    source = _vendored()["source"]
    assert source["sha256"] == CONTRACT_SHA256
    assert source["contract_docx_revision"] == 146
    assert CONTRACT_SHA256 in ssot_tables.__doc__


def test_vendored_tables_unedited():
    data = _vendored()
    canonical = json.dumps(
        data["tables"], sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    assert hashlib.sha256(canonical.encode()).hexdigest() == data["tables_sha256"]


# --- every hand-typed value equals the contract ---


def test_table_27_mass_matches_contract():
    assert ssot_tables.SSOT_TABLE_27_MASS_KG == contract_table_27()


def test_table_28_a_values_match_contract():
    assert ssot_tables.SSOT_TABLE_28_A_VALUES == contract_table_28()


def test_table_29_enthalpy_matches_contract():
    contract = contract_table_29()
    assert len(contract) == 30
    assert (
        table_29_mismatches(ssot_tables.SSOT_TABLE_29_ENTHALPY_J_PER_KG, contract) == []
    )


# --- the guard itself detects drift ---


def test_number_parser_reads_contract_cell_formats():
    assert _number("9 885 kg") == 9885.0
    assert _number("8 602") == 8602.0
    assert _number("a = -2.93") == -2.93
    assert _number("a = 1.82 E-05") == 1.82e-05
    assert _number("0.6") == 0.6


def test_table_29_drift_is_reported():
    contract = contract_table_29()
    drifted = list(contract)
    drifted[19] = (100.0, 10413.8, 12096.5)
    problems = table_29_mismatches(tuple(drifted[:-1]), contract)
    assert problems == [
        "row count 29 != 30",
        "T=100 K: mirror (100.0, 10413.8, 12096.5) != contract "
        "(100.0, 10413.9, 12096.5)",
    ]
