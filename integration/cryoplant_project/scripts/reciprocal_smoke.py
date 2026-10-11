"""ABACUS-to-cryoplant reciprocal federation smoke.

The local smoke tests in ``integration/cryoplant_project/tests`` only read
files in this repository. This script contacts GBOGEB/cryoplant-project
itself: it resolves the member's ``main`` head through the GitHub API, reads
the member's own ``federation/manifest.yaml`` at that commit and checks that
the member declares itself the active DELTA_1 auxiliary plane with ABACUS as
its runtime hub. The repository is private, so the run needs a token with
read access in ``GITHUB_TOKEN`` or ``GH_TOKEN``.

Writes ``integration/cryoplant_project/federation/reciprocal_smoke.json`` and
exits non-zero if any check fails or the member cannot be reached.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = (
    ROOT / "integration" / "cryoplant_project" / "federation" / "reciprocal_smoke.json"
)
MEMBER = "GBOGEB/cryoplant-project"
HUB = "GBOGEB/ABACUS"


def api(path: str, token: str) -> dict:
    request = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    # Fixed https://api.github.com base; no caller-controlled scheme.
    with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310
        return json.load(response)


def checks_for(manifest: dict) -> dict[str, bool]:
    federation = manifest.get("federation") or {}
    hub = (federation.get("hub") or {}).get("runtime_plane") or {}
    member = federation.get("self") or {}
    return {
        "moniker_is_delta_1": federation.get("moniker") == "DELTA_1",
        "member_status_active": federation.get("status") == "active",
        "member_is_auxiliary_plane": member.get("plane") == "auxiliary",
        "member_names_itself": member.get("repository") == MEMBER,
        "runtime_hub_is_abacus": hub.get("repository") == HUB,
    }


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("GITHUB_TOKEN or GH_TOKEN with read access is required", file=sys.stderr)
        return 2
    head = api(f"/repos/{MEMBER}/commits/main", token)["sha"]
    content = api(
        f"/repos/{MEMBER}/contents/federation/manifest.yaml?ref={head}", token
    )
    manifest = yaml.safe_load(base64.b64decode(content["content"]))
    checks = checks_for(manifest)
    status = "ok" if all(checks.values()) else "failed"
    evidence = {
        "direction": f"{HUB} -> {MEMBER}",
        "checked_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "member_main_sha": head,
        "checks": checks,
        "status": status,
    }
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2))
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
