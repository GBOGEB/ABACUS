from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "cryo_dashboard_v0_3_0" / "keb_bridge_contract.yaml"


def load_contract():
    return yaml.safe_load(CONTRACT.read_text())


def test_consumer_is_codex_keb_router():
    data = load_contract()
    assert data["consumer"]["repository"] == "GBOGEB/CODEX"
    assert data["consumer"]["role"] == "KEB_DOMAIN_CAPABILITY_ROUTER"


def test_heii_request_fails_closed_without_valid_provider():
    data = load_contract()
    assert "HeII_request_without_valid_low_temperature_provider" in data["request_contract"]["fail_closed_on"]


def test_hepak_is_not_claimed_active():
    data = load_contract()
    oracle = data["provider"]["independent_oracle"]
    assert oracle["lifecycle"] == "DORMANT_DECLARED"
    assert oracle["runtime_import_proven"] is False


def test_bidirectional_inter_repo_edges_exist():
    data = load_contract()
    types = {edge["type"] for edge in data["inter_repo_edges"]}
    assert "PROVIDES_TYPED_PROPERTY_RECEIPT_TO" in types
    assert "ROUTES_TYPED_PROPERTY_REQUEST_TO" in types


def test_no_formal_credit():
    assert load_contract()["formal_credit_delta"] == 0
