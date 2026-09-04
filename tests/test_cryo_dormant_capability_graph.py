from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "cryo_dashboard_v0_3_0" / "dormant_capability_graph.yaml"


def load_graph():
    return yaml.safe_load(GRAPH.read_text())


def test_hepak_runtime_remains_fail_closed():
    graph = load_graph()
    node = next(n for n in graph["nodes"] if n["id"] == "NODE-HEPAK-ORACLE")
    atom = next(a for a in graph["atoms"] if a["id"] == "ATOM-HEPAK-RUNTIME")
    assert node["lifecycle"] == "DORMANT_DECLARED"
    assert node["runtime_import_proven"] is False
    assert atom["status"] == "UNPROVEN"


def test_coolprop_runtime_is_bound_to_real_workload():
    graph = load_graph()
    edge = next(e for e in graph["edges"] if e["id"] == "EDGE-005")
    assert edge["source"] == "NODE-QPS-LINE-S"
    assert edge["target"] == "NODE-COOLPROP-HELIUM-RUNTIME"
    assert edge["status"] == "ACTIVE"


def test_dow_keb_edges_are_not_overstated():
    graph = load_graph()
    dow = next(e for e in graph["edges"] if e["id"] == "EDGE-006")
    keb = next(e for e in graph["edges"] if e["id"] == "EDGE-007")
    assert dow["status"] == "PENDING_REGISTRY_BINDING"
    assert keb["status"] == "PENDING_REGISTRY_BINDING"


def test_on_duty_requires_real_workload_and_crosscheck():
    graph = load_graph()
    gates = graph["promotion_gates"]["INTEGRATED_TO_ON_DUTY"]
    assert "real_QPS_workload_execution" in gates
    assert "independent_crosscheck" in gates
    assert "regression_guard" in gates


def test_graph_creates_no_formal_credit():
    graph = load_graph()
    assert graph["formal_credit_delta"] == 0
