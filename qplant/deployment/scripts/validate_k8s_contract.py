#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "deployment"
K8S = DEPLOY / "k8s"
EXPECTED_NAMESPACE = "qplant-production"
EXPECTED_PORT = 8100
EXPECTED_IMAGE = "qplant/api-server:v4.4.0"
EXPECTED_RUNTIME_USER = "10001:10001"


def docs(name: str):
    return list(yaml.safe_load_all((K8S / name).read_text(encoding="utf-8")))


def load_one(name: str):
    values = [d for d in docs(name) if d]
    if len(values) != 1:
        raise AssertionError(f"{name}: expected one YAML document, got {len(values)}")
    return values[0]


def check(condition: bool, message: str):
    if not condition:
        raise AssertionError(message)


def container_by_name(deployment: dict, name: str) -> dict:
    containers = deployment["spec"]["template"]["spec"].get("containers", [])
    return next(c for c in containers if c.get("name") == name)


def env_map(container: dict) -> dict[str, str]:
    out = {}
    for row in container.get("env", []):
        if "value" in row:
            out[row["name"]] = str(row["value"])
    return out


def main() -> None:
    dockerfile = (DEPLOY / "Dockerfile").read_text(encoding="utf-8")
    check("ENV QPLANT_API_PORT=8100" in dockerfile, "Dockerfile canonical API port is not 8100")
    check("EXPOSE 8100 8200" in dockerfile, "Dockerfile does not expose canonical API/config ports")
    check(
        f"USER {EXPECTED_RUNTIME_USER}" in dockerfile,
        "Dockerfile runtime USER must be a verifiable numeric non-root UID:GID",
    )

    deployment = load_one("deployment-api-server.yaml")
    check(deployment["metadata"]["namespace"] == EXPECTED_NAMESPACE, "deployment namespace mismatch")
    api = container_by_name(deployment, "api-server")
    check(api["image"] == EXPECTED_IMAGE, "deployment image mismatch")
    check(api["ports"][0]["containerPort"] == EXPECTED_PORT, "deployment containerPort mismatch")
    check(api["ports"][0]["name"] == "http", "deployment named port missing")
    check(env_map(api).get("QPLANT_API_PORT") == str(EXPECTED_PORT), "QPLANT_API_PORT env mismatch")
    for probe in ("startupProbe", "livenessProbe", "readinessProbe"):
        check(api[probe]["httpGet"]["port"] == "http", f"{probe} must use named http port")
    security = api.get("securityContext", {})
    check(security.get("allowPrivilegeEscalation") is False, "api privilege escalation must be disabled")
    check(security.get("readOnlyRootFilesystem") is True, "api root filesystem must be read-only")
    check(security.get("capabilities", {}).get("drop") == ["ALL"], "api Linux capabilities must be dropped")

    init = deployment["spec"]["template"]["spec"]["initContainers"][0]
    check(init["image"] == EXPECTED_IMAGE, "SSOT init validator must reuse canonical image dependencies")

    service = load_one("service.yaml")
    check(service["metadata"]["namespace"] == EXPECTED_NAMESPACE, "service namespace mismatch")
    check(service["spec"]["type"] == "ClusterIP", "ingress-fronted service must be ClusterIP")
    check(service["spec"]["ports"][0]["targetPort"] == "http", "service targetPort must use named http port")

    network = load_one("network-policy.yaml")
    allowed_ports = [p["port"] for rule in network["spec"].get("ingress", []) for p in rule.get("ports", [])]
    check(allowed_ports and set(allowed_ports) == {EXPECTED_PORT}, "network policy ingress port mismatch")

    hpa = load_one("hpa.yaml")
    check(hpa["spec"]["scaleTargetRef"]["name"] == deployment["metadata"]["name"], "HPA target mismatch")
    check(hpa["spec"]["minReplicas"] == deployment["spec"]["replicas"], "HPA minReplicas must equal HA baseline")
    check(hpa["spec"]["maxReplicas"] >= hpa["spec"]["minReplicas"], "HPA replica range invalid")

    config = load_one("configmap-ssot-production.yaml")
    check(config["metadata"]["namespace"] == EXPECTED_NAMESPACE, "production SSOT namespace mismatch")
    check(config.get("immutable") is True, "production SSOT ConfigMap must be immutable")

    validator_docs = [d for d in docs("ssot-validation-init-container.yaml") if d]
    check(len(validator_docs) == 2, "SSOT validator file must contain ConfigMap + CronJob")
    for item in validator_docs:
        check(item["metadata"]["namespace"] == EXPECTED_NAMESPACE, "SSOT validator namespace mismatch")
    cron = next(d for d in validator_docs if d["kind"] == "CronJob")
    cron_container = cron["spec"]["jobTemplate"]["spec"]["template"]["spec"]["containers"][0]
    check(cron_container["image"] == EXPECTED_IMAGE, "SSOT CronJob image mismatch")
    volumes = {v["name"]: v for v in cron["spec"]["jobTemplate"]["spec"]["template"]["spec"]["volumes"]}
    check(volumes["ssot-config"]["configMap"]["name"] == config["metadata"]["name"], "SSOT CronJob ConfigMap mismatch")

    ingress = load_one("ingress.yaml")
    backend = ingress["spec"]["rules"][0]["http"]["paths"][0]["backend"]["service"]
    check(backend["name"] == service["metadata"]["name"], "Ingress service binding mismatch")
    check(backend["port"]["number"] == service["spec"]["ports"][0]["port"], "Ingress service port mismatch")

    files = sorted(p for p in K8S.glob("*.yaml"))
    manifest_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    receipt = {
        "schema": "qplant-k8s-contract-receipt/v1",
        "status": "PASS",
        "namespace": EXPECTED_NAMESPACE,
        "api_port": EXPECTED_PORT,
        "image": EXPECTED_IMAGE,
        "replicas": {"baseline": deployment["spec"]["replicas"], "max": hpa["spec"]["maxReplicas"]},
        "security": {
            "non_root_pod": deployment["spec"]["template"]["spec"]["securityContext"]["runAsNonRoot"],
            "numeric_runtime_user": EXPECTED_RUNTIME_USER,
            "read_only_rootfs": security["readOnlyRootFilesystem"],
            "drop_all_capabilities": security["capabilities"]["drop"] == ["ALL"],
            "network_policy": True,
            "immutable_ssot": config["immutable"],
        },
        "manifest_sha256": manifest_hashes,
    }
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
