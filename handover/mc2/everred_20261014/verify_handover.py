#!/usr/bin/env python3
"""Read-only, standard library Git object + handover integrity verifier."""
import hashlib
import json
import re
from pathlib import Path

DIR = Path(__file__).resolve().parent

def blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()

def main():
    manifest = json.loads((DIR / "manifest.json").read_text(encoding="utf-8"))
    state = json.loads((DIR / "state.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "code-purple.lossless-manifest.v1"
    assert state["schema"] == "code-purple.lossless-handover.v1"
    assert state["role"] == "HISTORICAL_RECEIVER_NOT_MERGE_AUTHORITY"
    assert re.fullmatch("[a-f0-9]{40}", state["cut"]["main_sha"])
    assert state["invariants"]["security_waiver"] is False
    assert state["invariants"]["authority_transfer"] is False
    assert state["invariants"]["engineering_credit_delta"] == 0
    assert len({t["id"] for t in state["tasks"]}) == len(state["tasks"])
    assert any(x["status"] == "NOT_ARCHIVED" for x in state["unarchived"])
    for name, entry in manifest["files"].items():
        data = (DIR / name).read_bytes()
        assert len(data) == entry["bytes"], (name, "size")
        assert blob_sha(data) == entry["git_blob_sha1"], (name, "sha")
    print("PASS: Git handover blob hashes + fail-closed state structure")
if __name__ == "__main__":
    main()
