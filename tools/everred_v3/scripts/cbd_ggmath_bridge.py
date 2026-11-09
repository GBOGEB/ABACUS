"""Source-bound exploratory PCA provider request for canonical GBOGEB/gg_MATH.

This adapter prepares an incidence matrix and a gg_MATH worker contract. It
does NOT execute or validate PCA, calculate inferential CIs, or confer
engineering/root/admission authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value):
    return hashlib.sha256(canonical(value).encode("ascii")).hexdigest()


def build(summary, source_sha):
    require(
        isinstance(source_sha, str)
        and len(source_sha) == 40
        and all(ch in "0123456789abcdef" for ch in source_sha),
        "exact source SHA required",
    )
    require(summary.get("repository") == "GBOGEB/ABACUS", "repository mismatch")
    require(
        summary.get("schema") == "abacus.everred.cbd.portfolio_projection.v1",
        "schema mismatch",
    )
    require(
        summary.get("safety", {}).get("merge_admission") == "HOLD"
        and summary["safety"].get("security_waiver") is False,
        "source admission must remain HOLD",
    )
    families = summary.get("families")
    require(isinstance(families, list) and families, "families missing")
    names = [family.get("workflow") for family in families]
    require(
        all(isinstance(n, str) and n.strip() for n in names)
        and len(names) == len(set(names)),
        "non-unique workflow dimensions",
    )
    rows = set()
    for family in families:
        require(family.get("causal_root_id") is None, "forged root confirmation")
        group = family.get("affected_prs")
        require(
            isinstance(group, list) and all(type(x) is int and x > 0 for x in group),
            "invalid affected PR list",
        )
        rows.update(group)
    labels = [[p] for p in sorted(rows)]
    # Historical N0 alias: #2005 and #2010 share the same source head.
    if 2005 in rows and 2010 in rows:
        labels = [x for x in labels if x[0] not in (2005, 2010)]
        labels.append([2005, 2010])
        labels.sort(key=lambda x: x[0])
    matrix = []
    for label in labels:
        matrix.append(
            [
                int(any(p in family["affected_prs"] for p in label))
                for family in families
            ]
        )
    require(len(matrix) > 2 and len(names) > 1, "insufficient exploratory dimensions")
    source = {
        "schema": "abacus.cbd.ggmath.binary_incidence.v1",
        "observation_scope": "HISTORICAL_FIRST_PAGE_FAILURE_PRESENCE",
        "repository": summary["repository"],
        "source_sha": source_sha,
        "main_sha_at_observation": summary["main_sha_at_observation"],
        "cohort_ids": labels,
        "workflow_features": names,
        "values": matrix,
        "n_source_head_proxy_groups": len(labels),
        "p_workflow_features": len(names),
        "known_aliases_collapsed": (
            [[2005, 2010]] if 2005 in rows and 2010 in rows else []
        ),
        "sampling_complete": False,
        "causal_root_labels": None,
        "absence_means": "NOT_IN_FIRST_PAGE_FAILURE_SAMPLE",
        "authority_transfer": False,
    }
    task = {
        "schema": "gbogeb.skill.invoke.v1",
        "skill": "math",
        "task_id": "ABACUS-CBD-ggMATH-" + digest(source)[:12],
        "source_repo": summary["repository"],
        "source_ref": source_sha,
        "topic": "PCA",
        "maturity": "ADVANCED",
        "inputs": {
            "canonical_provider": "GBOGEB/gg_MATH",
            "incidence_schema": source["schema"],
            "incidence_sha256": digest(source),
            "matrix_dimensions": [len(labels), len(names)],
            "method": "centered SVD; standardized sensitivity on nonrare columns",
            "uncertainty": "head-cluster bootstrap for exploratory stability",
            "identifiability": "noncausal; source-head alias and CI fanout acknowledged",
            "providers_invoked": False,
        },
        "authority_transfer": False,
    }
    return source, task


def write(source, task, dest):
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    output = {
        "ggmath-incidence.json": canonical(source) + "\n",
        "ggmath-request.json": canonical(task) + "\n",
        "ggmath-status.json": canonical(
            {
                "schema": "abacus.cbd.ggmath.status.v1",
                "request_sha256": digest(task),
                "provider_executed": False,
                "pca_new_result": None,
                "causal_root_inference": None,
                "merge_admission": "HOLD",
                "authority_transfer": False,
            }
        )
        + "\n",
    }
    for key, value in output.items():
        (dest / key).write_text(value, encoding="utf-8")
    (dest / "sha256.json").write_text(
        canonical(
            {
                k: hashlib.sha256(v.encode("utf-8")).hexdigest()
                for k, v in sorted(output.items())
            }
        )
        + "\n",
        encoding="utf-8",
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    source, task = build(
        json.loads(args.summary.read_text(encoding="utf-8")), args.source_sha
    )
    write(source, task, args.output_dir)
    print(
        canonical(
            {
                "provider": "GBOGEB/gg_MATH",
                "invoked": False,
                "n": source["n_source_head_proxy_groups"],
                "p": source["p_workflow_features"],
                "admission": "HOLD",
            }
        )
    )


if __name__ == "__main__":
    main()
