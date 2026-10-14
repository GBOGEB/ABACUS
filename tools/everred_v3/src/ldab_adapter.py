"""Observe canonical ABACUS bd.ldab.joined.census.v1 without assigning root authority."""
from __future__ import annotations

import hashlib
import json

from four_planes import Source, demand, ldab_receipt


def consume_bd_ldab(report: dict, *, expected_source: Source) -> dict:
    demand(isinstance(report, dict) and report.get("schema") == "bd.ldab.joined.census.v1",
           "canonical BD/LDAB schema required")
    demand(report.get("merge_admission") == "HOLD" and report.get("authority_transfer") is False
           and report.get("security_waiver") is False, "canonical admission boundary violated")
    scope = report.get("scope")
    demand(isinstance(scope, dict), "missing canonical scope")
    fields = {"repository": expected_source.repository, "head_sha": expected_source.source_sha,
              "run_id": expected_source.run_id, "job_id": expected_source.job_id}
    demand(all(scope.get(k) == v for k, v in fields.items()), "canonical LDAB scope does not match native source")
    rows = report.get("roots")
    unlinked = report.get("unlinked_debug_receipts")
    demand(isinstance(rows, list) and isinstance(unlinked, list), "invalid root/debug arrays")
    ids = set()
    bandit = []
    ci = []
    for row in rows:
        demand(isinstance(row, dict) and isinstance(row.get("root_id"), str), "root identity invalid")
        root = row["root_id"]
        demand(root not in ids, "duplicate canonical root")
        ids.add(root)
        category = row.get("category")
        demand(category in ("BANDIT", "CI"), "root category unknown")
        observations = row.get("observations")
        demand(isinstance(observations, list), "root observations missing")
        for obs in observations:
            demand(isinstance(obs, dict), "malformed root observation")
            # Cross-repo data is not silently linked into local authority.
            if obs.get("repository") != expected_source.repository or obs.get("source_sha") != expected_source.source_sha:
                continue
            demand(type(obs.get("run_id")) is int and type(obs.get("job_id")) is int,
                   "root run/job identity invalid")
        if category == "CI":
            ci.append(root)
            continue
        fp = row.get("fingerprint")
        demand(isinstance(fp, str) and len(fp) == 64 and all(c in "0123456789abcdef" for c in fp),
               "invalid Bandit fingerprint")
        bandit.append(ldab_receipt(expected_source, {
            "root_id": root, "finding_fingerprint": fp, "owner": row.get("owner_lane"),
            "disposition": "HYPOTHESIS", "scope": "canonical-observation-only"}))
    metrics = report.get("metrics")
    demand(isinstance(metrics, dict) and metrics.get("full_bandit_unique") == len(bandit),
           "Bandit denominator mismatches canonical source")
    return {"schema": "abacus.everred.ldab.canonical.bridge.v1",
            "source_binding": expected_source.binding(),
            "canonical_sha256": hashlib.sha256(json.dumps(report, sort_keys=True,
                                                         separators=(",", ":")).encode()).hexdigest(),
            "bandit_candidates": bandit, "ci_candidate_ids": sorted(ci),
            "unlinked_debug_count": len(unlinked),
            "causal_roots_confirmed": None, "merge_admission": "HOLD",
            "authority_transfer": False, "security_disposition": "PENDING_INDEPENDENT_REVIEW"}
