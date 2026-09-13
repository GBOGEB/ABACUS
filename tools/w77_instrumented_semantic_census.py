#!/usr/bin/env python3
"""Instrument W72 exact-source semantic census without changing its semantics."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import w72_semantic_census as w72

PROBE_SCHEMA = "MC2-W77-PHASE-RUNTIME-PROBE-0.1.0"


def timed(callable_):
    wall_start = time.perf_counter_ns()
    cpu_start = time.process_time_ns()
    value = callable_()
    cpu_ns = time.process_time_ns() - cpu_start
    wall_ns = time.perf_counter_ns() - wall_start
    return value, {"wall_ns": wall_ns, "cpu_ns": cpu_ns}


def instrumented_consumer_hits(
    root: Path, bindings: dict[str, str]
) -> tuple[dict[str, set[str]], dict[str, int]]:
    hits = {key: set() for key in bindings}
    counters = {
        "scanned_text_files": 0,
        "scanned_text_bytes": 0,
        "consumer_candidate_checks": 0,
        "consumer_hits": 0,
        "consumer_files_with_hits": 0,
    }
    hit_files: set[str] = set()
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in w72.TEXT_SUFFIXES:
            continue
        if any(part in w72.SKIP_PARTS for part in path.parts):
            continue
        rel = path.relative_to(root).as_posix()
        if rel.startswith("ssot/") or any(
            rel.startswith(prefix) for prefix in w72.SKIP_PREFIXES
        ):
            continue
        text = w72.read_text(path)
        counters["scanned_text_files"] += 1
        counters["scanned_text_bytes"] += len(text.encode("utf-8"))
        for key, bound_path in bindings.items():
            if bound_path and rel == bound_path:
                continue
            counters["consumer_candidate_checks"] += 1
            if key in text or (bound_path and bound_path in text):
                hits[key].add(rel)
                counters["consumer_hits"] += 1
                hit_files.add(rel)
    counters["consumer_files_with_hits"] = len(hit_files)
    return hits, counters


def build_instrumented(
    root: Path, source_sha: str
) -> tuple[dict[str, dict], dict, dict]:
    def parse_sources():
        manifest = w72.manifest_bindings(root)
        indexed = w72.indexed_bindings(root)
        domain = {
            key: value
            for key, value in w72.parse_id_records(
                root / "ssot/ssot_items.yaml", "source"
            ).items()
        }
        gaps = w72.gap_bindings(root)
        refs = w72.semantic_refs(root)
        return manifest, indexed, domain, gaps, refs

    parsed, parse_timing = timed(parse_sources)
    manifest, indexed, domain, gaps, refs = parsed

    authority_ids = set(manifest) | set(indexed)
    domain_ids = set(domain) | set(gaps)
    known = authority_ids | domain_ids

    registry_findings = sorted(set(manifest) ^ set(indexed))
    registry_total = len(authority_ids)
    registry_open = len(registry_findings)

    unresolved = sorted(
        ref for ref in refs if ref not in known and w72.ID_RE.fullmatch(ref)
    )
    reference_total = len(refs)
    reference_open = len(unresolved)

    lineage_paths: dict[str, str] = {}
    lineage_paths.update(indexed)
    for logical_id, path in domain.items():
        if path:
            lineage_paths[logical_id] = w72.strip_anchor(path)
    lineage_paths.update(gaps)

    consumer_bindings = {key: lineage_paths.get(key, "") for key in known}
    consumer_result, scan_timing = timed(
        lambda: instrumented_consumer_hits(root, consumer_bindings)
    )
    hits, scan_counters = consumer_result
    unbound = sorted(key for key, values in hits.items() if not values)
    consumer_total = len(known)
    consumer_open = len(unbound)
    consumer_evidence = {
        key: sorted(values) for key, values in sorted(hits.items()) if values
    }

    def build_graph_lineage():
        edges: list[tuple[str, str]] = []
        for logical_id, path in lineage_paths.items():
            edges.append((logical_id, f"path:{path}"))
        for ref in refs:
            if ref in known:
                edges.append(("semantic", ref))

        nodes = set(known) | set(refs) | {
            node for edge in edges for node in edge
        }
        degree = {node: 0 for node in nodes}
        for left, right in edges:
            degree[left] = degree.get(left, 0) + 1
            degree[right] = degree.get(right, 0) + 1
        isolated = sorted(
            node for node, degree_value in degree.items() if degree_value == 0
        )
        unlineaged = sorted(
            logical_id
            for logical_id in known
            if not lineage_paths.get(logical_id)
            or not (root / lineage_paths[logical_id]).exists()
        )
        return edges, nodes, isolated, unlineaged

    graph_result, graph_timing = timed(build_graph_lineage)
    edges, nodes, isolated, unlineaged = graph_result
    graph_total = len(nodes)
    graph_open = len(isolated)
    lineage_total = len(known)
    lineage_open = len(unlineaged)

    def build_receipts():
        lane_defs = {
            "A_registry_gap": (
                registry_total,
                registry_open,
                {
                    "authority_registry_mismatches": registry_findings,
                    "manifest_authority_ids": sorted(manifest),
                    "index_authority_ids": sorted(indexed),
                },
            ),
            "B_reference_gap": (
                reference_total,
                reference_open,
                {"unresolved_references": unresolved},
            ),
            "C_consumer_penetration": (
                consumer_total,
                consumer_open,
                {
                    "unbound_consumers": unbound,
                    "consumer_evidence": consumer_evidence,
                },
            ),
            "D_graph_orphan_drop": (
                graph_total,
                graph_open,
                {"isolated_nodes": isolated},
            ),
            "E_lineage_evidence": (
                lineage_total,
                lineage_open,
                {"unlineaged_ids": unlineaged},
            ),
        }
        receipts: dict[str, dict] = {}
        for lane, (total, open_count, findings) in lane_defs.items():
            closed = max(0, total - open_count)
            receipts[lane] = {
                "schema_version": w72.SCHEMA_VERSION,
                "repository": "GBOGEB/ABACUS",
                "source_sha": source_sha,
                "lane": lane,
                "state": "MEASURED",
                "totals": {
                    "total_population": total,
                    "backlog_open": open_count,
                    "backlog_closed": closed,
                    "completion_pct": w72.pct(closed, total),
                },
                "findings": findings,
            }
        feature_row = {
            "measurement_schema": w72.SCHEMA_VERSION,
            "source_sha": source_sha,
            "registry_gap_rate": w72.finite_rate(
                registry_open / max(registry_total, 1)
            ),
            "unresolved_reference_rate": w72.finite_rate(
                reference_open / max(reference_total, 1)
            ),
            "consumer_penetration_rate": w72.finite_rate(
                (consumer_total - consumer_open) / max(consumer_total, 1)
            ),
            "graph_drop_rate": w72.finite_rate(
                graph_open / max(graph_total, 1)
            ),
            "lineage_gap_rate": w72.finite_rate(
                lineage_open / max(lineage_total, 1)
            ),
            "total_population": sum(
                values[0] for values in lane_defs.values()
            ),
            "total_open_backlog": sum(
                values[1] for values in lane_defs.values()
            ),
        }
        return receipts, feature_row

    built, emit_timing = timed(build_receipts)
    receipts, feature_row = built
    telemetry = {
        "phase_timing_ns": {
            "source_parse": parse_timing,
            "consumer_scan": scan_timing,
            "graph_lineage": graph_timing,
            "receipt_emit": emit_timing,
        },
        "work_counters": {
            **scan_counters,
            "semantic_entities": len(known),
            "authority_entities": len(authority_ids),
            "domain_entities": len(domain_ids),
            "semantic_references": len(refs),
            "lineage_paths": len(lineage_paths),
            "graph_nodes": len(nodes),
            "graph_edges": len(edges),
            "emitted_receipts": len(receipts) + 1,
        },
    }
    return receipts, feature_row, telemetry


def seconds(ns: int) -> float:
    return ns / 1_000_000_000.0


def normalized_features(telemetry: dict) -> dict[str, float]:
    timing = telemetry["phase_timing_ns"]
    work = telemetry["work_counters"]
    mib = max(work["scanned_text_bytes"] / (1024.0 * 1024.0), 1e-12)
    checks = max(work["consumer_candidate_checks"], 1)
    entities = max(work["semantic_entities"], 1)
    edges = max(work["graph_edges"], 1)
    emitted = max(work["emitted_receipts"], 1)
    return {
        "parse_cpu_seconds_per_entity": seconds(
            timing["source_parse"]["cpu_ns"]
        )
        / entities,
        "scan_cpu_seconds_per_mib": seconds(
            timing["consumer_scan"]["cpu_ns"]
        )
        / mib,
        "scan_cpu_seconds_per_candidate_check": seconds(
            timing["consumer_scan"]["cpu_ns"]
        )
        / checks,
        "graph_cpu_seconds_per_edge": seconds(
            timing["graph_lineage"]["cpu_ns"]
        )
        / edges,
        "emit_cpu_seconds_per_receipt": seconds(
            timing["receipt_emit"]["cpu_ns"]
        )
        / emitted,
        "scan_wall_seconds_per_mib": seconds(
            timing["consumer_scan"]["wall_ns"]
        )
        / mib,
        "graph_wall_seconds_per_edge": seconds(
            timing["graph_lineage"]["wall_ns"]
        )
        / edges,
    }


def write_outputs(
    out: Path,
    receipts: dict[str, dict],
    feature_row: dict,
    probe: dict,
) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for lane, receipt in receipts.items():
        (out / f"{lane}.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    feature_path = out / "FEATURE_ROW.json"
    feature_path.write_text(
        json.dumps(feature_row, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    probe["feature_row_sha256"] = hashlib.sha256(
        feature_path.read_bytes()
    ).hexdigest()
    (out / "W77_PROBE_RECEIPT.json").write_text(
        json.dumps(probe, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--repeat", required=True, type=int)
    parser.add_argument("--matrix-label", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    receipts, feature_row, telemetry = build_instrumented(root, args.source_sha)
    baseline_receipts, baseline_row = w72.measure(root, args.source_sha)
    if receipts != baseline_receipts or feature_row != baseline_row:
        raise RuntimeError("W77 semantic parity failure against W72")

    probe = {
        "schema_version": PROBE_SCHEMA,
        "repository": "GBOGEB/ABACUS",
        "source_sha": args.source_sha,
        "matrix_label": args.matrix_label,
        "repeat": args.repeat,
        "probe": "w72_semantic_census_exact_source_state_phase_instrumented",
        "semantic_parity_with_w72": True,
        **telemetry,
        "runtime_sensitive_features": normalized_features(telemetry),
        "execution_state": "PASS",
        "authority": "derived_operational_analysis",
        "global_allocation_authority": False,
    }
    write_outputs(Path(args.out), receipts, feature_row, probe)
    print(json.dumps(probe, sort_keys=True))


if __name__ == "__main__":
    main()
