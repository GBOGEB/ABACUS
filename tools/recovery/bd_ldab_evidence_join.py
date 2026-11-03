"""Evidence-only BD/LDAB join: no matching by guesswork or promotion."""

import argparse
import json
from pathlib import Path


def join(roots: dict, observations: dict) -> dict:
    if not isinstance(roots.get("roots"), list) or not isinstance(
        observations.get("observations"), list
    ):
        raise ValueError("canonical arrays required")
    known = {
        x["root_id"]
        for x in roots["roots"]
        if isinstance(x, dict) and isinstance(x.get("root_id"), str)
    }
    if len(known) != len(roots["roots"]):
        raise ValueError("invalid or duplicate roots")
    rows = []
    for item in observations["observations"]:
        if not isinstance(item, dict):
            raise ValueError("observation must be object")
        root_id = item.get("root_id")
        verified = bool(
            root_id in known
            and item.get("commit_sha")
            and item.get("run_id")
            and item.get("job_id")
            and item.get("evidence_uri")
            and item.get("causal_link_verified") is True
        )
        rows.append(
            {
                "root_id": root_id if root_id in known else None,
                "fingerprint": item.get("fingerprint"),
                "evidence_attached": verified,
                "closure_credit": False,
            }
        )
    return {
        "schema": "bd.ldab.read_only.join.v1",
        "observations": rows,
        "root_closures": None,
        "admission": "HOLD",
        "security_waiver": False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("roots", type=Path)
    p.add_argument("observations", type=Path)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    a.out.write_text(
        json.dumps(
            join(
                json.loads(a.roots.read_text()), json.loads(a.observations.read_text())
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
