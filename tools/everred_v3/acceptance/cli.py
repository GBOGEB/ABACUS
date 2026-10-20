"""Read-only deterministic builder for machine and human acceptance debt receipts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import core, graph, render, telemetry


def load_events(paths):
    observations = []
    for path in paths:
        p = Path(path)
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                observations.append(json.loads(line))
    return observations


def build(contract, contexts, events, output, local_testflight=None):
    core.validate_contract(contract)
    core.validate_contexts(contexts)
    observed = core.dedupe_events(events, core.validate_contract(contract)[0])
    clocks = sorted({0, 1, 2} | {row["pulse"] for row in observed})
    require_three = clocks[:3] == [0, 1, 2]
    core.require(require_three, "first three pulse clocks missing")
    waves = []
    for clock in clocks:
        subset = [row for row in observed if row["pulse"] <= clock]
        projection = core.project(contract, contexts, subset)
        dag = graph.graph_projection(projection)
        graph.check_graph_acyclic(dag)
        deps = [edge for edge in dag["edges"] if edge["kind"] == "DEPENDS_ON"]
        waves.append({
            "pulse": clock, "projection": projection,
            "dependency_hash": core.digest(deps),
            "graph_hash": core.digest(dag),
            "evidence_class": "LOCAL_REPLAY_OF_PRIOR_SOURCE_BOUND_OBSERVATIONS",
        })
    result = waves[-1]["projection"]
    dag = graph.graph_projection(result)
    sipoc = graph.sipoc(result)
    history = telemetry.analyze(waves)
    hashes = render.write_bundle(output, result, dag, sipoc, history, local_testflight)
    return {"schema": "codepurple.acceptance.build_receipt.v1",
            "input_contract_sha256": core.digest(contract),
            "input_contexts_sha256": core.digest(contexts),
            "input_events_sha256": core.digest(observed),
            "output_hash_manifest_sha256": core.digest(hashes),
            "metrics": result["metrics"], "graph_metrics": dag["metrics"],
            "temporal_metrics": history["metrics"],
            "independent_admission": "HOLD",
            "canonical_ledger_written": False, "source_mutated": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--contexts", required=True, type=Path)
    parser.add_argument("--events", required=True, type=Path, nargs="+")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--local-testflight", type=Path)
    args = parser.parse_args(argv)
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    contexts = json.loads(args.contexts.read_text(encoding="utf-8"))
    events = load_events(args.events)
    local = (json.loads(args.local_testflight.read_text(encoding="utf-8"))
             if args.local_testflight else None)
    result = build(contract, contexts, events, args.out, local)
    (args.out / "build-receipt.json").write_text(core.canonical(result) + "\n",
                                                  encoding="utf-8")
    print(core.canonical(result))


if __name__ == "__main__":
    main()
