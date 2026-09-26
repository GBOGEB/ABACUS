from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from . import runtime as runtime_model

ROOT = Path(__file__).resolve().parents[2]
EXTRACTION = (
    ROOT
    / "docs"
    / "qps_line_s_recovery"
    / "appendix_8_4_mode_valve_extraction.yaml"
)
SOURCE_RECEIPT = (
    ROOT
    / "docs"
    / "qps_line_s_recovery"
    / "appendix_8_4_source_receipt.json"
)
ASSUMPTIONS = (
    ROOT
    / "docs"
    / "qps_line_s_recovery"
    / "assumptions_register.yaml"
)
RUNTIME_STATUS = (
    ROOT
    / "docs"
    / "qps_line_s_recovery"
    / "generated"
    / "runtime_status.json"
)

SCHEMA = "abacus.qps_line_s.appendix_8_4_mode_valve_extraction.v2"
RECEIPT_SCHEMA = "abacus.qps_line_s.appendix_8_4_source_receipt.v1"
MDA_GATE_IDS = {
    "ASSUM-VEFF",
    "ASSUM-PLIMIT",
    "ASSUM-RECOV-PWR",
    "ASSUM-ENERGY-MODEL",
}
ALLOWED_COMMANDED_STATES = {"OPEN", "CLOSED", "UNKNOWN"}
ALLOWED_FAIL_STATES = {
    "FAIL_OPEN",
    "FAIL_CLOSED",
    "NOT_APPLICABLE",
    "UNKNOWN",
}
ALLOWED_EXTRACTION_STATES = {
    "MODE_IDENTIFIED",
    "STATE_PARTIAL",
    "STATE_COMPLETE",
}
UNKNOWN_PLACEHOLDER = "UNKNOWN_FROM_CURRENT_EXTRACTION"
EXTRACTION_BLOCKER_IDS = {
    "APPENDIX_8_4_FULL_STATE_TRANSCRIPTION",
    "MODE_DEPENDENT_RECOVERY_PATH",
    "MODE_DEPENDENT_VEFF",
}
RESOLVED_UNRESOLVED_STATES = {"RESOLVED", "CLOSED", "COMPLETE"}
FIGURE_REF_PATTERN = re.compile(r"^image\d+\.emf$")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value.lower())
    )


def _is_unknown_placeholder(value: Any) -> bool:
    if not _nonempty(value):
        return True
    normalized = value.strip().upper()
    return normalized == "UNKNOWN" or normalized.startswith("UNKNOWN_")


def load_extraction(path: Path = EXTRACTION) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    require(
        isinstance(data, dict),
        "Appendix 8.4 extraction must be a mapping",
    )
    return data


def load_source_receipt(path: Path = SOURCE_RECEIPT) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    require(
        isinstance(data, dict),
        "Appendix 8.4 source receipt must be a mapping",
    )
    return data


def missing_required_artefacts(root: Path = ROOT) -> list[str]:
    missing: list[str] = []
    for artefact in runtime_model.REQUIRED_ARTEFACTS:
        relative = artefact.relative_to(runtime_model.ROOT)
        if not (root / relative).exists():
            missing.append(str(relative))
    return missing


def validate_extraction(data: dict) -> dict:
    require(
        data.get("schema") == SCHEMA,
        "Appendix 8.4 extraction schema mismatch",
    )
    require(
        data.get("authority_transfer") is False,
        "authority_transfer must remain false",
    )
    require(
        data.get("formal_credit_delta") == 0,
        "formal_credit_delta must remain zero",
    )

    source = data.get("source")
    require(isinstance(source, dict), "source must be a mapping")
    require(
        source.get("source_id") == "SRC-D2-8-4",
        "source_id must remain SRC-D2-8-4",
    )
    require(source.get("document") == "D2.1", "source document mismatch")
    require(
        source.get("section") == "Appendix 8.4 modes",
        "source section mismatch",
    )

    policy = data.get("policy")
    require(isinstance(policy, dict), "policy must be a mapping")
    require(
        policy.get("infer_valve_states") is False,
        "valve-state inference must remain disabled",
    )
    require(
        set(policy.get("allowed_commanded_states") or [])
        == ALLOWED_COMMANDED_STATES,
        "commanded-state vocabulary mismatch",
    )
    require(
        set(policy.get("allowed_fail_states") or [])
        == ALLOWED_FAIL_STATES,
        "fail-state vocabulary mismatch",
    )
    require(
        set(policy.get("allowed_extraction_states") or [])
        == ALLOWED_EXTRACTION_STATES,
        "extraction-state vocabulary mismatch",
    )

    modes = data.get("modes")
    require(isinstance(modes, list), "modes must be a list")

    source_available = source.get("source_material_available")
    require(
        isinstance(source_available, bool),
        "source_material_available must be boolean",
    )
    in_repo = source.get("source_material_available_in_repo")
    require(
        isinstance(in_repo, bool),
        "source_material_available_in_repo must be boolean",
    )

    if not source_available:
        require(
            data.get("status") == "SOURCE_PENDING",
            "unavailable source must keep extraction SOURCE_PENDING",
        )
        require(
            modes == [],
            "no mode/valve rows may be inferred while source is unavailable",
        )
        return data

    require(
        _nonempty(source.get("source_material_location")),
        "available source requires source_material_location",
    )
    require(
        data.get("status") in {"PARTIAL_EXTRACTED", "EXTRACTED"},
        "available source requires PARTIAL_EXTRACTED or EXTRACTED status",
    )
    require(
        _nonempty(source.get("source_ref")),
        "available source requires source_ref",
    )
    require(
        _nonempty(source.get("evidence_locator")),
        "available source requires evidence_locator",
    )
    require(
        _is_sha256(source.get("source_sha256")),
        "available source requires a 64-character source_sha256",
    )
    require(
        bool(modes),
        "source-backed extraction requires at least one mode row",
    )

    coverage = data.get("coverage")
    require(isinstance(coverage, dict), "coverage must be a mapping")
    expected = coverage.get("mode_inventory_expected")
    present = coverage.get("mode_rows_present")
    require(
        isinstance(expected, int) and expected > 0,
        "coverage.mode_inventory_expected must be a positive integer",
    )
    require(
        present == len(modes) == expected,
        "mode inventory coverage must match the source-bound mode count",
    )

    mode_ids = [
        mode.get("mode_id")
        for mode in modes
        if isinstance(mode, dict)
    ]
    require(
        len(mode_ids) == len(set(mode_ids)),
        "mode_id values must be unique",
    )

    extraction_states: list[str] = []
    figure_refs: list[str] = []
    figure_hashes: list[str] = []

    for mode_index, mode in enumerate(modes):
        require(
            isinstance(mode, dict),
            f"mode[{mode_index}] must be a mapping",
        )
        prefix = f"mode[{mode_index}]"
        require(
            mode.get("status") == "SOURCE_BOUND",
            f"{prefix} must be SOURCE_BOUND",
        )

        extraction_state = mode.get("extraction_state")
        require(
            extraction_state in ALLOWED_EXTRACTION_STATES,
            f"{prefix}.extraction_state is invalid",
        )
        extraction_states.append(extraction_state)

        require(
            _nonempty(mode.get("mode_id")),
            f"{prefix}.mode_id is required",
        )
        require(
            _nonempty(mode.get("mode_name")),
            f"{prefix}.mode_name is required",
        )
        require(
            _nonempty(mode.get("source_ref")),
            f"{prefix}.source_ref is required",
        )
        require(
            _nonempty(mode.get("evidence_locator")),
            f"{prefix}.evidence_locator is required",
        )

        figure_ref = mode.get("figure_ref")
        require(
            isinstance(figure_ref, str)
            and FIGURE_REF_PATTERN.fullmatch(figure_ref) is not None,
            f"{prefix}.figure_ref must be imageNN.emf",
        )
        figure_refs.append(figure_ref)

        figure_sha = mode.get("figure_sha256")
        require(
            _is_sha256(figure_sha),
            f"{prefix}.figure_sha256 must be a 64-character SHA-256",
        )
        figure_hashes.append(figure_sha)

        require(
            _nonempty(mode.get("recovery_path")),
            f"{prefix}.recovery_path is required",
        )
        require(
            _nonempty(mode.get("v_eff_consequence")),
            f"{prefix}.v_eff_consequence is required",
        )

        valves = mode.get("valves")
        require(
            isinstance(valves, list) and valves,
            f"{prefix}.valves must be a non-empty list",
        )
        for valve_index, valve in enumerate(valves):
            require(
                isinstance(valve, dict),
                f"{prefix}.valves[{valve_index}] must be a mapping",
            )
            vp = f"{prefix}.valves[{valve_index}]"
            require(
                _nonempty(valve.get("valve_id")),
                f"{vp}.valve_id is required",
            )
            members = valve.get("members")
            if members is not None:
                require(
                    isinstance(members, list)
                    and bool(members)
                    and all(_nonempty(member) for member in members),
                    f"{vp}.members must be a non-empty string list",
                )
            require(
                valve.get("commanded_state")
                in ALLOWED_COMMANDED_STATES,
                f"{vp}.commanded_state is invalid",
            )
            require(
                valve.get("fail_state") in ALLOWED_FAIL_STATES,
                f"{vp}.fail_state is invalid",
            )
            require(
                _nonempty(valve.get("source_ref")),
                f"{vp}.source_ref is required",
            )
            require(
                _nonempty(valve.get("evidence_locator")),
                f"{vp}.evidence_locator is required",
            )

        if extraction_state == "STATE_COMPLETE":
            require(
                not _is_unknown_placeholder(mode.get("recovery_path")),
                f"{prefix}.STATE_COMPLETE requires resolved recovery_path",
            )
            require(
                not _is_unknown_placeholder(
                    mode.get("v_eff_consequence")
                ),
                f"{prefix}.STATE_COMPLETE requires resolved "
                "v_eff_consequence",
            )
            for valve_index, valve in enumerate(valves):
                vp = f"{prefix}.valves[{valve_index}]"
                require(
                    valve.get("commanded_state") != "UNKNOWN",
                    f"{vp}.STATE_COMPLETE requires commanded state",
                )
                require(
                    valve.get("fail_state") != "UNKNOWN",
                    f"{vp}.STATE_COMPLETE requires fail-state disposition",
                )

    require(
        len(figure_refs) == len(set(figure_refs)),
        "figure_ref values must be unique",
    )
    require(
        len(figure_hashes) == len(set(figure_hashes)),
        "figure_sha256 values must be unique",
    )

    complete = extraction_states.count("STATE_COMPLETE")
    partial = extraction_states.count("STATE_PARTIAL")
    identified = extraction_states.count("MODE_IDENTIFIED")
    require(
        coverage.get("state_complete_modes") == complete,
        "coverage.state_complete_modes mismatch",
    )
    require(
        coverage.get("state_partial_modes") == partial,
        "coverage.state_partial_modes mismatch",
    )
    require(
        coverage.get("mode_identified_only") == identified,
        "coverage.mode_identified_only mismatch",
    )
    require(
        complete + partial + identified == expected,
        "extraction-state coverage must equal the mode inventory",
    )

    unresolved = data.get("unresolved", [])
    require(isinstance(unresolved, list), "unresolved must be a list")
    unresolved_by_id: dict[str, dict] = {}
    for index, row in enumerate(unresolved):
        require(
            isinstance(row, dict),
            f"unresolved[{index}] must be a mapping",
        )
        row_id = row.get("id")
        require(
            _nonempty(row_id),
            f"unresolved[{index}].id is required",
        )
        require(
            row_id not in unresolved_by_id,
            f"duplicate unresolved id: {row_id}",
        )
        unresolved_by_id[row_id] = row

    if data.get("status") == "EXTRACTED":
        require(
            complete == expected,
            "EXTRACTED requires every source mode to be STATE_COMPLETE",
        )
        require(
            coverage.get("extraction_complete") is True,
            "EXTRACTED requires coverage.extraction_complete=true",
        )
        for blocker_id in sorted(EXTRACTION_BLOCKER_IDS):
            require(
                blocker_id in unresolved_by_id,
                f"EXTRACTED requires blocker record {blocker_id}",
            )
            blocker = unresolved_by_id[blocker_id]
            blocker_state = str(blocker.get("state", "")).upper()
            require(
                blocker_state in RESOLVED_UNRESOLVED_STATES,
                f"EXTRACTED requires {blocker_id} resolved",
            )
    else:
        require(
            complete < expected,
            "PARTIAL_EXTRACTED must retain incomplete source-state coverage",
        )
        require(
            coverage.get("extraction_complete") is False,
            "PARTIAL_EXTRACTED requires coverage.extraction_complete=false",
        )

    return data


def validate_source_receipt(extraction: dict, receipt: dict) -> dict:
    require(
        receipt.get("schema") == RECEIPT_SCHEMA,
        "Appendix 8.4 source receipt schema mismatch",
    )
    require(
        receipt.get("authority_transfer") is False,
        "source receipt authority_transfer must remain false",
    )
    require(
        receipt.get("formal_credit_delta") == 0,
        "source receipt formal_credit_delta must remain zero",
    )
    require(
        receipt.get("authority_transfer")
        is extraction.get("authority_transfer"),
        "source receipt authority_transfer mismatch",
    )
    require(
        receipt.get("formal_credit_delta")
        == extraction.get("formal_credit_delta"),
        "source receipt formal_credit_delta mismatch",
    )

    source = extraction["source"]
    receipt_source = receipt.get("source")
    require(
        isinstance(receipt_source, dict),
        "source receipt source must be a mapping",
    )
    require(
        receipt_source.get("filename") == source.get("source_ref"),
        "source receipt filename mismatch",
    )
    require(
        receipt_source.get("sha256") == source.get("source_sha256"),
        "source receipt SHA-256 mismatch",
    )
    require(
        receipt_source.get("custody")
        == source.get("source_material_location"),
        "source receipt custody mismatch",
    )
    require(
        receipt_source.get("committed_to_repository")
        is source.get("source_material_available_in_repo"),
        "source receipt repository-custody mismatch",
    )

    coverage = extraction["coverage"]
    expected = coverage["mode_inventory_expected"]
    receipt_extraction = receipt.get("extraction")
    require(
        isinstance(receipt_extraction, dict),
        "source receipt extraction must be a mapping",
    )
    count_pairs = {
        "figure_count": expected,
        "mode_inventory_count": expected,
        "state_complete_modes": coverage["state_complete_modes"],
        "state_partial_modes": coverage["state_partial_modes"],
        "mode_identified_only": coverage["mode_identified_only"],
    }
    for key, expected_value in count_pairs.items():
        require(
            receipt_extraction.get(key) == expected_value,
            f"source receipt {key} mismatch",
        )
    require(
        receipt_extraction.get("extraction_complete")
        is coverage["extraction_complete"],
        "source receipt extraction_complete mismatch",
    )
    require(
        receipt_extraction.get("ocr_used") is False,
        "source receipt must retain ocr_used=false",
    )
    require(
        receipt_extraction.get("inferred_valve_states") is False,
        "source receipt must retain inferred_valve_states=false",
    )

    figures = receipt.get("figures")
    require(
        isinstance(figures, list) and len(figures) == expected,
        "source receipt figure inventory count mismatch",
    )
    receipt_by_image: dict[str, dict] = {}
    for index, figure in enumerate(figures):
        require(
            isinstance(figure, dict),
            f"source receipt figure[{index}] must be a mapping",
        )
        image = figure.get("image")
        require(
            isinstance(image, str)
            and FIGURE_REF_PATTERN.fullmatch(image) is not None,
            f"source receipt figure[{index}].image is invalid",
        )
        require(
            image not in receipt_by_image,
            "source receipt figure image values must be unique",
        )
        require(
            _is_sha256(figure.get("sha256")),
            f"source receipt figure[{index}].sha256 is invalid",
        )
        receipt_by_image[image] = figure

    for mode in extraction["modes"]:
        figure_ref = mode["figure_ref"]
        require(
            figure_ref in receipt_by_image,
            f"source receipt missing {figure_ref}",
        )
        receipt_figure = receipt_by_image[figure_ref]
        require(
            receipt_figure.get("title") == mode["mode_name"],
            f"source receipt title mismatch for {figure_ref}",
        )
        require(
            receipt_figure.get("sha256") == mode["figure_sha256"],
            f"source receipt digest mismatch for {figure_ref}",
        )

    partial_ids = {
        mode["mode_id"]
        for mode in extraction["modes"]
        if mode["extraction_state"] == "STATE_PARTIAL"
    }
    require(
        set(receipt.get("partial_state_modes") or []) == partial_ids,
        "source receipt partial_state_modes mismatch",
    )

    return receipt


def validate_current_contract(root: Path = ROOT) -> dict:
    assumptions_path = root / ASSUMPTIONS.relative_to(ROOT)
    runtime_path = root / RUNTIME_STATUS.relative_to(ROOT)
    extraction_path = root / EXTRACTION.relative_to(ROOT)
    receipt_path = root / SOURCE_RECEIPT.relative_to(ROOT)

    assumptions = (
        yaml.safe_load(assumptions_path.read_text(encoding="utf-8"))
        or {}
    )
    require(
        isinstance(assumptions, dict),
        "assumptions register must be a mapping",
    )
    meta = assumptions.get("meta") or {}
    require(
        meta.get("open_gates") == [],
        "assumptions SSOT must expose zero open MDA gates",
    )

    blockers = {
        row.get("id"): row
        for row in assumptions.get("blockers", [])
        if isinstance(row, dict) and row.get("id")
    }
    require(
        MDA_GATE_IDS <= set(blockers),
        "one or more canonical MDA gates are missing",
    )
    for gate_id in sorted(MDA_GATE_IDS):
        require(
            blockers[gate_id].get("status") == "RESOLVED",
            f"{gate_id} must remain RESOLVED for PROCEED_MDA",
        )

    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    require(
        runtime.get("verdict") == "PROCEED_MDA",
        "runtime verdict must match resolved MDA gates",
    )
    require(
        runtime.get("n_open_gates") == 0,
        "runtime must report zero open gates",
    )
    require(
        runtime.get("open_gates") == [],
        "runtime open_gates must be empty",
    )
    require(
        runtime.get("missing_artefacts") == [],
        "runtime missing_artefacts must be empty",
    )
    live_missing = missing_required_artefacts(root)
    require(
        live_missing == [],
        "required Line-S artefacts missing from current tree: "
        + ", ".join(live_missing),
    )

    extraction = validate_extraction(load_extraction(extraction_path))
    receipt = validate_source_receipt(
        extraction,
        load_source_receipt(receipt_path),
    )
    return {
        "status": "PASS",
        "mda_gate_count": len(MDA_GATE_IDS),
        "open_mda_gates": 0,
        "runtime_verdict": runtime["verdict"],
        "appendix_8_4_status": extraction["status"],
        "appendix_8_4_source_available": extraction["source"][
            "source_material_available"
        ],
        "appendix_8_4_source_available_in_repo": extraction["source"][
            "source_material_available_in_repo"
        ],
        "appendix_8_4_source_location": extraction["source"][
            "source_material_location"
        ],
        "appendix_8_4_receipt_status": receipt["status"],
        "authority_transfer": receipt["authority_transfer"],
        "formal_credit_delta": receipt["formal_credit_delta"],
    }


if __name__ == "__main__":
    print(json.dumps(validate_current_contract(), sort_keys=True))
