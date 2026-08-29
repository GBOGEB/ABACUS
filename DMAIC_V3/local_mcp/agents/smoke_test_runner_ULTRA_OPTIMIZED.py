"""Canonical DOW Stage 6 validation mechanic.

Fail-closed validation of the enriched JSON artifacts produced by the canonical DOW pipeline.
This is intentionally parent-owned and generic: it validates contract/lineage/idempotency/recursive
structure and the presence of convergence + knowledge outputs without embedding child-domain logic.
"""

import json
import sys
from pathlib import Path

TARGET = Path("DMAIC_CANONICAL_OUTPUT")
REQUIRED_TOP_LEVEL = {
    "metadata",
    "lineage",
    "idempotency",
    "recursive_hooks",
    "convergence_metrics",
    "knowledge_gain",
}


def validate_file(path: Path):
    errors = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"{path}: invalid JSON: {exc}"]

    missing = sorted(REQUIRED_TOP_LEVEL - set(data))
    if missing:
        errors.append(f"{path}: missing top-level keys: {', '.join(missing)}")

    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        errors.append(f"{path}: metadata must be an object")
    else:
        for key in ("iteration", "phase", "version"):
            if key not in metadata:
                errors.append(f"{path}: metadata.{key} missing")

    lineage = data.get("lineage")
    if not isinstance(lineage, dict):
        errors.append(f"{path}: lineage must be an object")
    else:
        if not lineage.get("artifact_path"):
            errors.append(f"{path}: lineage.artifact_path missing")
        if "parent_artifacts" not in lineage:
            errors.append(f"{path}: lineage.parent_artifacts missing")

    idem = data.get("idempotency")
    if not isinstance(idem, dict):
        errors.append(f"{path}: idempotency must be an object")
    else:
        for key in ("input_hash", "output_hash"):
            value = idem.get(key)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{path}: idempotency.{key} missing/empty")

    hooks = data.get("recursive_hooks")
    if not isinstance(hooks, dict):
        errors.append(f"{path}: recursive_hooks must be an object")
    else:
        for key in ("consumed_from", "feeds_into", "iteration_lineage", "version_history"):
            if key not in hooks:
                errors.append(f"{path}: recursive_hooks.{key} missing")

    conv = data.get("convergence_metrics")
    if not isinstance(conv, dict):
        errors.append(f"{path}: convergence_metrics must be an object")

    knowledge = data.get("knowledge_gain")
    if not isinstance(knowledge, dict):
        errors.append(f"{path}: knowledge_gain must be an object")
    else:
        for key in (
            "patterns_discovered",
            "insights_generated",
            "learnings_captured",
            "improvements_suggested",
        ):
            if key not in knowledge:
                errors.append(f"{path}: knowledge_gain.{key} missing")

    return errors


def main():
    if not TARGET.exists():
        print(f"[X] Target directory not found: {TARGET}")
        return 1

    files = sorted(TARGET.glob("*.json"))
    if not files:
        print(f"[X] No JSON artifacts found in {TARGET}")
        return 1

    all_errors = []
    for path in files:
        all_errors.extend(validate_file(path))

    if all_errors:
        print("[X] DOW Stage 6 validation failed")
        for error in all_errors:
            print(f" - {error}")
        return 1

    print(f"[OK] DOW Stage 6 validation passed for {len(files)} JSON artifact(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
