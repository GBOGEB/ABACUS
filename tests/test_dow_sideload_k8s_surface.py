"""DOW K8S side-load registry invariants; no QPS authority or runtime fabrications."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "triage/SIDELOAD_K8S_SURFACE_CURRENT_v1.json"
CAND = ROOT / "federation/sideload/DOW_K8S_STATIC_CANDIDATE_v1.json"


def load():
    return json.loads(REG.read_text()), json.loads(CAND.read_text())


def test_dow_registry_identifies_canonical_k8s_and_distinct_compose():
    reg, _ = load()
    k = {x["id"]: x for x in reg["canonical_products"]}
    assert len(k) == 4
    assert k["DOW_QPLANT_K8S_STATIC"]["port"] == 8100
    assert k["DOW_QPLANT_K8S_STATIC"]["namespace"] == "qplant-production"
    assert k["DOW_QPLANT_K8S_STATIC"]["baseline_replicas"] == 3
    assert k["DOW_QPLANT_K8S_STATIC"]["max_replicas"] == 10
    assert k["DOW_DOCKER_COMPOSE"]["kind"] == "DOCKER_COMPOSE"


def test_references_real_owned_files_without_copying_source():
    reg, cand = load()
    for record in reg["canonical_products"]:
        assert (ROOT / record["source"]).exists(), record["source"]
        if record["workflow"] is not None:
            assert (ROOT / record["workflow"]).is_file()
    assert (ROOT / cand["source"]["path"]).is_file()


def test_transport_is_candidate_not_auto_promoted():
    reg, cand = load()
    transport = reg["keb_transport"]
    assert transport["status"] == "CANDIDATE_EXTERNAL_PR_NOT_MERGED"
    assert len(transport["head_sha"]) == 40
    assert len(transport["contract_git_blob"]) == 40
    assert cand["schema"] == "qps.federation.sideload.envelope.v1"
    assert cand["producer"]["sha"] == reg["producer"]["captured_main_sha"]


def test_runtime_unknown_not_zero_or_static_credit():
    reg, cand = load()
    metrics = reg["sideload"]["runtime_metrics"]
    assert all(x is None for x in metrics.values())
    assert all(x is None for x in cand["native"].values())
    assert cand["source"]["sha256"] is None
    assert cand["source"]["size_bytes"] is None
    assert reg["sideload"]["edge_parent"]["inherited_from_cloud_k8s"] is False


def test_native_and_child_admission_remain_explicit_hold():
    reg, cand = load()
    a = reg["authority"]
    assert a["authority_transfer"] is False
    assert a["engineering_credit_delta"] == a["formal_credit_delta"] == 0
    assert a["merge_admission"] == "HOLD"
    assert a["qps_child_disposition"] == "DEFER"
    assert cand["claims"] == {
        "authority_transfer": False,
        "engineering_credit_delta": 0,
        "release_admitted": False,
    }


def test_w169_runtime_not_substituted_by_w74_static():
    reg, _ = load()
    static, api, runtime = reg["canonical_products"][:3]
    assert static["workflow"] != api["workflow"]
    assert api["workflow"] == runtime["workflow"]
    assert "NOT_INDEPENDENTLY_AUTHENTICATED" in api["status"]
