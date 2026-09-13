#!/usr/bin/env python3
"""Build a W75 repeat panel from three retained W74 artifact families."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def artifact_member(root: Path, artifact_id: int, member: str) -> Path:
    path = root / f"artifact-{artifact_id}" / member
    if not path.is_file():
        raise ValueError(f"missing artifact member: {path}")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--evidence-root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    manifest = load(Path(args.manifest))
    root = Path(args.evidence_root)
    rows: list[dict] = []
    seen: set[tuple[int, str]] = set()

    runs = manifest.get("runs") or []
    if len(runs) != 3:
        raise ValueError("W75 historical replay requires exactly three runs")

    for run in sorted(runs, key=lambda item: int(item["repeat"])):
        repeat = int(run["repeat"])
        run_id = int(run["run_id"])
        control_head = str(run["control_head_sha"])
        paired = run["paired_artifact"]
        paired_rows = load(
            artifact_member(
                root,
                int(paired["artifact_id"]),
                str(paired["expected_member"]),
            )
        )
        probes = {
            str(item["source_sha"]): item for item in (run.get("probes") or [])
        }
        if len(paired_rows) != 5 or len(probes) != 5:
            raise ValueError(f"repeat {repeat}: expected five paired rows and probes")

        for source in paired_rows:
            source_sha = str(source["source_sha"])
            key = (repeat, source_sha)
            if key in seen:
                raise ValueError(f"duplicate repeat/source state: {key}")
            seen.add(key)
            probe_meta = probes.get(source_sha)
            if probe_meta is None:
                raise ValueError(f"repeat {repeat}: no probe for {source_sha}")
            probe = load(
                artifact_member(
                    root,
                    int(probe_meta["artifact_id"]),
                    str(probe_meta["expected_member"]),
                )
            )
            if str(probe["source_sha"]) != source_sha:
                raise ValueError("probe/source SHA mismatch")
            if str(probe["matrix_label"]) != str(probe_meta["label"]):
                raise ValueError("probe label mismatch")
            if source.get("execution_state") != "PASS":
                raise ValueError("historical row is not PASS")
            if int(source.get("runner_id") or 0) <= 0:
                raise ValueError("historical row has no real runner")
            if int(source.get("steps_executed_total") or 0) <= 0:
                raise ValueError("historical row executed zero steps")
            evidence_ref = str(source.get("evidence_reference") or "")
            if f"/actions/runs/{run_id}/jobs" not in evidence_ref:
                raise ValueError("paired row does not bind declared run")

            intrinsic = float(probe["probe_execute_seconds"])
            wall = float(source["execute_seconds_total"])
            item = dict(source)
            item.update(
                {
                    "repeat": repeat,
                    "control_head_sha": control_head,
                    "source_run_id": run_id,
                    "paired_artifact_id": int(paired["artifact_id"]),
                    "paired_artifact_digest": str(paired["digest"]),
                    "probe_artifact_id": int(probe_meta["artifact_id"]),
                    "probe_artifact_digest": str(probe_meta["digest"]),
                    "probe_execute_seconds": intrinsic,
                    "orchestration_overhead_seconds": round(max(wall - intrinsic, 0.0), 6),
                }
            )
            rows.append(item)

    if len(rows) != 15 or len(seen) != 15:
        raise ValueError("W75 requires exactly 15 unique repeat/source rows")
    by_repeat = {repeat: 0 for repeat in (1, 2, 3)}
    source_shas = set()
    for row in rows:
        by_repeat[int(row["repeat"])] += 1
        source_shas.add(str(row["source_sha"]))
    if by_repeat != {1: 5, 2: 5, 3: 5} or len(source_shas) != 5:
        raise ValueError("W75 panel balance must be 3 repeats x 5 exact SHAs")

    rows.sort(key=lambda row: (int(row["repeat"]), str(row["source_sha"])))
    Path(args.out).write_text(
        json.dumps(rows, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "rows": len(rows),
                "distinct_source_shas": len(source_shas),
                "repeats": by_repeat,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
