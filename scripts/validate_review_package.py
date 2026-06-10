"""Validate the W000 Q3/Q4/Q5 review artifact package."""

from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DOCS = (
    "docs/Q3_Q4_Q5/README.md",
    "docs/Q3_Q4_Q5/MAIN_QA_REGISTER.md",
    "docs/Q3_Q4_Q5/COMPENDIUM.md",
    "docs/Q3_Q4_Q5/MANAGEMENT_SUMMARY.md",
    "docs/Q3_Q4_Q5/WHAT_ALAT_IS_REALLY_ASKING.md",
    "docs/Q3_Q4_Q5/CONTRACTUAL_GAPS.md",
)
REQUIRED_SSOT_IDS = {"SSOT-Q3", "SSOT-Q4", "SSOT-Q5", "SSOT-CG"}
REQUIRED_GAP_IDS = {f"CG-{index:02d}" for index in range(1, 9)}
REQUIRED_DOMAINS = {
    "ssot_registry",
    "contractual_gap_register",
    "governance_controls",
    "ci_cd_scaffolding",
    "tender_review_package",
}
REQUIRED_REVIEW_GATES = {
    "Technical Review",
    "Contract Review",
    "Procurement Review",
    "Publish Approval",
}


def _read_yaml(path: Path) -> Dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    return data if isinstance(data, dict) else {}


def _require_fields(
    errors: List[str],
    label: str,
    item: Dict[str, Any],
    fields: Sequence[str],
) -> None:
    for field in fields:
        if not item.get(field):
            errors.append(f"{label} is missing {field}")


def _validate_paths(errors: List[str], paths: Iterable[str]) -> None:
    for relative_path in paths:
        if not (REPO_ROOT / relative_path).is_file():
            errors.append(f"Missing required file: {relative_path}")


def _validate_ssot(errors: List[str]) -> None:
    registry = _read_yaml(REPO_ROOT / "ssot/ssot_items.yaml")
    items = registry.get("ssot_items", [])
    ids = {item.get("id") for item in items if isinstance(item, dict)}
    for missing_id in sorted(REQUIRED_SSOT_IDS - ids):
        errors.append(f"Missing SSOT registry item: {missing_id}")
    for item in items:
        if isinstance(item, dict) and item.get("id") in REQUIRED_SSOT_IDS:
            _require_fields(
                errors,
                item["id"],
                item,
                ("name", "source", "owner", "status", "linked_artifacts"),
            )


def _validate_gaps(errors: List[str]) -> None:
    register = _read_yaml(REPO_ROOT / "ssot/contractual_gap_register.yaml")
    gaps = register.get("contractual_gaps", [])
    ids = {gap.get("id") for gap in gaps if isinstance(gap, dict)}
    for missing_id in sorted(REQUIRED_GAP_IDS - ids):
        errors.append(f"Missing contractual gap: {missing_id}")
    for gap in gaps:
        if isinstance(gap, dict) and gap.get("id") in REQUIRED_GAP_IDS:
            _require_fields(
                errors,
                gap["id"],
                gap,
                (
                    "title",
                    "related_question",
                    "ssot_id",
                    "severity",
                    "status",
                    "owner",
                    "resolution_path",
                    "review_gate",
                ),
            )


def _validate_governance(errors: List[str]) -> None:
    controls = _read_yaml(REPO_ROOT / "governance/pr_review_control.yaml")
    pr_control = controls.get("pr_control", {})
    for field in (
        "required_reviewers",
        "require_ssot_traceability",
        "require_rtm_reference",
        "require_management_review",
    ):
        if field not in pr_control:
            errors.append(f"PR control is missing {field}")

    policy = _read_yaml(REPO_ROOT / "governance/review_gate_policy.yaml")
    gates = policy.get("review_gates", {})
    gate_names = {
        gate.get("name")
        for gate in gates.values()
        if isinstance(gate, dict) and gate.get("name")
    }
    for gate_name in sorted(REQUIRED_REVIEW_GATES - gate_names):
        errors.append(f"Missing review gate: {gate_name}")


def _validate_manifest(errors: List[str]) -> None:
    manifest = _read_yaml(REPO_ROOT / "ssot/review_artifact_manifest.yaml")
    artifacts = manifest.get("artifacts", [])
    domains = set()
    paths = []
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            errors.append("Manifest artifact entries must be mappings")
            continue
        _require_fields(
            errors,
            artifact.get("id", "artifact"),
            artifact,
            ("id", "domain", "path"),
        )
        if artifact.get("domain"):
            domains.add(artifact["domain"])
        if artifact.get("path"):
            paths.append(artifact["path"])
    for missing_domain in sorted(REQUIRED_DOMAINS - domains):
        errors.append(f"Manifest is missing domain: {missing_domain}")
    _validate_paths(errors, paths)


def _validate_workflow(errors: List[str]) -> None:
    workflow_path = (
        REPO_ROOT / ".github/workflows/review-artifact-validation.yml"
    )
    workflow = workflow_path.read_text(encoding="utf-8")
    for expected in (
        "scripts/validate_review_package.py",
        "docs/**",
        "ssot/**",
        "governance/**",
    ):
        if expected not in workflow:
            errors.append(f"Review artifact workflow is missing {expected}")


def validate_review_package() -> List[str]:
    """Return validation errors for the W000 review package."""

    errors: List[str] = []
    _validate_paths(
        errors,
        (
            *REQUIRED_DOCS,
            "ssot/ssot_items.yaml",
            "ssot/contractual_gap_register.yaml",
            "ssot/review_artifact_manifest.yaml",
            "governance/review_gate_policy.yaml",
            "governance/pr_review_control.yaml",
            ".github/workflows/review-artifact-validation.yml",
        ),
    )
    if errors:
        return errors

    _validate_ssot(errors)
    _validate_gaps(errors)
    _validate_governance(errors)
    _validate_manifest(errors)
    _validate_workflow(errors)
    return errors


def main() -> int:
    """Run review package validation from the command line."""

    errors = validate_review_package()
    if errors:
        print("W000 review package validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("W000 review package validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
