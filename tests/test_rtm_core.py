"""Tests for the current QPLANT RTM generator implementation."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = (
    PROJECT_ROOT
    / "rtm_integration"
    / "automation"
    / "scripts"
    / "automation"
    / "improved_rtm_generator.py"
)


def _load_generator_class():
    assert MODULE_PATH.is_file(), f"RTM generator not found: {MODULE_PATH}"
    spec = importlib.util.spec_from_file_location("improved_rtm_generator", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ImprovedCryoplantRTMGenerator


def _sample_requirement():
    return {
        "req_id": "RTM-T001",
        "description": "The QPLANT shall provide safe operational flow control.",
        "full_description": "The QPLANT shall provide safe operational flow control.",
        "sbs_l0": "QSYS-PR",
        "sbs_l1": "QPLANT",
        "sbs_l2": "WCS",
        "sbs_l3": "PVPS",
        "requirement_type": "Safety",
        "verification_method": "Test",
        "acceptance_criteria": "Compliance with requirement as specified",
        "priority": "High",
        "source_section": "test",
        "parent_requirements": [],
        "child_requirements": [],
        "status": "Active",
        "rationale": "Required for safe operation of cryogenic system",
        "category": "Safety",
        "numerical_value": "N/A",
    }


def test_current_rtm_generator_loads():
    generator_class = _load_generator_class()
    generator = generator_class()

    assert generator.sbs_structure
    assert "QSYS" in generator.sbs_structure
    assert "QPLANT" in generator.sbs_structure
    assert "WCS" in generator.sbs_structure


def test_current_rtm_generator_classifies_requirement():
    generator = _load_generator_class()()

    assert generator._determine_requirement_type(
        "The QPLANT shall provide safe purge protection."
    ) == "Safety"
    assert generator._determine_priority(
        "The QPLANT shall provide safe purge protection."
    ) == "High"
    assert generator._determine_verification_method(
        "The QPLANT shall pass an acceptance test."
    ) == "Test"


def test_current_rtm_generator_assigns_sbs():
    generator = _load_generator_class()()

    assignment = generator._assign_to_sbs(
        "RTM-T001",
        "The warm compressor WCS high pressure piping shall be protected.",
    )

    assert assignment["l1"] == "QPLANT"
    assert assignment["l2"] == "WCS"
    assert assignment["l3"] in {"PVPS", "HP"}


def test_current_rtm_generator_builds_rtm_dataframe():
    generator = _load_generator_class()()

    frame = generator.create_rtm_dataframe([_sample_requirement()])

    assert isinstance(frame, pd.DataFrame)
    assert list(frame["Requirement ID"]) == ["RTM-T001"]
    assert list(frame["Requirement Type"]) == ["Safety"]
    assert list(frame["Verification Method"]) == ["Test"]


def test_current_rtm_generator_builds_sbs_dataframe():
    generator = _load_generator_class()()

    frame = generator.create_sbs_dataframe()

    assert isinstance(frame, pd.DataFrame)
    assert "QPLANT" in set(frame["SBS ID"])
    assert "WCS" in set(frame["SBS ID"])
