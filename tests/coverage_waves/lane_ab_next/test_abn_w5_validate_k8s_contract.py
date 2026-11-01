"""Behaviour tests for qplant/deployment/scripts/validate_k8s_contract.py.

The real Dockerfile and k8s manifests are copied into tmp_path and the module's
DEPLOY/K8S paths are redirected there, so each contract rule can be broken in
isolation without touching the repository.
"""

import json
import shutil

import pytest
import yaml

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

mod = load(
    "qplant/deployment/scripts/validate_k8s_contract.py",
    name="abn_w5_validate_k8s_contract",
)

SRC_DEPLOY = REPO_ROOT / "qplant" / "deployment"


@pytest.fixture
def deploy(tmp_path, monkeypatch):
    target = tmp_path / "deployment"
    (target / "k8s").mkdir(parents=True)
    shutil.copyfile(SRC_DEPLOY / "Dockerfile", target / "Dockerfile")
    for path in (SRC_DEPLOY / "k8s").glob("*.yaml"):
        shutil.copyfile(path, target / "k8s" / path.name)
    monkeypatch.setattr(mod, "DEPLOY", target)
    monkeypatch.setattr(mod, "K8S", target / "k8s")
    return target


def _rewrite(deploy, name, mutate):
    path = deploy / "k8s" / name
    items = [d for d in yaml.safe_load_all(path.read_text(encoding="utf-8")) if d]
    mutate(items)
    path.write_text(yaml.safe_dump_all(items), encoding="utf-8")


def _api(items):
    containers = items[0]["spec"]["template"]["spec"]["containers"]
    return next(c for c in containers if c["name"] == "api-server")


def _pod(items):
    return items[0]["spec"]["template"]["spec"]


def test_module_constants_point_at_repo_deployment():
    assert mod.ROOT == REPO_ROOT / "qplant"
    assert mod.K8S == SRC_DEPLOY / "k8s"
    assert mod.EXPECTED_PORT == 8100


def test_check_helper():
    mod.check(True, "unused")
    with pytest.raises(AssertionError, match="boom"):
        mod.check(False, "boom")


def test_env_map_keeps_only_literal_values():
    container = {
        "env": [
            {"name": "A", "value": 1},
            {"name": "B", "valueFrom": {"secretKeyRef": {}}},
            {"name": "C", "value": "x"},
        ]
    }
    assert mod.env_map(container) == {"A": "1", "C": "x"}
    assert mod.env_map({}) == {}


def test_container_by_name_found_and_missing():
    dep = {"spec": {"template": {"spec": {"containers": [{"name": "a"}]}}}}
    assert mod.container_by_name(dep, "a") == {"name": "a"}
    with pytest.raises(StopIteration):
        mod.container_by_name(dep, "b")
    with pytest.raises(StopIteration):
        mod.container_by_name({"spec": {"template": {"spec": {}}}}, "a")


def test_load_one_rejects_multi_document(deploy):
    with pytest.raises(AssertionError, match="expected one YAML document, got 2"):
        mod.load_one("ssot-validation-init-container.yaml")
    (deploy / "k8s" / "empty.yaml").write_text("---\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="got 0"):
        mod.load_one("empty.yaml")


def test_main_passes_on_real_manifests_and_prints_receipt(deploy, capsys):
    mod.main()
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["status"] == "PASS"
    assert receipt["schema"] == "qplant-k8s-contract-receipt/v1"
    assert receipt["namespace"] == "qplant-production"
    assert receipt["api_port"] == 8100
    assert receipt["replicas"]["baseline"] <= receipt["replicas"]["max"]
    assert receipt["security"]["drop_all_capabilities"] is True
    assert receipt["security"]["immutable_ssot"] is True
    names = sorted(p.name for p in (deploy / "k8s").glob("*.yaml"))
    assert sorted(receipt["manifest_sha256"]) == names
    assert all(len(h) == 64 for h in receipt["manifest_sha256"].values())


@pytest.mark.parametrize(
    "old,new,message",
    [
        ("ENV QPLANT_API_PORT=8100", "ENV QPLANT_API_PORT=9", "canonical API port"),
        ("EXPOSE 8100 8200", "EXPOSE 1 2", "does not expose"),
        ("USER 10001:10001", "USER root", "runtime USER"),
    ],
)
def test_dockerfile_rules(deploy, old, new, message):
    path = deploy / "Dockerfile"
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new), encoding="utf-8")
    with pytest.raises(AssertionError, match=message):
        mod.main()


def _set(getter, key, value):
    def mutate(items):
        getter(items)[key] = value

    return mutate


def _deep(*keys_then_value):
    *keys, value = keys_then_value

    def mutate(items):
        node = items[0]
        for key in keys[:-1]:
            node = node[key]
        node[keys[-1]] = value

    return mutate


def _env(name, value):
    def mutate(items):
        for row in _api(items)["env"]:
            if row["name"] == name:
                row["value"] = value

    return mutate


def _mount(key, value):
    def mutate(items):
        for row in _api(items)["volumeMounts"]:
            if row["name"] == "auth-state":
                row[key] = value

    return mutate


def _drop_mount(items):
    api = _api(items)
    api["volumeMounts"] = [r for r in api["volumeMounts"] if r["name"] != "auth-state"]


def _drop_volume(items):
    pod = _pod(items)
    pod["volumes"] = [v for v in pod["volumes"] if v["name"] != "auth-state"]


def _volume(new):
    def mutate(items):
        for row in _pod(items)["volumes"]:
            if row["name"] == "auth-state":
                row.clear()
                row.update(new)

    return mutate


def _security(key, value):
    def mutate(items):
        _api(items)["securityContext"][key] = value

    return mutate


def _probe(items):
    _api(items)["readinessProbe"]["httpGet"]["port"] = 8100


def _port(key, value):
    def mutate(items):
        _api(items)["ports"][0][key] = value

    return mutate


def _init_image(items):
    _pod(items)["initContainers"][0]["image"] = "other:1"


DEPLOYMENT_CASES = [
    (_deep("metadata", "namespace", "dev"), "deployment namespace mismatch"),
    (_set(lambda i: _pod(i)["securityContext"], "runAsNonRoot", False), "non-root"),
    (_set(lambda i: _pod(i)["securityContext"], "runAsUser", 0), "runAsUser"),
    (_set(lambda i: _pod(i)["securityContext"], "runAsGroup", 0), "runAsGroup"),
    (_set(lambda i: _pod(i)["securityContext"], "fsGroup", 0), "fsGroup"),
    (_set(_api, "image", "qplant/api-server:old"), "deployment image mismatch"),
    (_port("containerPort", 80), "containerPort mismatch"),
    (_port("name", "web"), "named port missing"),
    (_env("QPLANT_API_PORT", "9999"), "QPLANT_API_PORT env mismatch"),
    (_env("QPLANT_API_KEYS_DB", "/home/x.json"), "QPLANT_API_KEYS_DB"),
    (_probe, "readinessProbe must use named http port"),
    (_security("allowPrivilegeEscalation", True), "privilege escalation"),
    (_security("readOnlyRootFilesystem", False), "read-only"),
    (_security("capabilities", {"drop": ["NET_RAW"]}), "capabilities"),
    (_drop_mount, "must mount bounded auth-state"),
    (_mount("mountPath", "/var/other"), "auth-state mount path mismatch"),
    (_mount("readOnly", True), "must be writable"),
    (_drop_volume, "must declare auth-state volume"),
    (_volume({"name": "auth-state", "hostPath": {}}), "explicit emptyDir"),
    (_volume({"name": "auth-state", "emptyDir": {}}), "must stay bounded"),
    (_init_image, "SSOT init validator"),
]


@pytest.mark.parametrize("mutate,message", DEPLOYMENT_CASES)
def test_deployment_rules(deploy, mutate, message):
    _rewrite(deploy, "deployment-api-server.yaml", mutate)
    with pytest.raises(AssertionError, match=message):
        mod.main()


def _svc_port(items):
    items[0]["spec"]["ports"][0]["targetPort"] = 8100


def _netpol_port(items):
    for rule in items[0]["spec"]["ingress"]:
        for port in rule.get("ports", []):
            port["port"] = 80


def _netpol_empty(items):
    items[0]["spec"]["ingress"] = []


def _validator_ns(items):
    items[0]["metadata"]["namespace"] = "dev"


def _validator_extra(items):
    items.append({"kind": "ConfigMap", "metadata": {"namespace": "qplant-production"}})


def _cron(items):
    return next(d for d in items if d["kind"] == "CronJob")


def _cron_spec(items):
    return _cron(items)["spec"]["jobTemplate"]["spec"]["template"]["spec"]


def _cron_image(items):
    _cron_spec(items)["containers"][0]["image"] = "x:1"


def _cron_cm(items):
    for vol in _cron_spec(items)["volumes"]:
        if vol["name"] == "ssot-config":
            vol["configMap"]["name"] = "other"


def _ingress_backend(key):
    def mutate(items):
        backend = items[0]["spec"]["rules"][0]["http"]["paths"][0]["backend"]
        if key == "name":
            backend["service"]["name"] = "other"
        else:
            backend["service"]["port"]["number"] = 1

    return mutate


OTHER_CASES = [
    ("service.yaml", _deep("metadata", "namespace", "x"), "service namespace"),
    ("service.yaml", _deep("spec", "type", "NodePort"), "ClusterIP"),
    ("service.yaml", _svc_port, "service targetPort"),
    ("network-policy.yaml", _netpol_port, "network policy ingress port"),
    ("network-policy.yaml", _netpol_empty, "network policy ingress port"),
    ("hpa.yaml", _deep("spec", "scaleTargetRef", "name", "x"), "HPA target"),
    ("hpa.yaml", _deep("spec", "minReplicas", 1), "HPA minReplicas"),
    ("hpa.yaml", _deep("spec", "maxReplicas", 0), "HPA replica range"),
    (
        "configmap-ssot-production.yaml",
        _deep("metadata", "namespace", "x"),
        "production SSOT namespace",
    ),
    ("configmap-ssot-production.yaml", _deep("immutable", False), "immutable"),
    ("ssot-validation-init-container.yaml", _validator_extra, "ConfigMap \\+ CronJob"),
    ("ssot-validation-init-container.yaml", _validator_ns, "SSOT validator namespace"),
    ("ssot-validation-init-container.yaml", _cron_image, "SSOT CronJob image"),
    ("ssot-validation-init-container.yaml", _cron_cm, "SSOT CronJob ConfigMap"),
    ("ingress.yaml", _ingress_backend("name"), "Ingress service binding"),
    ("ingress.yaml", _ingress_backend("port"), "Ingress service port"),
]


@pytest.mark.parametrize("name,mutate,message", OTHER_CASES)
def test_other_manifest_rules(deploy, name, mutate, message):
    _rewrite(deploy, name, mutate)
    with pytest.raises(AssertionError, match=message):
        mod.main()


def test_main_missing_dockerfile(deploy):
    (deploy / "Dockerfile").unlink()
    with pytest.raises(FileNotFoundError):
        mod.main()
