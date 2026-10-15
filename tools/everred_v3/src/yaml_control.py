"""Strict configuration control and dependency-DAG validation for EVERRED V3.1.

YAML is *configuration*, not a merge authority or an executable command stream.
The canonical ABACUS workflow_policy.json and .mesh/MESH_DOCK.yaml are NOT
replaced by these bounded review profiles.
"""

from __future__ import annotations

import hashlib
import re
from collections import deque
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None

from four_planes import EvidenceError, canon, demand


class StrictLoader(yaml.SafeLoader if yaml else object):
    """YAML 1.2 boolean rules, no duplicate keys, aliases or merges."""


if yaml is not None:
    StrictLoader.yaml_implicit_resolvers = {
        k: [(tag, regex) for tag, regex in v if tag != "tag:yaml.org,2002:bool"]
        for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }
    for c in "tTfF":
        StrictLoader.add_implicit_resolver(
            "tag:yaml.org,2002:bool", re.compile(r"^(?:true|false)$", re.I), [c]
        )

    def construct_mapping(loader, node, deep=False):
        mapping = {}
        for knode, vnode in node.value:
            key = loader.construct_object(knode, deep=deep)
            demand(isinstance(key, (str, int)), "invalid YAML map key")
            demand(key not in mapping, f"duplicate YAML key: {key}")
            demand(key != "<<", "YAML merge keys prohibited")
            mapping[key] = loader.construct_object(vnode, deep=deep)
        return mapping

    StrictLoader.add_constructor("tag:yaml.org,2002:map", construct_mapping)


def load_yaml(raw: str | bytes, *, max_bytes: int = 128000) -> dict:
    demand(yaml is not None, "PyYAML required for configuration")
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise EvidenceError("YAML not UTF-8") from exc
    demand(
        isinstance(raw, str) and len(raw.encode("utf-8")) <= max_bytes, "YAML too large"
    )
    try:
        events = list(yaml.parse(raw))
        demand(
            not any(isinstance(x, yaml.events.AliasEvent) for x in events),
            "YAML aliases prohibited",
        )
        value = yaml.load(raw, Loader=StrictLoader)
    except yaml.YAMLError as exc:
        raise EvidenceError(f"invalid YAML: {type(exc).__name__}") from exc
    demand(isinstance(value, dict), "YAML must be mapping")
    return value


def normalize_yaml(raw: str) -> tuple[str, str]:
    """Deterministic read-only formatting projection and semantic digest."""
    content = load_yaml(raw)
    text = yaml.safe_dump(
        content, sort_keys=True, allow_unicode=False, default_flow_style=False, width=79
    )
    demand(load_yaml(text) == content, "YAML formatter changed meaning")
    return text, hashlib.sha256(canon(content).encode("utf-8")).hexdigest()


def semantic_diff(old: str, new: str) -> dict:
    a = load_yaml(old)
    b = load_yaml(new)
    keys = sorted({*a, *b})
    return {
        "changed": a != b,
        "before_digest": hashlib.sha256(canon(a).encode()).hexdigest(),
        "after_digest": hashlib.sha256(canon(b).encode()).hexdigest(),
        "top_level_changes": [k for k in keys if a.get(k) != b.get(k)],
    }


def safe_path(path: str) -> str:
    demand(
        isinstance(path, str) and bool(path) and "\\" not in path,
        "path must be relative POSIX",
    )
    demand(
        not path.startswith("/") and not re.match(r"^[A-Za-z]:", path),
        "absolute path rejected",
    )
    parts = path.split("/")
    demand(all(p not in ("", ".", "..") for p in parts), "traversal or empty path")
    return path


def overlaps(a: str, b: str) -> bool:
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def validate_plan(plan: dict) -> dict:
    demand(
        isinstance(plan, dict)
        and plan.get("schema") == "abacus.everred.execution-plan.v1",
        "plan schema invalid",
    )
    tasks = plan.get("tasks")
    demand(isinstance(tasks, list) and 0 < len(tasks) <= 100, "task count invalid")
    ids = set()
    records = {}
    writes = []
    for task in tasks:
        demand(isinstance(task, dict), "task malformed")
        tid = task.get("id")
        demand(
            isinstance(tid, str) and bool(re.fullmatch(r"[A-Z][A-Z0-9_]{2,63}", tid)),
            "task ID invalid",
        )
        demand(tid not in ids, "duplicate task ID")
        ids.add(tid)
        demand(
            task.get("plane") in ("diagnostic", "runtime", "orchestration", "evidence"),
            "task plane invalid",
        )
        demand(
            task.get("mode") in ("READ_ONLY", "NATIVE_PROBE", "REVIEW_REQUIRED"),
            "task execution mode invalid",
        )
        demand(
            isinstance(task.get("owner"), str) and bool(task["owner"]), "owner missing"
        )
        deps = task.get("needs", [])
        paths = task.get("write_paths", [])
        demand(
            isinstance(deps, list) and all(isinstance(d, str) for d in deps),
            "dependencies malformed",
        )
        demand(isinstance(paths, list) and len(paths) <= 32, "path list invalid")
        norm_paths = [safe_path(p) for p in paths]
        demand(len(norm_paths) == len(set(norm_paths)), "duplicate write path")
        if norm_paths:
            demand(
                task["mode"] == "REVIEW_REQUIRED",
                "unapproved worker cannot write source",
            )
        for p in norm_paths:
            for owner, other in writes:
                demand(
                    not overlaps(p, other), f"worker write conflict: {tid} vs {owner}"
                )
            writes.append((tid, p))
        records[tid] = task
    incoming = {i: set(records[i].get("needs", [])) for i in records}
    for task_id, deps in incoming.items():
        demand(task_id not in deps and deps.issubset(ids), "unknown or self dependency")
    order = []
    ready = sorted(t for t, deps in incoming.items() if not deps)
    while ready:
        tid = ready.pop(0)
        order.append(tid)
        for successor, deps in incoming.items():
            if tid in deps:
                deps.remove(tid)
                if not deps and successor not in order and successor not in ready:
                    ready.append(successor)
                    ready.sort()
    demand(len(order) == len(records), "cyclic workflow dependency")
    return {
        "schema": plan["schema"],
        "task_count": len(records),
        "topological_order": order,
        "mutating_tasks": sorted(t for t, x in records.items() if x["write_paths"]),
        "source_leases_required": bool(writes),
        "dispatch_authority": False,
        "plan_digest": hashlib.sha256(canon(plan).encode()).hexdigest(),
    }


def evaluate_dispatch(plan: dict, observed: dict[str, str]) -> dict:
    """Prepare jobs, never execute a source-writing task or infer a pass."""
    result = validate_plan(plan)
    tasks = {t["id"]: t for t in plan["tasks"]}
    demand(
        all(
            k in tasks and s in ("PASS", "FAIL", "UNKNOWN", "PENDING")
            for k, s in observed.items()
        ),
        "status map invalid",
    )
    rows = []
    for tid in result["topological_order"]:
        t = tasks[tid]
        deps = t.get("needs", [])
        if t["mode"] == "REVIEW_REQUIRED":
            state = "HOLD_REVIEW"
        elif any(observed.get(d) == "FAIL" for d in deps):
            state = "BLOCKED_UPSTREAM_RED"
        elif any(observed.get(d) != "PASS" for d in deps):
            state = "WAITING_FOR_EVIDENCE"
        else:
            state = "READY_TO_REQUEST"
        rows.append(
            {
                "id": tid,
                "plane": t["plane"],
                "state": state,
                "needs": deps,
                "actor": t["owner"],
            }
        )
    return {
        "schema": "abacus.everred.dispatch-preview.v1",
        "tasks": rows,
        "executed": False,
        "mutations": False,
        "admission": "HOLD",
        "plan_digest": result["plan_digest"],
    }


def validate_federation_policy(policy: dict) -> dict:
    demand(
        isinstance(policy, dict)
        and policy.get("schema") == "abacus.everred.federation-policy.v1",
        "federation schema invalid",
    )
    bindings = policy.get("bindings")
    demand(isinstance(bindings, list) and bool(bindings), "federation mappings missing")
    pairs = set()
    for b in bindings:
        demand(isinstance(b, dict), "invalid binding")
        producer, consumer = b.get("producer"), b.get("consumer")
        for x in (producer, consumer):
            demand(
                isinstance(x, str)
                and bool(re.fullmatch(r"[\w.-]+/[\w.-]+", x))
                and all(seg not in (".", "..") for seg in x.split("/")),
                "federation repo invalid",
            )
        demand(producer != consumer, "federation requires distinct producer")
        demand(
            b.get("action") == "OBSERVATION_ONLY",
            "federation cannot delegate authority",
        )
        key = (producer, consumer, b.get("domain"))
        demand(key not in pairs, "duplicate federation binding")
        pairs.add(key)
    return {
        "binding_count": len(pairs),
        "policy_digest": hashlib.sha256(canon(policy).encode()).hexdigest(),
        "authority_transfer": False,
    }
