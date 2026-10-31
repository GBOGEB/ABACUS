#!/usr/bin/env python3
"""LOSSLESS_HANDOVER_V2: reproducible, evidence-bound operational capsules.

No network access; a PASS field is checked for local consistency, not independently
verified against GitHub. The generator cannot attest complete-chat preservation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path, PurePosixPath

from jsonschema import Draft202012Validator, FormatChecker

PROTOCOL = "LOSSLESS_HANDOVER_V2"
CORE_FILES = (
    "state.json",
    "handover.md",
    "dropin.md",
    "comparisons.json",
    "unknowns.json",
    "qa_report.json",
)
PROTOCOL_FILES = (
    "build_handover.py",
    "handover_input.schema.json",
    "process_spec.json",
    "requirements.txt",
)
SHA = re.compile(r"^[0-9a-f]{40}$")
RISKY_SECRET = re.compile(
    r"(?i)(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"sk-proj-[A-Za-z0-9_-]{20,}|authorization\s*:\s*bearer\s+\S+|"
    r"[?&](?:token|access_token|sig|signature|X-Amz-Signature)=)"
)


def canonical(obj: object) -> bytes:
    return (
        json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pct(n: int, d: int) -> str:
    return f"{(Decimal(n) * 100 / Decimal(d)):.2f}%"


def safe_md(text: object) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def valid_relpath(name: str) -> PurePosixPath:
    if "\\" in name or name.startswith("/") or "\x00" in name:
        raise ValueError(f"Unsafe archive path: {name!r}")
    path = PurePosixPath(name)
    if any(x in ("..", ".", "") for x in path.parts) or str(path) != name:
        raise ValueError(f"Unsafe archive path: {name!r}")
    if len(path.parts) < 2 or path.parts[0] != "raw":
        raise ValueError("Raw paths must start with raw/ and contain a filename")
    return path


def must_unique(rows: list, group: str) -> dict:
    ids = [row["id"] for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError(f"Duplicate {group} ID")
    return {row["id"]: row for row in rows}


def validate_graph(actions: dict) -> None:
    flags: dict[str, int] = {}

    def visit(node: str):
        if flags.get(node) == 1:
            raise ValueError("Action dependency cycle at " + node)
        if flags.get(node) == 2:
            return
        flags[node] = 1
        for dep in actions[node]["depends_on"]:
            if dep not in actions:
                raise ValueError(f"Action {node} references unknown dependency {dep}")
            visit(dep)
        flags[node] = 2

    for node in actions:
        visit(node)
    orders = [row["order"] for row in actions.values()]
    if len(orders) != len(set(orders)):
        raise ValueError("Duplicate action order")
    for row in actions.values():
        for dep in row["depends_on"]:
            if actions[dep]["order"] >= row["order"]:
                raise ValueError(
                    "Dependency cannot run after dependent action: " + row["id"]
                )


def validate_admission_gates(authority: dict, gates: dict) -> None:
    """Fail closed when a non-HOLD decision has no required admission evidence."""
    if authority["merge_decision"] == "HOLD":
        return
    required = [g for g in gates.values() if g["required_for_admission"]]
    if not required:
        raise ValueError("Admission requires at least one required gate")
    if (
        authority["effective_branch_protection"] != "EFFECTIVE"
        or authority["independent_approval"] != "ESTABLISHED"
        or any(g["status"] != "PASS" for g in required)
    ):
        raise ValueError(
            "Admission cannot proceed without protected main, review and required PASS gates"
        )


def semantic_validate(s: dict, raw_base: Path) -> None:
    if s["protocol"] != PROTOCOL:
        raise ValueError("Unsupported protocol")
    try:
        dt = datetime.fromisoformat(
            s["snapshot"]["captured_at_utc"].replace("Z", "+00:00")
        )
        if dt.utcoffset() != timezone.utc.utcoffset(dt):
            raise ValueError("Snapshot time must be UTC")
    except (ValueError, TypeError) as exc:
        raise ValueError("Snapshot must contain valid UTC capture time") from exc
    # Fail rather than accidentally embedding common credential-bearing URLs.
    if RISKY_SECRET.search(json.dumps(s)):
        raise ValueError("Potential secret/signed URL in capsule input; redact first")

    head = s["subject"]["head_sha"]
    evidence = must_unique(s["evidence"], "evidence")
    metrics = must_unique(s["metrics"], "metric")
    gates = must_unique(s["gates"], "gate")
    blockers = must_unique(s["blockers"], "blocker")
    actions = must_unique(s["actions"], "action")
    must_unique(s["unknowns"], "unknown")
    must_unique(s["targets"], "target")
    must_unique(s["comparisons"], "comparison")
    must_unique(s["decisions"], "decision")
    validate_graph(actions)
    for row in s["actions"]:
        for b in row["blocked_by"]:
            if b not in blockers:
                raise ValueError("Action references absent blocker " + b)

    raw_by_evidence = {}
    for row in s["raw_sources"]:
        path = valid_relpath(row["path"])
        if row["evidence_id"] not in evidence:
            raise ValueError("Raw source references unknown evidence")
        source = (raw_base / str(path)).resolve()
        if not source.is_relative_to(raw_base.resolve()):
            raise ValueError("Raw source escapes the input directory")
        if not source.is_file():
            raise ValueError("Raw source unavailable: " + str(source))
        if sha256(source.read_bytes()) != row["sha256"]:
            raise ValueError("Raw source hash mismatch: " + str(source))
        if row["path"] in raw_by_evidence:
            raise ValueError("Duplicate archive source path")
        raw_by_evidence[row["path"]] = row
        ev = evidence[row["evidence_id"]]
        if ev["sha256"] is not None and ev["sha256"] != row["sha256"]:
            raise ValueError("Evidence vs raw file hash mismatch: " + ev["id"])

    # Derived-fact assertions bind numbers to archived native JSON, not mere URLs.
    def resolve_pointer(doc, pointer):
        if not pointer.startswith("/"):
            raise ValueError("JSON pointer must start with '/'")
        for part in pointer.split("/")[1:]:
            part = part.replace("~1", "/").replace("~0", "~")
            if isinstance(doc, dict):
                doc = doc[part]
            elif isinstance(doc, list):
                if not part.isdecimal():
                    raise ValueError("JSON pointer uses nonnumeric list index")
                doc = doc[int(part)]
            else:
                raise ValueError("JSON pointer traverses non-container")
        return doc

    equality_ids = set()
    for entry in s["byte_equalities"]:
        if entry["id"] in equality_ids:
            raise ValueError("Duplicate byte equality assertion")
        equality_ids.add(entry["id"])
        for p in (entry["left_path"], entry["right_path"]):
            valid_relpath(p)
            if p not in raw_by_evidence:
                raise ValueError("Equality requires archived source " + p)
        if (raw_base / entry["left_path"]).read_bytes() != (
            raw_base / entry["right_path"]
        ).read_bytes():
            raise ValueError("Byte equality failed: " + entry["id"])
    numeric_ids = set()
    coverage_by_metric = {}
    for entry in s["numeric_bindings"]:
        if entry["id"] in numeric_ids:
            raise ValueError("Duplicate numeric binding assertion")
        numeric_ids.add(entry["id"])
        p = entry["source_path"]
        valid_relpath(p)
        if p not in raw_by_evidence:
            raise ValueError("Numeric binding requires archived source " + p)
        if entry["metric_id"] not in {m["id"] for m in s["metrics"]}:
            raise ValueError("Numeric binding references missing metric")
        m = next(m for m in s["metrics"] if m["id"] == entry["metric_id"])
        if m["state"] == "UNKNOWN":
            raise ValueError("Cannot bind unknown measurement")
        source_ev = next(
            ev for ev in s["evidence"] if ev["id"] == raw_by_evidence[p]["evidence_id"]
        )
        if (
            source_ev["source_sha"] != m["source_sha"]
            or source_ev["id"] not in m["evidence_ids"]
        ):
            raise ValueError(
                "Numeric source not SHA/evidence-bound to metric: " + entry["id"]
            )
        if entry["field"] in coverage_by_metric.setdefault(m["id"], set()):
            raise ValueError("Duplicate binding to numeric field " + m["id"])
        coverage_by_metric[m["id"]].add(entry["field"])
        try:
            doc = json.loads((raw_base / p).read_bytes())
            got = resolve_pointer(doc, entry["json_pointer"])
        except (
            ValueError,
            TypeError,
            KeyError,
            IndexError,
            json.JSONDecodeError,
        ) as exc:
            raise ValueError("Invalid numeric source pointer " + entry["id"]) from exc
        if entry["operation"] == "LIST_LENGTH":
            if not isinstance(got, list):
                raise ValueError("LIST_LENGTH source not list")
            got = len(got)
        if isinstance(got, bool) or not isinstance(got, (int, float)):
            raise ValueError("Claim binding did not resolve to a number")
        if got != m[entry["field"]]:
            raise ValueError(
                "Numeric measurement disagrees with raw source: " + entry["id"]
            )
    if s["snapshot"]["fidelity_mode"] == "EVIDENCE_ARCHIVE":
        for m in s["metrics"]:
            if m["state"] != "MEASURED":
                continue
            required = (
                {"numerator", "denominator"}
                if m["measure_type"] == "RATIO"
                else {"value"}
            )
            if coverage_by_metric.get(m["id"], set()) != required:
                raise ValueError(
                    "EVIDENCE_ARCHIVE missing measured numeric source bindings: "
                    + m["id"]
                )
    if s["snapshot"]["fidelity_mode"] == "EVIDENCE_ARCHIVE" and not raw_by_evidence:
        raise ValueError("EVIDENCE_ARCHIVE requires at least one verified source")
    for ev in evidence.values():
        if ev["observation"] == "LOCAL_BYTES_VERIFIED":
            if not ev["sha256"]:
                raise ValueError(
                    "Archived evidence requires source digest: " + ev["id"]
                )
            if not any(v["evidence_id"] == ev["id"] for v in raw_by_evidence.values()):
                raise ValueError(
                    "ARCHIVED evidence lacks matching raw file: " + ev["id"]
                )
        if ev["observation"] in ("REMOTE_OBSERVED", "LOCAL_BYTES_VERIFIED"):
            if not ev["uri"] or not ev["source_sha"]:
                raise ValueError(
                    "Observed/archived evidence requires URI and SHA: " + ev["id"]
                )
        if ev["observation"] == "UNVERIFIED" and ev["sha256"]:
            raise ValueError("Do not provide a verified digest for UNVERIFIED evidence")

    def check_refs(
        ids: list[str], source_sha: str | None, label: str, require_native: bool = False
    ) -> None:
        if not ids:
            raise ValueError(label + " requires evidence ID(s)")
        for ident in ids:
            if ident not in evidence:
                raise ValueError(label + " references absent evidence " + ident)
            ev = evidence[ident]
            if ev["source_sha"] != source_sha:
                raise ValueError(label + " evidence has different SHA " + ident)
            if ev["observation"] not in ("REMOTE_OBSERVED", "LOCAL_BYTES_VERIFIED"):
                raise ValueError(
                    label + " relies on unverified/user-only evidence " + ident
                )
        if require_native and not any(
            evidence[i]["kind"] in ("WORKFLOW_RUN", "WORKFLOW_JOB", "ARTIFACT")
            for i in ids
        ):
            raise ValueError(label + " needs native CI/producer evidence")

    for m in metrics.values():
        n, d, val = m["numerator"], m["denominator"], m["value"]
        st = m["state"]
        if st == "UNKNOWN":
            if (
                n is not None
                or d is not None
                or val is not None
                or m["source_sha"] is not None
                or m["evidence_ids"]
            ):
                raise ValueError(
                    "UNKNOWN metric cannot contain measurements/proofs: " + m["id"]
                )
            if not m["missing_reason"]:
                raise ValueError("UNKNOWN metric missing reason: " + m["id"])
        else:
            if not m["source_sha"]:
                raise ValueError("Measured/historical metric missing source SHA")
            if st == "MEASURED" and m["source_sha"] != head:
                raise ValueError("Current metric carries other SHA: " + m["id"])
            check_refs(m["evidence_ids"], m["source_sha"], "metric " + m["id"])
            if m["missing_reason"] is not None:
                raise ValueError("Measured metric cannot claim missing reason")
            if m["measure_type"] == "RATIO":
                if n is None or d is None or not (0 <= n <= d) or val is not None:
                    raise ValueError("Invalid ratio numerator/denominator: " + m["id"])
            elif n is not None or d is not None or val is None:
                raise ValueError("Invalid count metric fields: " + m["id"])
    for t in s["targets"]:
        if (
            t["metric_id"] not in metrics
            or metrics[t["metric_id"]]["measure_type"] != "RATIO"
        ):
            raise ValueError("Target must address a ratio metric " + t["id"])
    for c in s["comparisons"]:
        if c["before_metric_id"] not in metrics or c["after_metric_id"] not in metrics:
            raise ValueError("Comparison references missing metric: " + c["id"])
        if c["before_metric_id"] == c["after_metric_id"]:
            raise ValueError("Comparison cannot compare identical metric ID")
    for g in gates.values():
        st = g["status"]
        if (
            g["run_id"] is not None
            and g["evidence_ids"]
            and not any(evidence[i]["run_id"] == g["run_id"] for i in g["evidence_ids"])
        ):
            raise ValueError("Gate run ID disagrees with cited evidence: " + g["id"])
        if st == "PASS":
            if not g["source_sha"]:
                raise ValueError("PASS gate lacks source SHA: " + g["id"])
            if g["scope"] == "EXACT_HEAD" and g["source_sha"] != head:
                raise ValueError("PASS gate is not bound to latest head: " + g["id"])
            if (
                g["scope"] == "MAIN"
                and g["source_sha"] != s["subject"]["default_branch_sha"]
            ):
                raise ValueError("MAIN PASS gate is not main-bound: " + g["id"])
            check_refs(
                g["evidence_ids"],
                g["source_sha"],
                "PASS gate " + g["id"],
                require_native=g["scope"] not in ("INDEPENDENT_AUTHORITY",),
            )
        if st == "UNKNOWN" and (g["source_sha"] or g["evidence_ids"] or g["run_id"]):
            raise ValueError("UNKNOWN gate must not imply an observed run: " + g["id"])
        for ident in g["evidence_ids"]:
            if ident not in evidence:
                raise ValueError("Unknown gate evidence ID " + ident)
    for b in blockers.values():
        if b["disposition"] == "RESOLVED":
            check_refs(
                b["evidence_ids"], b["source_sha"], "resolved blocker " + b["id"]
            )
        for ident in b["evidence_ids"]:
            if ident not in evidence:
                raise ValueError("Unknown blocker evidence ID " + ident)
        for ident in b["gate_ids"]:
            if ident not in gates:
                raise ValueError("Unknown linked gate " + ident)
    for d in s["decisions"]:
        for ident in d["evidence_ids"]:
            if ident not in evidence:
                raise ValueError("Unknown decision evidence ID " + ident)
    authority = s["authority"]
    if authority["security_waiver"] or authority["authority_transfer"]:
        raise ValueError(
            "No security waiver or authority transfer admitted by this protocol"
        )
    if authority["merged"] != (authority["merge_decision"] == "MERGED"):
        raise ValueError("merged=true requires MERGED decision, and vice versa")
    validate_admission_gates(authority, gates)


def validate_input(s: dict, schema: dict, raw_base: Path) -> None:
    Draft202012Validator.check_schema(schema)
    errs = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(s),
        key=lambda x: (list(map(str, x.absolute_path)), x.message),
    )
    if errs:
        first = errs[0]
        raise ValueError(
            "SCHEMA INVALID /" + "/".join(map(str, first.path)) + ": " + first.message
        )
    semantic_validate(s, raw_base)


def metric_string(m: dict) -> str:
    if m["state"] == "UNKNOWN":
        return "UNKNOWN (" + m["missing_reason"] + ")"
    if m["measure_type"] == "COUNT":
        return f"{m['value']} {m['unit']}"
    return (
        f"{m['numerator']}/{m['denominator']} = {pct(m['numerator'], m['denominator'])}"
    )


def comparability(before: dict, after: dict, label: str, cid: str) -> dict:
    row = {
        "id": cid,
        "label": label,
        "before_metric_id": before["id"],
        "after_metric_id": after["id"],
        "status": "INELIGIBLE",
        "reasons": [],
        "before": metric_string(before),
        "after": metric_string(after),
        "delta_covered": None,
        "delta_eligible": None,
        "delta_percentage_points": None,
        "denominator_changed": None,
    }
    if before["state"] == "UNKNOWN" or after["state"] == "UNKNOWN":
        row["reasons"].append("Missing numerator/denominator")
        return row
    if before["measure_type"] != "RATIO" or after["measure_type"] != "RATIO":
        row["reasons"].append("Ratio comparison required")
        return row
    a, b = before["basis"], after["basis"]
    for k in ("scope_id", "paths", "unit_definition", "instrumentor", "selection"):
        if a[k] != b[k]:
            row["reasons"].append("Different " + k)
    for k in ("instrumentor_version", "configuration_sha256"):
        if not a[k] or not b[k]:
            row["reasons"].append(k + " not proven for both measurements")
        elif a[k] != b[k]:
            row["reasons"].append("Different " + k)
    if not row["reasons"]:
        row["status"] = "COMPARABLE"
        row["delta_covered"] = after["numerator"] - before["numerator"]
        row["delta_eligible"] = after["denominator"] - before["denominator"]
        row["delta_percentage_points"] = round(
            100 * after["numerator"] / after["denominator"]
            - 100 * before["numerator"] / before["denominator"],
            4,
        )
        row["denominator_changed"] = after["denominator"] != before["denominator"]
    return row


def compute_comparisons(s: dict, previous: dict | None = None) -> dict:
    ms = {x["id"]: x for x in s["metrics"]}
    rows = [
        comparability(
            ms[c["before_metric_id"]], ms[c["after_metric_id"]], c["label"], c["id"]
        )
        for c in s["comparisons"]
    ]
    if previous:
        prev = {x["id"]: x for x in previous["metrics"]}
        for ident in sorted(set(prev) & set(ms)):
            if ms[ident]["state"] == "HISTORICAL":
                continue
            rows.append(
                comparability(
                    prev[ident], ms[ident], "Iteration " + ident, "ITERATION." + ident
                )
            )
    return {
        "schema": "handover.comparisons.v2",
        "snapshot_head": s["subject"]["head_sha"],
        "parent_head": previous["subject"]["head_sha"] if previous else None,
        "comparisons": rows,
        "comparability_is_not_security_or_merge_approval": True,
    }


def compute_unknowns(s: dict) -> dict:
    rows = [
        {
            "id": u["id"],
            "kind": "EXPLICIT",
            "priority": u["priority"],
            "question": u["question"],
            "reason": u["reason"],
            "needed_evidence": u["needed_evidence"],
            "acquisition": u["acquisition"],
            "owner": u["owner"],
        }
        for u in s["unknowns"]
    ]
    for m in s["metrics"]:
        if m["state"] == "UNKNOWN":
            rows.append(
                {
                    "id": "METRIC." + m["id"],
                    "kind": "METRIC",
                    "priority": 3,
                    "question": m["label"],
                    "reason": m["missing_reason"],
                    "needed_evidence": "Matched native numerator and denominator, scoped to SHA",
                    "acquisition": "Execute native producer; extract source-bound artifact",
                    "owner": "Metric producer",
                }
            )
    for g in s["gates"]:
        if g["status"] in ("UNKNOWN", "PENDING", "IN_PROGRESS", "CANCELLED"):
            rows.append(
                {
                    "id": "GATE." + g["id"],
                    "kind": "GATE",
                    "priority": 2,
                    "question": g["label"],
                    "reason": g["status"],
                    "needed_evidence": "Terminal authenticated run or eligible independent authority",
                    "acquisition": "Inspect matching SHA and original gate source",
                    "owner": "Gate owner",
                }
            )
    return {
        "schema": "handover.unknowns.v2",
        "snapshot_head": s["subject"]["head_sha"],
        "counts": {"explicit": len(s["unknowns"]), "total_open_questions": len(rows)},
        "unknowns": sorted(rows, key=lambda x: (x["priority"], x["id"])),
    }


def render_report(s: dict, cm: dict, un: dict) -> bytes:
    su = s["subject"]
    snap = s["snapshot"]
    aut = s["authority"]
    lines = [
        f"# {snap['title']}",
        "",
        f"**Protocol:** `{PROTOCOL}` | **Captured UTC:** `{snap['captured_at_utc']}`",
        f"**Fidelity:** `{snap['fidelity_mode']}`; transcript completeness `{snap['transcript_completeness']}`.",
        "**Warning:** capsule bytes and locally declared claims may be checked; remote authenticity and complete conversation capture are NOT certified.",
        "",
        "## 1. Identity and objective",
        "",
        f"- Repository: `{su['repository']}`; item: [{su['work_item']}]({su['url']}).",
        f"- Branch: `{su['branch']}`.",
        f"- Exact head: `{su['head_sha']}`.",
        f"- Base SHA: `{su['base_sha'] or 'UNKNOWN'}`; main SHA: `{su['default_branch_sha'] or 'UNKNOWN'}`.",
        f"- Objective: {snap['objective']}",
        f"- Replay boundary: {snap['replay_boundary']}",
        "",
        "## 2. Admission authority",
        "",
        f"**Decision: {aut['merge_decision']}** | merged={aut['merged']} | protection={aut['effective_branch_protection']} | independent approval={aut['independent_approval']}",
        f"Waiver={aut['security_waiver']}; authority transfer={aut['authority_transfer']}; formal credit={aut['formal_credit_delta']}; engineering credit={aut['engineering_credit_delta']}.",
        "",
        "## 3. Metrics (historical is not current)",
        "",
        "| ID | State | Scope | Measurement | Source SHA | Evidence |",
        "|---|---|---|---:|---|---|",
    ]
    for m in s["metrics"]:
        lines.append(
            f"| `{m['id']}` | {m['state']} | `{m['basis']['scope_id']}` | {safe_md(metric_string(m))} | `{m['source_sha'] or 'UNKNOWN'}` | {', '.join(m['evidence_ids']) or 'UNKNOWN'} |"
        )
    lines += [
        "",
        "## 4. Comparison admission",
        "",
        "| Comparison | Eligibility | Delta covered | Delta eligible | Delta percentage points | Reason |",
        "|---|---|---:|---:|---:|---|",
    ]
    for x in cm["comparisons"]:
        lines.append(
            f"| {safe_md(x['label'])} | {x['status']} | {x['delta_covered'] if x['delta_covered'] is not None else 'UNKNOWN'} | {x['delta_eligible'] if x['delta_eligible'] is not None else 'UNKNOWN'} | {x['delta_percentage_points'] if x['delta_percentage_points'] is not None else 'UNKNOWN'} | {safe_md('; '.join(x['reasons']) or 'Same verified measurement basis')} |"
        )
    lines += [
        "",
        "## 5. Required and supporting gates",
        "",
        "| Gate | Scope | Status | Required | SHA | Evidence |",
        "|---|---|---|---|---|---|",
    ]
    for g in s["gates"]:
        lines.append(
            f"| {safe_md(g['label'])} | {g['scope']} | **{g['status']}** | {g['required_for_admission']} | `{g['source_sha'] or 'UNKNOWN'}` | {', '.join(g['evidence_ids']) or 'UNKNOWN'} |"
        )
    lines += [
        "",
        "## 6. BD / LDAB independent root ledger",
        "",
        "| ID | Kind | Disposition | Signature | Owner | Treatment |",
        "|---|---|---|---|---|---|",
    ]
    for b in s["blockers"]:
        lines.append(
            f"| `{b['id']}` | {b['classification']} | {b['disposition']} | {safe_md(b['signature'])} | {safe_md(b['owner'])} | {safe_md(b['next_action'])} |"
        )
    lines += [
        "",
        f"## 7. Unresolved / pending questions ({un['counts']['total_open_questions']})",
        "",
        "| Priority | ID | Reason | Next evidence |",
        "|---:|---|---|---|",
    ]
    for u in un["unknowns"]:
        lines.append(
            f"| {u['priority']} | `{u['id']}` | {safe_md(u['reason'])} | {safe_md(u['acquisition'])} |"
        )
    lines += [
        "",
        "## 8. Ordered next operations and DoV",
        "",
    ]
    for a in sorted(s["actions"], key=lambda x: x["order"]):
        lines += [
            f"{a['order']}. **{safe_md(a['title'])}** (`{a['id']}`) — {a['instruction']}",
            f"   - Owner: {a['owner']}; prerequisites: {', '.join(a['depends_on']) or 'none'}; blockers: {', '.join(a['blocked_by']) or 'none'}.",
            f"   - **Acceptance:** {a['acceptance']}",
            f"   - Stop condition: {a['stop_condition'] or 'Only when the acceptance receipt is available'}.",
        ]
    lines += [
        "",
        "## 9. Evidence provenance index",
        "",
    ]
    for ev in s["evidence"]:
        lines.append(
            f"- `{ev['id']}` {ev['label']} [{ev['observation']}]: {ev['uri'] or 'no external URI'}; SHA `{ev['source_sha'] or 'UNKNOWN'}`; event `{ev['event']}`, run/attempt/job/artifact `{ev['run_id'] or '-'}/{ev['run_attempt'] or '-'}/{ev['job_id'] or '-'}/{ev['artifact_id'] or '-'}`."
        )
    lines += [
        "",
        "## 10. Raw byte inventory (partial evidence is not full chat)",
        "",
    ]
    if s["raw_sources"]:
        for raw in s["raw_sources"]:
            lines.append(
                f"- `{raw['path']}` SHA-256 `{raw['sha256']}` ({raw['evidence_id']})."
            )
    else:
        lines.append("- No source bytes included.")
    lines += [
        "",
        "## 11. Decisions / controls and tool restrictions",
        "",
    ]
    for d in s["decisions"]:
        lines.append(f"- `{d['id']}` {d['status']}: {d['reason']}")
    for t in s["constraints"]:
        lines.append("- CONSTRAINT: " + t)
    for t in s["tool_limitations"]:
        lines.append("- LIMITATION: " + t)
    lines += [
        "",
        "## 12. Restart contract",
        "",
        "1. Verify live exact head and branch, including event='workflow_dispatch' runs separately from PR runs.",
        "2. Compare fresh evidence to this dated snapshot; never overwrite historical run identities.",
        "3. Repair only a verified first-red root; preserve the protected-main and reviewer gates.",
        "4. Emit next snapshot and compare only matching source scope/configuration.",
        "5. If launch or authenticated evidence is unavailable, report the blocker once; do not loop on empty checks.",
        "",
        "## 13. Assurance boundary",
        "",
        "Generated artifacts are deterministic and their hashes are checkable, but SHA-256 alone is not third-party authentication. The remote run/approval remains independently verifiable only by inspecting its authoritative source. A complete original conversation is NOT proved archived by this handover.",
        "",
    ]
    return ("\n".join(lines)).encode("utf-8")


def render_dropin(s: dict) -> bytes:
    title = s["snapshot"]["title"]
    lead = f"""# DROP-IN: {PROTOCOL} / {title}

Continue this task using the JSON snapshot below as dated operational evidence, not as authorization. First obtain live exact head, event-specific native workflow runs, review and main protection. Distinguish same-SHA PASS from other-sha historical success. Use metric numerators, denominators, scope, tool version and config digest; do not credit unverified comparisons. Inspect first-red and fix only owned root. Preserve immutable source links and exact GitHub identities. No security waivers, self approval, branch bypass or invented crew/debug receipts. Stop repetitive empty polling if execution authority is absent. Make a new capsule with links, bounded delta, DoD/DoV, UNKNOWN acquisition plans, and preserve this one as predecessor. This handover is not a full literal chat export.

```json
"""
    return lead.encode("utf-8") + canonical(s) + b"```\n"


def qa_report(s: dict, cm: dict, un: dict) -> bytes:
    result = {
        "schema": "handover.qa.v2",
        "snapshot_head": s["subject"]["head_sha"],
        "static_validations": {
            "json_schema": "PASS",
            "semantic_evidence_references": "PASS",
            "source_sha_binding": "PASS",
            "authority_fail_closed": "PASS",
            "raw_file_digest_checks": "PASS",
            "byte_equality_assertions": "PASS",
            "archived_numeric_claims_bound_to_source_json": "PASS",
            "action_dependency_dag": "PASS",
            "comparison_ineligible_without_config_proof": "PASS",
        },
        "remote_urls_fetched_by_generator": False,
        "original_conversation_completeness_proved": False,
        "independent_security_acceptance_inferred": False,
        "measured_current_metrics": sum(x["state"] == "MEASURED" for x in s["metrics"]),
        "historical_metrics": sum(x["state"] == "HISTORICAL" for x in s["metrics"]),
        "explicit_unknown_metrics": sum(x["state"] == "UNKNOWN" for x in s["metrics"]),
        "unresolved_comparisons": sum(
            x["status"] != "COMPARABLE" for x in cm["comparisons"]
        ),
        "unresolved_questions": un["counts"]["total_open_questions"],
        "byte_equality_checks_count": len(s["byte_equalities"]),
        "numeric_source_bindings_count": len(s["numeric_bindings"]),
        "verification_scope": "LOCAL_CONSISTENCY_AND_BYTES_ONLY",
    }
    return canonical(result)


def compute_generated(s: dict, previous: dict | None = None) -> dict[str, bytes]:
    comparisons = compute_comparisons(s, previous)
    unknowns = compute_unknowns(s)
    return {
        "state.json": canonical(s),
        "handover.md": render_report(s, comparisons, unknowns),
        "dropin.md": render_dropin(s),
        "comparisons.json": canonical(comparisons),
        "unknowns.json": canonical(unknowns),
        "qa_report.json": qa_report(s, comparisons, unknowns),
    }


def source_bytes(s: dict, base: Path) -> dict[str, bytes]:
    return {
        "sources/" + x["path"]: (base / x["path"]).read_bytes()
        for x in s["raw_sources"]
    }


def protocol_bytes(script_dir: Path) -> dict[str, bytes]:
    return {
        "protocol/" + name: (script_dir / name).read_bytes() for name in PROTOCOL_FILES
    }


def expected_files(
    input_path: Path,
    script_dir: Path,
    raw_base: Path,
    previous: dict | None = None,
    previous_manifest: dict | None = None,
) -> tuple[dict[str, bytes], bytes]:
    inp = input_path.read_bytes()
    s = json.loads(inp)
    schema = json.loads((script_dir / "handover_input.schema.json").read_bytes())
    validate_input(s, schema, raw_base)
    gen = compute_generated(s, previous)
    allfiles = {
        **gen,
        "input.json": inp,
        **protocol_bytes(script_dir),
        **source_bytes(s, raw_base),
    }
    if previous is not None:
        if previous_manifest is None:
            raise ValueError("Previous state provided without previous manifest")
        if (
            previous_manifest["manifest_root_sha256"]
            != s["snapshot"]["parent_manifest_root_sha256"]
        ):
            raise ValueError("Parent manifest root differs from declared lineage")
        allfiles["previous/state.json"] = canonical(previous)
        allfiles["previous/manifest.json"] = canonical(previous_manifest)
    entries = {name: sha256(value) for name, value in sorted(allfiles.items())}
    payload = {
        "manifest_schema": "handover.manifest.v2",
        "protocol": PROTOCOL,
        "head_sha": s["subject"]["head_sha"],
        "captured_at_utc": s["snapshot"]["captured_at_utc"],
        "parent_manifest_root_sha256": s["snapshot"]["parent_manifest_root_sha256"],
        "file_hashes_sha256": entries,
        "claims_complete_original_conversation": False,
        "claims_remote_validation_by_generator": False,
        "verified_byte_scope": "only files listed in file_hashes_sha256",
    }
    payload["manifest_root_sha256"] = sha256(canonical(payload))
    allfiles["manifest.json"] = canonical(payload)
    return allfiles, allfiles["manifest.json"]


def capsule_verify(directory: Path, allow_previous: bool = True) -> tuple[dict, dict]:
    base = directory.resolve()
    inp = base / "input.json"
    if not inp.is_file():
        raise ValueError("Not a capsule: missing input.json")
    s = json.loads(inp.read_bytes())
    man = json.loads((base / "manifest.json").read_bytes())
    # External symlink targets violate self-contained capsule replay, even
    # when their current bytes happen to match the recorded digest.
    for member in base.rglob("*"):
        if member.is_symlink():
            raise ValueError(
                "Capsule contains symbolic link: " + str(member.relative_to(base))
            )
    # Independently check all stored hashes and forbid unrecorded file content.
    entries = man.get("file_hashes_sha256", {})
    present = {p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file()}
    if present != set(entries) | {"manifest.json"}:
        raise ValueError(
            "Unexpected or missing file(s) in capsule: "
            + str(sorted(present ^ (set(entries) | {"manifest.json"})))
        )
    for name, digest in entries.items():
        if sha256((base / name).read_bytes()) != digest:
            raise ValueError("Manifest content hash mismatch: " + name)
    payload = dict(man)
    root = payload.pop("manifest_root_sha256", None)
    if root != sha256(canonical(payload)):
        raise ValueError("Manifest root digest mismatch")
    # Regeneration uses embedded pinned generator/schema/spec and copied raw bytes.
    prev_state = None
    prev_manifest = None
    if (base / "previous/state.json").exists():
        prev_state = json.loads((base / "previous/state.json").read_bytes())
        prev_manifest = json.loads((base / "previous/manifest.json").read_bytes())
        if s["snapshot"]["parent_manifest_root_sha256"] != prev_manifest.get(
            "manifest_root_sha256"
        ):
            raise ValueError("Parent chain root mismatch")
    expected, _ = expected_files(
        inp, base / "protocol", base / "sources", prev_state, prev_manifest
    )
    if set(expected) != present:
        raise ValueError("Generated file-set mismatch")
    for name, value in expected.items():
        if (base / name).read_bytes() != value:
            raise ValueError("Deterministic replay mismatch: " + name)
    return s, man


def build(args):
    input_path = Path(args.input).resolve()
    out = Path(args.out).resolve()
    script_dir = Path(__file__).resolve().parent
    s = json.loads(input_path.read_bytes())
    parent_s = None
    if args.previous:
        parent_s, parent_m = capsule_verify(Path(args.previous))
        if (
            s["snapshot"]["parent_manifest_root_sha256"]
            != parent_m["manifest_root_sha256"]
        ):
            raise ValueError("Parent root does not match input lineage")
    elif s["snapshot"]["parent_manifest_root_sha256"]:
        raise ValueError("Parent root declared but --previous not supplied")
    files, _manifest = expected_files(
        input_path,
        script_dir,
        input_path.parent,
        parent_s,
        parent_m if args.previous else None,
    )
    if out.exists() and any(out.iterdir()) and not args.replace:
        raise ValueError(
            "Output directory already populated; use --replace intentionally"
        )
    if out.exists() and args.replace:
        shutil.rmtree(out)
    for name, contents in files.items():
        dest = out / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(contents)
    _, man = capsule_verify(out)
    print(
        "PASS BUILD; deterministic replay; files="
        + str(len(files))
        + "; root="
        + man["manifest_root_sha256"]
    )


def verify(args):
    _, man = capsule_verify(Path(args.capsule))
    print(
        "PASS VERIFY; schema, semantic guards, manifest, raw hashes, second-pass equality"
    )
    print("MANIFEST_ROOT_SHA256=" + man["manifest_root_sha256"])
    print("REMOTE_VERIFICATION=NOT_PERFORMED; COMPLETE_TRANSCRIPT=NOT_ATTESTED")


def diff(args):
    a, am = capsule_verify(Path(args.before))
    b, bm = capsule_verify(Path(args.after))
    comp = compute_comparisons(b, a)
    ag = {g["id"]: g["status"] for g in a["gates"]}
    bg = {g["id"]: g["status"] for g in b["gates"]}
    ab = {x["id"]: x["disposition"] for x in a["blockers"]}
    bb = {x["id"]: x["disposition"] for x in b["blockers"]}
    result = {
        "schema": "handover.iteration.delta.v2",
        "before_root": am["manifest_root_sha256"],
        "after_root": bm["manifest_root_sha256"],
        "before_head": a["subject"]["head_sha"],
        "after_head": b["subject"]["head_sha"],
        "comparisons": comp["comparisons"],
        "gate_transitions": [
            {"id": k, "before": ag.get(k), "after": bg.get(k)}
            for k in sorted(set(ag) | set(bg))
            if ag.get(k) != bg.get(k)
        ],
        "blocker_transitions": [
            {"id": k, "before": ab.get(k), "after": bb.get(k)}
            for k in sorted(set(ab) | set(bb))
            if ab.get(k) != bb.get(k)
        ],
        "independent_admission_claimed": False,
    }
    Path(args.out).write_bytes(canonical(result))
    print(
        "PASS DIFF; output="
        + args.out
        + "; comparable="
        + str(sum(x["status"] == "COMPARABLE" for x in comp["comparisons"]))
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    pb = sub.add_parser("build")
    pb.add_argument("--input", required=True)
    pb.add_argument("--out", required=True)
    pb.add_argument("--previous")
    pb.add_argument("--replace", action="store_true")
    pv = sub.add_parser("verify")
    pv.add_argument("--capsule", required=True)
    pd = sub.add_parser("diff")
    pd.add_argument("--before", required=True)
    pd.add_argument("--after", required=True)
    pd.add_argument("--out", required=True)
    args = parser.parse_args()
    try:
        {"build": build, "verify": verify, "diff": diff}[args.command](args)
    except (ValueError, KeyError, FileNotFoundError, json.JSONDecodeError) as exc:
        print("FAIL " + str(exc), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
