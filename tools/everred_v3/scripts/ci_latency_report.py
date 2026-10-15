"""Collect exact-source native CI timings into an independent JSON receipt."""

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from ci_latency import SCHEMA, cohort, digest_receipt, measure_run
from native_ingest import GitHubReadOnly


def run(args):
    if not args.run_id or len(args.run_id) > 30:
        raise ValueError("provide between one and 30 native run IDs")
    if len(set(args.run_id)) != len(args.run_id):
        raise ValueError("duplicate native run IDs")
    reader = GitHubReadOnly()
    evidence = []
    for run_id in args.run_id:
        run, jobs = reader.run_and_jobs(args.repo, run_id, args.sha)
        evidence.append(measure_run(run, jobs, args.repo, args.sha))
    result = {
        "schema": SCHEMA + ".batch",
        "repository": args.repo,
        "source_sha": args.sha,
        "run_receipts": evidence,
        "cohort": cohort(evidence),
        "security_waiver": False,
        "authority_transfer": False,
        "merge_admission": "HOLD",
    }
    result["sha256"] = digest_receipt(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "runs": len(evidence),
                "state": result["cohort"]["status"],
                "source_sha": args.sha,
                "batch_digest": result["sha256"],
            },
            sort_keys=True,
        )
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--run-id", type=int, required=True, action="append")
    parser.add_argument("--output", type=pathlib.Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
