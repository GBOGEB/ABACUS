from pathlib import Path
import xml.etree.ElementTree as ET

import yaml
from jsonschema import validate

from renderers.mathml_renderer import MathMLRenderer
from renderers.process_flow_renderer import ProcessFlowRenderer
from src.qplant_presentation_engine.schema_validation import canonical_schema_path


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTENT_DIR = REPO_ROOT / "content" / "qplant"
SCHEMA_PATH = canonical_schema_path("yaml")

CONTENT_FILES = {
    "process_flow": CONTENT_DIR / "process_flow.yaml",
    "utilities": CONTENT_DIR / "utilities.yaml",
    "thermodynamics": CONTENT_DIR / "thermodynamics.yaml",
    "lifecycle": CONTENT_DIR / "lifecycle.yaml",
}


EXPECTED_TRUTH_PRINCIPLES = {
    "chat_is_not_repo",
    "architecture_is_not_runtime",
    "claimed_is_not_validated",
    "exists_in_repo_is_not_ci_execution",
}


def _load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _schema():
    return _load_yaml(SCHEMA_PATH)


def _schema_envelope(document: dict) -> dict:
    return {
        "visualization": document["visualization"],
        "lineage": document["lineage"],
        "metrics": document["metrics"],
        "truth_matrix": document["truth_matrix"],
    }


def _validate_common_envelope(document: dict) -> None:
    schema = _schema()

    for key in ("visualization", "lineage", "metrics", "truth_matrix"):
        assert key in document, f"missing required envelope key: {key}"

    visualization = document["visualization"]
    assert isinstance(visualization, dict)
    assert isinstance(visualization.get("type"), str) and visualization["type"].strip()
    assert isinstance(visualization.get("title"), str) and visualization["title"].strip()
    assert isinstance(visualization.get("data_ref"), str) and visualization["data_ref"].strip()

    validate(
        instance=document["lineage"],
        schema=schema["properties"]["lineage"],
    )
    validate(
        instance=document["metrics"],
        schema=schema["properties"]["metrics"],
    )
    validate(
        instance=document["truth_matrix"],
        schema=schema["properties"]["truth_matrix"],
    )


def test_qplant_content_files_exist_and_loadable():
    for path in CONTENT_FILES.values():
        assert path.exists(), f"missing content file: {path}"
        data = _load_yaml(path)
        assert isinstance(data, dict), f"content file is not a mapping: {path}"


def test_all_qplant_content_have_scientific_visualization_governance_envelope():
    for path in CONTENT_FILES.values():
        _validate_common_envelope(_load_yaml(path))


def test_supported_visualization_types_are_schema_compliant():
    schema = _schema()

    process_doc = _load_yaml(CONTENT_FILES["process_flow"])
    lifecycle_doc = _load_yaml(CONTENT_FILES["lifecycle"])

    validate(instance=_schema_envelope(process_doc), schema=schema)
    validate(instance=_schema_envelope(lifecycle_doc), schema=schema)


def test_process_flow_validity_and_renderer_compatibility():
    content = _load_yaml(CONTENT_FILES["process_flow"])
    process_flow = content["process_flow"]

    expected_nodes = [
        "WCSHCC",
        "PVPS",
        "WSH",
        "QRB",
        "Cold Box",
        "4.5 K Refrigeration",
        "2.0 K Superfluid Helium",
        "QCELL",
    ]
    expected_edges = [
        ("WCSHCC", "PVPS"),
        ("PVPS", "WSH"),
        ("WSH", "QRB"),
        ("QRB", "Cold Box"),
        ("Cold Box", "4.5 K Refrigeration"),
        ("4.5 K Refrigeration", "2.0 K Superfluid Helium"),
        ("2.0 K Superfluid Helium", "QCELL"),
    ]

    nodes = process_flow["nodes"]
    edges = process_flow["edges"]

    assert [node["id"] for node in nodes] == expected_nodes
    assert [(edge["from"], edge["to"]) for edge in edges] == expected_edges

    renderer_input = {
        "type": "process_flow",
        "title": content["visualization"]["title"],
        "nodes": nodes,
        "edges": edges,
    }
    svg = ProcessFlowRenderer().render(renderer_input)
    root = ET.fromstring(svg)
    rects = root.findall("{http://www.w3.org/2000/svg}rect")
    lines = root.findall("{http://www.w3.org/2000/svg}line")
    assert len(rects) == len(expected_nodes)
    assert len(lines) == len(expected_edges)


def test_utilities_table_metrics_validity():
    content = _load_yaml(CONTENT_FILES["utilities"])

    assert content["visualization"]["type"] == "table_metrics"
    expected = {
        "Cooling Water (PCW)": (1300, "kW"),
        "Electricity": (1526, "kW"),
        "HVAC": (124, "kW"),
        "Heat Recovery": (850, "kW"),
        "Instrument Air": (60, "m3/h"),
    }

    observed = {item["name"]: (item["capacity"], item["unit"]) for item in content["utilities"]}
    assert observed == expected


def test_thermodynamics_mathml_renderer_compatibility():
    content = _load_yaml(CONTENT_FILES["thermodynamics"])
    assert content["visualization"]["type"] == "scientific_equations"

    expected_displays = {
        "Carnot Efficiency": "η = 1 - Tc/Th",
        "COP": "COP = Q/W",
        "Heat Balance": "Q = m·cp·ΔT",
    }

    renderer = MathMLRenderer()
    for equation in content["equations"]:
        assert equation["display"] == expected_displays[equation["name"]]
        mathml = renderer.render({"name": equation["name"], "expression": equation["expression"]})
        root = ET.fromstring(mathml)
        assert root.tag.endswith("math")


def test_lifecycle_timeline_validity():
    content = _load_yaml(CONTENT_FILES["lifecycle"])
    assert content["visualization"]["type"] == "timeline"

    expected_labels = [
        "L0 Procurement",
        "L1 Concept Design",
        "L2 Detailed Design",
        "L3 Construction",
        "L4 Installation",
        "L5 Commissioning",
        "L6 Acceptance",
        "L8 Integrated Operation",
    ]
    stages = content["timeline"]["stages"]

    assert [stage["label"] for stage in stages] == expected_labels


def test_truth_matrix_principles_are_canonical_across_all_content_files():
    for path in CONTENT_FILES.values():
        content = _load_yaml(path)
        assert set(content["truth_matrix"]["principles"]) == EXPECTED_TRUTH_PRINCIPLES
