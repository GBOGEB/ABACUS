"""Fail-closed DELTA_1 Codespaces identity cross-check.

Compare GitHub repository identifiers case-insensitively, without allowing
different owner/repo spellings, duplicate members or malformed values.
This checks configuration only; it never activates a federation member.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

CANONICAL = "GBOGEB/CODESPACES_jyperter"
HUB = "GBOGEB/ABACUS"


def normalized(value: object) -> str:
    if not isinstance(value, str) or value.count("/") != 1:
        raise ValueError("repository must be an owner/name string")
    owner, name = value.split("/")
    if not owner or not name or owner.strip() != owner or name.strip() != name:
        raise ValueError("invalid repository identifier")
    return value.casefold()


def validate(manifest: dict, runtime: dict, contract: dict) -> None:
    federation = manifest["federation"]
    if federation.get("moniker") != "DELTA_1":
        raise ValueError("unexpected federation moniker")
    members = federation["member_repos"]
    identities = [normalized(item["name"]) for item in members]
    if len(set(identities)) != len(identities):
        raise ValueError("duplicate member identity (case-insensitive)")
    target = normalized(CANONICAL)
    selected = [item for item in members if normalized(item["name"]) == target]
    if len(selected) != 1 or selected[0].get("status") != "active":
        raise ValueError("Codespaces member not uniquely active")
    if selected[0].get("plane") != "notebook":
        raise ValueError("Codespaces member plane mismatch")
    values = (
        federation["planes"]["notebook"]["repository"],
        runtime["federation"]["notebook_plane"]["repository"],
        contract["contract"]["consumer"],
    )
    if any(normalized(value) != target for value in values):
        raise ValueError("Codespaces identity mismatch across federation")
    if normalized(contract["contract"]["provider"]) != normalized(HUB):
        raise ValueError("unexpected contract provider")
    if contract["contract"].get("federation_moniker") != "DELTA_1":
        raise ValueError("contract federation mismatch")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    root = parser.parse_args().root
    paths = (
        "federation/manifest.yaml",
        "runtime/federation/codex-abacus-federation.yaml",
        "integration/codespace_jyperter/abacus_contract.yaml",
    )
    try:
        documents = [
            yaml.safe_load((root / path).read_text(encoding="utf-8")) for path in paths
        ]
        validate(*documents)
    except (ValueError, KeyError, TypeError, OSError, yaml.YAMLError) as exc:
        print(f"Codespaces federation identity FAIL: {exc}")
        return 1
    print("Codespaces federation identity PASS: canonical aliases agree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
