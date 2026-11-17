"""Adversarial tests for Codespaces federation identity checks."""

from copy import deepcopy

import pytest

from scripts.validate_federation_identity import validate

CANON = "GBOGEB/CODESPACES_jyperter"


@pytest.fixture
def data():
    manifest = {
        "federation": {
            "moniker": "DELTA_1",
            "planes": {"notebook": {"repository": CANON}},
            "member_repos": [{"name": CANON, "status": "active", "plane": "notebook"}],
        }
    }
    runtime = {"federation": {"notebook_plane": {"repository": CANON}}}
    contract = {
        "contract": {
            "consumer": "GBOGEB/codespaces_jyperter",
            "provider": "GBOGEB/ABACUS",
            "federation_moniker": "DELTA_1",
        }
    }
    return manifest, runtime, contract


def test_case_alias_allowed(data):
    validate(*data)


@pytest.mark.parametrize(
    "bad",
    [
        "GBOGEB/other",
        "EVIL/CODESPACES_jyperter",
        "../CODESPACES_jyperter",
        "GBOGEB/",
        "GBOGEB/CODESPACES_jyperter/other",
        "",
        None,
        " GBOGEB/CODESPACES_jyperter",
    ],
)
def test_reject_other_consumer_id(data, bad):
    m, r, c = deepcopy(data)
    c["contract"]["consumer"] = bad
    with pytest.raises(ValueError):
        validate(m, r, c)


def test_reject_duplicate_differing_only_by_case(data):
    m, r, c = deepcopy(data)
    m["federation"]["member_repos"].append(
        {
            "name": CANON.lower(),
            "status": "active",
            "plane": "notebook",
        }
    )
    with pytest.raises(ValueError, match="duplicate"):
        validate(m, r, c)


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "proposed"),
        ("plane", "auxiliary"),
    ],
)
def test_reject_wrong_membership_state(data, field, value):
    m, r, c = deepcopy(data)
    m["federation"]["member_repos"][0][field] = value
    with pytest.raises(ValueError):
        validate(m, r, c)


def test_reject_runtime_mismatch(data):
    m, r, c = deepcopy(data)
    r["federation"]["notebook_plane"]["repository"] = "EVIL/other"
    with pytest.raises(ValueError):
        validate(m, r, c)
