"""Read-only Mission Control Wide federation observations.

Local digest equality is not GitHub provenance, runtime execution, or admission.
A roll-up never promotes source discovery or candidate disappearance to closure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

INPUT_SCHEMA = "mcw.federation.input.v1"
PROOF_SCHEMA = "mcw.federation.proof.v1"
OUTPUT_SCHEMA = "mcw.federation.rollup.v1"
FAMILIES = frozenset(("MCL", "MIP", "DMAIC", "REX", "LDAB", "CENSUS", "3P", "PCA"))
SOURCE_OBSERVATION_SCHEMAS = {
    "MCL": "mcl.coverage.pulse.v1",
    "LDAB": "mip.ldab.telemetry.v1",
    "CENSUS": "bd.ldab.joined.census.v1",
}
EDGE_KINDS = frozenset(("evidence", "feedback", "dependency", "challenge"))
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value, name, minimum=0):
    require(type(value) is int and value >= minimum, "invalid " + name)
    return value


def sha(value, digits, name):
    pat = HEX40 if digits == 40 else HEX64
    require(isinstance(value, str) and pat.fullmatch(value), "invalid " + name)
    return value


def coverage(proof):
    data = proof.get("coverage")
    if data is None:
        return None
    require(isinstance(data, dict), "invalid coverage")
    require(
        isinstance(data.get("scope_id"), str) and bool(data["scope_id"]),
        "invalid scope",
    )
    sha(data.get("config_sha256"), 64, "coverage configuration")
    files = data.get("files")
    require(
        isinstance(files, list)
        and files
        and all(isinstance(f, str) and bool(f) for f in files)
        and len(set(files)) == len(files),
        "invalid coverage files",
    )
    for field in ("covered_lines", "total_lines", "covered_branches", "total_branches"):
        number(data.get(field), field)
    require(
        data["total_lines"] > 0 and data["covered_lines"] <= data["total_lines"],
        "invalid line coverage denominator",
    )
    require(
        data["covered_branches"] <= data["total_branches"],
        "invalid branch coverage denominator",
    )
    return {
        **data,
        "files": sorted(files),
        "line_percent": round(100 * data["covered_lines"] / data["total_lines"], 4),
        "branch_percent": (
            round(100 * data["covered_branches"] / data["total_branches"], 4)
            if data["total_branches"]
            else None
        ),
    }


def read_proof(node, root):
    artifact = node.get("artifact")
    if artifact is None:
        return None
    require(isinstance(artifact, dict), "artifact declaration must be an object")
    path = artifact.get("path")
    require(
        isinstance(path, str)
        and bool(path)
        and not Path(path).is_absolute()
        and ".." not in Path(path).parts,
        "unsafe artifact path",
    )
    sha(artifact.get("sha256"), 64, "artifact SHA-256")
    candidate = (root / path).resolve()
    require(
        candidate.is_relative_to(root) and candidate.is_file(),
        "artifact absent or escaped root",
    )
    raw = candidate.read_bytes()
    require(
        raw and hashlib.sha256(raw).hexdigest() == artifact["sha256"],
        "artifact byte mismatch",
    )
    proof = json.loads(raw)
    require(
        isinstance(proof, dict) and proof.get("schema") == PROOF_SCHEMA,
        "unsupported proof schema",
    )
    for field in ("repository", "source_sha", "family"):
        require(proof.get(field) == node[field], "proof identity mismatch: " + field)
    number(proof.get("run_id"), "run_id", 1)
    number(proof.get("job_id"), "job_id", 1)
    tests = proof.get("tests")
    require(isinstance(tests, dict), "missing native test counts")
    for f in ("required", "passed", "failed", "skipped"):
        number(tests.get(f), "tests." + f)
    require(
        tests["required"] > 0
        and sum(tests[k] for k in ("passed", "failed", "skipped")) == tests["required"],
        "inconsistent test denominator",
    )
    return {
        "run_id": proof["run_id"],
        "job_id": proof["job_id"],
        "tests": tests,
        "all_tests_pass": tests["passed"] == tests["required"],
        "coverage": coverage(proof),
        "sha256": artifact["sha256"],
    }


def compare_coverage(previous, current):
    if previous is None or current is None:
        return {"status": "UNKNOWN", "line_delta_pp": None, "branch_delta_pp": None}
    keys = ("scope_id", "config_sha256", "files", "total_lines", "total_branches")
    if any(previous.get(k) != current.get(k) for k in keys):
        return {
            "status": "INCOMPARABLE",
            "line_delta_pp": None,
            "branch_delta_pp": None,
        }
    return {
        "status": "COMPARABLE",
        "line_delta_pp": round(current["line_percent"] - previous["line_percent"], 4),
        "branch_delta_pp": (
            round(current["branch_percent"] - previous["branch_percent"], 4)
            if current["branch_percent"] is not None
            else None
        ),
        "newly_covered_lines": current["covered_lines"] - previous["covered_lines"],
        "newly_covered_branches": current["covered_branches"]
        - previous["covered_branches"],
    }


def rollup(bundle, artifact_root, previous=None):
    require(
        isinstance(bundle, dict) and bundle.get("schema") == INPUT_SCHEMA,
        "input schema mismatch",
    )
    require(
        isinstance(bundle.get("wave_id"), str) and bool(bundle["wave_id"]),
        "missing wave ID",
    )
    nodes, edges = bundle.get("nodes"), bundle.get("edges")
    require(
        isinstance(nodes, list) and isinstance(edges, list),
        "nodes/edges must be arrays",
    )
    require(all(isinstance(n, dict) for n in nodes), "invalid node")
    root = Path(artifact_root).resolve()
    seen, reports, counts = set(), [], Counter()
    for node in nodes:
        identity = node.get("id")
        require(
            isinstance(identity, str) and bool(identity) and identity not in seen,
            "invalid or duplicate node",
        )
        seen.add(identity)
        repo = node.get("repository")
        require(
            isinstance(repo, str) and repo.count("/") == 1 and all(repo.split("/")),
            "invalid repository",
        )
        sha(node.get("source_sha"), 40, "source SHA")
        require(node.get("family") in FAMILIES, "unknown federation family")
        proof = read_proof(node, root)
        observation = node.get("source_observation")
        if observation is not None:
            require(
                isinstance(observation, dict)
                and observation.get("evidence_grade") == "UNAUTHENTICATED_SOURCE_BYTES"
                and observation.get("schema")
                == SOURCE_OBSERVATION_SCHEMAS.get(node["family"])
                and isinstance(observation.get("metrics"), dict),
                "invalid source observation",
            )
            sha(observation.get("local_sha256"), 64, "source observation digest")
        counts[node["family"]] += 1
        reports.append(
            {
                "id": identity,
                "repository": repo,
                "source_sha": node["source_sha"],
                "family": node["family"],
                "byte_verified": proof is not None,
                "evidence_grade": (
                    "LOCAL_BYTE_MATCH_ONLY" if proof else "SOURCE_DISCOVERY_ONLY"
                ),
                "native_gha_authenticated": False,
                "source_observation": observation,
                "proof": proof,
            }
        )
    graph = set()
    outgoing = Counter()
    for edge in edges:
        require(isinstance(edge, dict), "invalid edge")
        a, b, kind = edge.get("source"), edge.get("target"), edge.get("kind")
        require(
            a in seen and b in seen and a != b and kind in EDGE_KINDS,
            "invalid or dangling edge",
        )
        key = (a, b, kind)
        require(key not in graph, "duplicate graph edge")
        graph.add(key)
        outgoing[a] += 1
    by_id = {row["id"]: row for row in reports}
    cross = sum(by_id[a]["repository"] != by_id[b]["repository"] for a, b, _ in graph)
    former = {}
    if previous is not None:
        require(
            isinstance(previous, dict) and previous.get("schema") == OUTPUT_SCHEMA,
            "invalid previous wave",
        )
        require(isinstance(previous.get("nodes"), list), "invalid previous nodes")
        former = {}
        for item in previous["nodes"]:
            require(
                isinstance(item, dict)
                and isinstance(item.get("id"), str)
                and bool(item["id"])
                and item["id"] not in former,
                "invalid or duplicate previous node",
            )
            require(
                isinstance(item.get("repository"), str)
                and item.get("family") in FAMILIES,
                "invalid previous identity",
            )
            sha(item.get("source_sha"), 40, "previous source SHA")
            older_proof = item.get("proof")
            if older_proof is not None:
                require(isinstance(older_proof, dict), "invalid previous proof")
                prior_cov = older_proof.get("coverage")
                if prior_cov is not None:
                    require(isinstance(prior_cov, dict), "invalid previous coverage")
                    normalized = coverage({"coverage": prior_cov})
                    require(
                        prior_cov == normalized,
                        "tampered previous coverage percentages or scope",
                    )
            former[item["id"]] = item
    deltas = {}
    for row in reports:
        old = former.get(row["id"])
        if old and (
            old["repository"] != row["repository"] or old["family"] != row["family"]
        ):
            deltas[row["id"]] = {
                "status": "INCOMPARABLE",
                "line_delta_pp": None,
                "branch_delta_pp": None,
            }
        else:
            before = (old.get("proof") or {}).get("coverage") if old else None
            after = (row.get("proof") or {}).get("coverage")
            deltas[row["id"]] = compare_coverage(before, after)
    evidenced = sum(row["byte_verified"] for row in reports)
    return {
        "schema": OUTPUT_SCHEMA,
        "wave_id": bundle["wave_id"],
        "counts": {
            "nodes": len(reports),
            "repositories": len({r["repository"] for r in reports}),
            "families": len(counts),
            "local_byte_verified_nodes": evidenced,
            "source_only_nodes": len(reports) - evidenced,
            "unverified_source_metric_nodes": sum(
                row["source_observation"] is not None for row in reports
            ),
            "declared_edges": len(graph),
            "declared_cross_repository_edges": cross,
            "declared_fanout_sources": len(outgoing),
            "max_declared_outdegree": max(outgoing.values(), default=0),
            "family_breadth_percent": round(100 * len(counts) / len(FAMILIES), 4),
            "local_byte_proof_percent": (
                round(100 * evidenced / len(reports), 4) if reports else None
            ),
        },
        "families": dict(sorted(counts.items())),
        "missing_families": sorted(FAMILIES - set(counts)),
        "nodes": sorted(reports, key=lambda x: x["id"]),
        "edges": [dict(source=a, target=b, kind=k) for a, b, k in sorted(graph)],
        "coverage_deltas": dict(sorted(deltas.items())),
        "rollup_line_percent": None,
        "rollup_branch_percent": None,
        "actual_worker_fanout": None,
        "rollout_accepted_receipts": None,
        "pca_gate": "WITHHELD_REQUIRES_LONGITUDINAL_NATIVE_QUALIFICATION",
        "dmaic_gate": "OBSERVATION_ONLY",
        "confirmed_root_closures": 0,
        "authenticated_federation_receipts": None,
        "active_runtime_workers": None,
        "merge_admission": "HOLD",
        "authority_transfer": False,
        "note": "Graph links are declared only; file hashes are local matches, not authenticated GitHub artifacts or peer execution.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prev = json.loads(args.previous.read_text()) if args.previous else None
    result = rollup(json.loads(args.input.read_text()), args.artifact_root, prev)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "wave_id": result["wave_id"],
                "counts": result["counts"],
                "merge_admission": result["merge_admission"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
