"""Summarize immutable wave-pulse receipts without granting runtime authority."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

INPUT_SCHEMA = "abacus.mip.pulse-history-input.v1"
RECEIPT_SCHEMA = "abacus.mip.wave-pulse.v1"
SHA = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
KINDS = {"SYNTHETIC_CONTROL", "UNVERIFIED_OPERATIONAL"}
COVERAGE_STATES = {"COMPARABLE", "INCOMPARABLE", "UNKNOWN"}


def require(ok: bool, message: str) -> None:
    """Reject missing or contradictory evidence rather than guessing."""
    if not ok:
        raise ValueError(message)


def nonblank(value: object) -> bool:
    """Check an identifier without normalizing its spelling."""
    return isinstance(value, str) and bool(value.strip())


def scoped_file(root: Path, name: object) -> Path:
    """Only read ordinary files inside the declared evidence directory."""
    require(nonblank(name), "missing receipt path")
    path = (root / str(name)).resolve()
    require(path.is_relative_to(root) and path.is_file(), "unsafe or missing receipt")
    return path


def parse_metrics(entry: dict, receipt: dict) -> dict:
    """Extract displayed metrics without treating the input as attestation."""
    coverage = receipt.get("coverage")
    require(isinstance(coverage, dict), "missing coverage decision")
    status = coverage.get("status")
    require(status in COVERAGE_STATES, "invalid coverage decision")
    delta = "UNKNOWN"
    if status == "COMPARABLE":
        value = coverage.get("delta_pp")
        require(type(value) in (int, float), "missing comparable delta")
        require(-100 <= value <= 100, "invalid comparable delta")
        delta = round(value, 8)
    counts = receipt.get("root_counts")
    require(isinstance(counts, dict), "missing root census")
    for value in counts.values():
        require(type(value) is int and value >= 0, "invalid root count")
    tests = receipt.get("tests")
    require(isinstance(tests, dict), "missing tests")
    for key in ("passed", "failed", "skipped"):
        require(type(tests.get(key)) is int and tests[key] >= 0, "invalid test count")
    reds = receipt.get("first_reds")
    require(isinstance(reds, list), "missing first-reds")
    return {
        "wave_id": entry["wave_id"],
        "iteration_id": entry["iteration_id"],
        "pulse_id": entry["pulse_id"],
        "sequence": entry["sequence"],
        "source_kind": entry["source_kind"],
        "head_sha": entry["head_sha"],
        "run_id": entry["run_id"],
        "job_id": entry.get("job_id") or "UNKNOWN",
        "receipt_sha256": entry["receipt_sha256"],
        "coverage_status": status,
        "coverage_delta_pp": delta,
        "root_counts_from_receipt": counts,
        "first_red_manifestations": len(reds),
        "tests_from_payload": tests,
        "admission_disposition": receipt.get("disposition", "UNKNOWN"),
        "provenance_status": "HASH_MATCH_LOCAL_ONLY",
        "verified_operational_closures": "UNKNOWN",
        "authenticated_rex_receipts": "UNKNOWN",
    }


def evaluate(manifest: dict, evidence_dir: Path) -> dict:
    """Build a deterministic per-pulse census of SHA-matched local artifacts."""
    require(isinstance(manifest, dict), "manifest must be object")
    require(manifest.get("schema") == INPUT_SCHEMA, "invalid history schema")
    require(manifest.get("repository") == "GBOGEB/ABACUS", "wrong repository")
    records = manifest.get("records")
    require(isinstance(records, list) and records, "missing pulse records")
    root = evidence_dir.resolve()
    used = set()
    seen_sequences = set()
    output = []
    for record in records:
        require(isinstance(record, dict), "invalid pulse record")
        for name in ("wave_id", "iteration_id", "pulse_id"):
            require(nonblank(record.get(name)), "missing " + name)
        require(record.get("source_kind") in KINDS, "invalid source kind")
        require(type(record.get("sequence")) is int and record["sequence"] > 0, "invalid sequence")
        head_sha = record.get("head_sha")
        require(isinstance(head_sha, str) and SHA.fullmatch(head_sha), "invalid SHA")
        require(type(record.get("run_id")) is int and record["run_id"] > 0, "invalid run ID")
        job_id = record.get("job_id")
        require(job_id is None or (type(job_id) is int and job_id > 0), "invalid job ID")
        digest = record.get("receipt_sha256")
        require(isinstance(digest, str) and DIGEST.fullmatch(digest), "invalid digest")
        identity = (record["wave_id"], record["iteration_id"], record["pulse_id"])
        order = (record["wave_id"], record["sequence"])
        require(identity not in used and order not in seen_sequences, "duplicate pulse identity")
        used.add(identity)
        seen_sequences.add(order)
        path = scoped_file(root, record.get("receipt_path"))
        raw = path.read_bytes()
        require(bool(raw) and hashlib.sha256(raw).hexdigest() == digest, "receipt bytes mismatch")
        receipt = json.loads(raw)
        require(isinstance(receipt, dict) and receipt.get("schema") == RECEIPT_SCHEMA, "invalid receipt schema")
        require(receipt.get("repository") == manifest["repository"], "receipt repository mismatch")
        require(receipt.get("wave_id") == record["wave_id"], "receipt wave mismatch")
        require(receipt.get("head_sha") == record["head_sha"], "receipt SHA mismatch")
        require(receipt.get("merge_admitted") is not True, "admitted claim needs independent verification")
        output.append(parse_metrics(record, receipt))
    output.sort(key=lambda value: (value["wave_id"], value["sequence"]))
    return {
        "schema": "abacus.mip.pulse-history.v1",
        "repository": manifest["repository"],
        "evidence_class": "LOCAL_HASH_VERIFICATION_NOT_GITHUB_ADMISSION",
        "pulse_count": len(output),
        "synthetic_count": sum(item["source_kind"] == "SYNTHETIC_CONTROL" for item in output),
        "unverified_operational_count": sum(
            item["source_kind"] == "UNVERIFIED_OPERATIONAL" for item in output
        ),
        "measured_main_gain_pp": "UNKNOWN",
        "formal_root_closures": "UNKNOWN",
        "merge_admission": "HOLD",
        "pulses": output,
    }


def render_markdown(history: dict) -> str:
    """Give each pulse a visible row; do not plot synthetic operational gains."""
    lines = [
        "# MIP Wave / Iteration / Pulse history",
        "",
        "> LOCAL HASH CHECK ONLY — not a trusted runner, REX or merge receipt.",
        "> SYNTHETIC_CONTROL rows are fixtures, not operational burndown.",
        "",
        "| Wave | Iteration | Pulse | Kind | Run | Coverage | Delta pp | Open | Red | Tests* |",
        "| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in history["pulses"]:
        counts = row["root_counts_from_receipt"]
        tests = row["tests_from_payload"]
        summary = f"{tests['passed']}/{tests['failed']}/{tests['skipped']}"
        lines.append(
            f"| {row['wave_id']} | {row['iteration_id']} | {row['pulse_id']} | "
            f"{row['source_kind']} | {row['run_id']} | {row['coverage_status']} | "
            f"{row['coverage_delta_pp']} | {counts.get('open', 'UNKNOWN')} | "
            f"{row['first_red_manifestations']} | {summary} |"
        )
    lines.extend([
        "",
        "*Tests* = pass/fail/skip as **reported in the input payload**, not verified JUnit.",
        "Operational root closures and main-coverage improvements remain UNKNOWN.",
        "A real wave requires source-bound runner records and independent admission.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    """Produce two synchronized text-only outputs for CI artifact uploading."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    history = evaluate(data, args.artifact_root)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "mip_wave_history.json").write_text(
        json.dumps(history, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    (args.output_dir / "mip_wave_history.md").write_text(
        render_markdown(history), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
