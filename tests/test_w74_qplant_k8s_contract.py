import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "qplant" / "deployment" / "scripts" / "validate_k8s_contract.py"


def test_qplant_k8s_contract_executes_and_passes():
    run = subprocess.run(
        [sys.executable, str(VALIDATOR)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    receipt = json.loads(run.stdout)
    assert receipt["status"] == "PASS"
    assert receipt["api_port"] == 8100
    assert receipt["namespace"] == "qplant-production"
    assert receipt["replicas"] == {"baseline": 3, "max": 10}
    assert receipt["security"]["immutable_ssot"] is True
    assert receipt["security"]["network_policy"] is True
    assert receipt["security"]["numeric_runtime_user"] == "10001:10001"


def test_k8s_contract_has_manifest_hashes():
    run = subprocess.run(
        [sys.executable, str(VALIDATOR)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    receipt = json.loads(run.stdout)
    required = {
        "configmap-ssot-production.yaml",
        "deployment-api-server.yaml",
        "hpa.yaml",
        "ingress.yaml",
        "network-policy.yaml",
        "service.yaml",
        "ssot-validation-init-container.yaml",
    }
    assert required <= set(receipt["manifest_sha256"])
    assert all(len(value) == 64 for value in receipt["manifest_sha256"].values())
