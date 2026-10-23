"""Offline integrity check for an evidence-recovery handover pack.

Errors (exit 1) mean the pack is internally inconsistent. Warnings are
evidence-quality gaps that should be carried forward, not hidden.

Usage: python -I ci/verify_handover.py [pack_root]
"""
import json
import re
import sys
from pathlib import Path

SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
RUN_KEYS = ("repo", "source_sha", "checkout_kind", "workflow", "run", "attempt",
            "job", "artifact", "terminal", "conclusion")
UNKNOWN = (None, "UNKNOWN")


def load(path):
    rows = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                errors.append(f"{path.name}:{n}: invalid JSON ({e})")
    return rows


def check_sha(where, value, pattern=SHA40):
    if value in UNKNOWN or (isinstance(value, str) and value.startswith("UNKNOWN")):
        return
    if not isinstance(value, str) or not pattern.match(value):
        errors.append(f"{where}: malformed hash {value!r}")


errors, warnings = [], []
root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1])
tel = root / "telemetry"
ledger = load(tel / "evidence_ledger.jsonl")
roots = load(tel / "causal_roots.jsonl")
cohorts = load(tel / "coverage_cohorts.jsonl")

ids = {r["id"] for r in ledger}
if len(ids) != len(ledger):
    errors.append("evidence_ledger: duplicate ids")

artifact_digest = {}
for r in ledger:
    where = f"ledger {r['id']}"
    if r.get("kind") == "repo_state":
        check_sha(where, r.get("main_sha"))
        continue
    for k in RUN_KEYS:
        if k not in r:
            errors.append(f"{where}: missing key {k!r}")
    check_sha(where, r.get("source_sha"))
    check_sha(where, r.get("checkout_sha"))
    check_sha(where, r.get("prev_source_sha"))
    if r.get("artifact_sha256") is not None:
        check_sha(where, r["artifact_sha256"], SHA256)
        if r.get("digest_source") != "verified":
            warnings.append(f"{where}: artifact {r['artifact']} digest is {r.get('digest_source')}, not re-hashed")
    if r.get("artifact") is not None:
        prev = artifact_digest.setdefault(r["artifact"], r.get("artifact_sha256"))
        if prev != r.get("artifact_sha256"):
            errors.append(f"{where}: artifact {r['artifact']} has conflicting digests")
    if r.get("checkout_kind") == "exact_head" and r.get("checkout_sha") not in (None, r.get("source_sha")):
        errors.append(f"{where}: exact_head but checkout_sha != source_sha")
    if r.get("terminal") is not True and r.get("conclusion") not in ("queued", "in_progress", "action_required"):
        errors.append(f"{where}: non-terminal row with terminal conclusion {r.get('conclusion')!r}")
    if r.get("attempt") is None:
        warnings.append(f"{where}: run {r['run']} attempt unknown")
    elif r["attempt"] > 1 and (r.get("attempt1_conclusion") in UNKNOWN
                               or str(r.get("attempt1_conclusion")).startswith("UNKNOWN")):
        warnings.append(f"{where}: run {r['run']} attempt {r['attempt']} - attempt-1 outcome at same SHA unrecorded (rerun-pass risk)")
    if r.get("superseded_by") and r["superseded_by"] not in ids:
        errors.append(f"{where}: superseded_by {r['superseded_by']} not in ledger")
    for rid in r.get("roots", []):
        if rid not in {x["id"] for x in roots}:
            errors.append(f"{where}: references unknown root {rid}")

for c in roots:
    where = f"root {c['id']}"
    for e in c.get("evidence", []) + c.get("displacement_evidence", []):
        if e not in ids:
            errors.append(f"{where}: references unknown evidence {e}")
    if c.get("status") == "displaced":
        if c.get("displaced_at") in UNKNOWN:
            errors.append(f"{where}: displaced without displaced_at")
        elif c.get("displaced_at") == c.get("first_red_at"):
            errors.append(f"{where}: displaced at the same SHA as first-red (not source-changing)")
        check_sha(where, c.get("displaced_at"))
    if c.get("accepted_closure"):
        warnings.append(f"{where}: accepted_closure=true - confirm a governed merge backs it")
    if c.get("status") in ("open", "suspected"):
        warnings.append(f"{where}: {c['status']} - {c['summary']}")

by_id = {c["id"]: c for c in cohorts if "id" in c}
for c in by_id.values():
    where = f"cohort {c['id']}"
    check_sha(where, c.get("source_sha"))
    base = by_id.get(c.get("delta_vs"))
    if c.get("delta_vs") and base is None:
        errors.append(f"{where}: delta_vs {c['delta_vs']} unknown")
    elif base:
        for denom in ("statements", "branches"):
            if c.get(denom) != base.get(denom):
                errors.append(f"{where}: {denom} denominator differs from {base['id']} - delta not comparable")
        actual = c["covered_statements"] - base["covered_statements"]
        if actual != c.get("delta_statements"):
            errors.append(f"{where}: delta_statements {c.get('delta_statements')} != computed {actual}")
for rule in (c for c in cohorts if c.get("rule") == "no_accumulation"):
    for cid in rule["cohorts"]:
        if cid not in by_id:
            errors.append(f"no_accumulation rule references unknown cohort {cid}")

print(f"pack: {root}")
print(f"ledger rows: {len(ledger)}  roots: {len(roots)}  cohorts: {len(by_id)}")
for w in warnings:
    print("WARN ", w)
for e in errors:
    print("ERROR", e)
print(f"{len(errors)} error(s), {len(warnings)} warning(s)")
sys.exit(1 if errors else 0)
