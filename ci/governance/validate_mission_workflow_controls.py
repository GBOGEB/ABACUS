#!/usr/bin/env python3
"""Fail-closed controls for HIST-BD-015/016.

REX-CM-003: governed external GitHub Actions are pinned to full commit SHAs.
REX-CM-004: W74/W169 explicitly checkout and assert the evaluated PR head/push SHA.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOVERNED = {
    ".github/workflows/ci-governance.yml": {"pin_actions": True, "exact_source": False},
    ".github/workflows/w74-qplant-k8s-contract.yml": {"pin_actions": True, "exact_source": True},
    ".github/workflows/w169-qplant-k8s-runtime.yml": {"pin_actions": True, "exact_source": True},
}

USES_RE = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)", re.MULTILINE)
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def external_action_refs(text: str) -> list[str]:
    refs: list[str] = []
    for match in USES_RE.finditer(text):
        ref = match.group(1).strip()
        if ref.startswith("./") or ref.startswith("docker://"):
            continue
        refs.append(ref)
    return refs


def validate_pins(path: str, text: str) -> list[str]:
    errors: list[str] = []
    for ref in external_action_refs(text):
        if "@" not in ref:
            errors.append(f"{path}: external action has no immutable ref: {ref}")
            continue
        _, version = ref.rsplit("@", 1)
        if not FULL_SHA_RE.fullmatch(version):
            errors.append(f"{path}: external action is not pinned to 40-char SHA: {ref}")
    return errors


def validate_exact_source(path: str, text: str) -> list[str]:
    required = [
        "github.event.pull_request.head.sha || github.sha",
        "EVALUATED_SOURCE_SHA",
        "git rev-parse",
    ]
    missing = [token for token in required if token not in text]
    if missing:
        return [f"{path}: missing exact-source controls: {missing}"]
    if "ref: ${{ github.event.pull_request.head.sha || github.sha }}" not in text:
        return [f"{path}: checkout ref is not explicitly bound to evaluated PR head/push SHA"]
    return []


def main() -> int:
    errors: list[str] = []
    checked_actions = 0
    for rel, policy in GOVERNED.items():
        path = ROOT / rel
        if not path.exists():
            errors.append(f"missing governed workflow: {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        refs = external_action_refs(text)
        checked_actions += len(refs)
        if policy["pin_actions"]:
            errors.extend(validate_pins(rel, text))
        if policy["exact_source"]:
            errors.extend(validate_exact_source(rel, text))

    if errors:
        for error in errors:
            print(f"FAIL {error}")
        return 1

    print(
        "PASS REX-CM-003/004 "
        f"governed_workflows={len(GOVERNED)} external_action_refs={checked_actions} "
        "immutable_pins=true exact_source_workflows=2"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
