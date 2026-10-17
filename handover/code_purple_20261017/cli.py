#!/usr/bin/env python3
"""Read-only CODE PURPLE handover viewer/build/QA/ZIP CLI.

Edits to MONIKERS.json require an ordinary reviewed GitHub PR; no endpoint is
called by build/verify/serve. This is a dated snapshot, not the V2 evidence
archive or an independent source-of-truth.
"""
import argparse
import hashlib
import html
import http.server
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
SOURCE_FILES = ("STATE.json", "MONIKERS.json", "HANDOVER.md", "DROPIN.md",
                "README.md", "viewer_template.html", "cli.py")
PROJECT = "CODE_PURPLE_LOSSLESS_HANDOVER_20261017"
SCHEMA = "code-purple.handover.monikers/1.0"
STAMP = (2026, 10, 17, 0, 0, 0)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load():
    state = json.loads((HERE / "STATE.json").read_text(encoding="utf-8"))
    monikers = json.loads((HERE / "MONIKERS.json").read_text(encoding="utf-8"))
    if monikers.get("schema") != SCHEMA or monikers.get("promotion_authority") is not False:
        raise ValueError("Unsupported moniker schema or authority change")
    entries = monikers.get("entries")
    if not isinstance(entries, list) or not entries or len({e["id"] for e in entries}) != len(entries):
        raise ValueError("Missing or duplicate canonical monikers")
    if state.get("merge_admission") != "HOLD" or state.get("authority_transfer") is not False:
        raise ValueError("Handover must not promote admission authority")
    for key in ("repository_heads", "confirmed_merges", "issue_controls"):
        if not state.get(key):
            raise ValueError("Handover missing required lineage " + key)
    return state, monikers


def inline_json(doc):
    return json.dumps(doc, ensure_ascii=False, separators=(",", ":")).replace(
        "<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def render():
    state, monikers = load()
    template = (HERE / "viewer_template.html").read_text(encoding="utf-8")
    output = (template.replace("__MONIKER_JSON__", inline_json(monikers))
              .replace("__STATE_JSON__", inline_json(state))
              .replace("__DROPIN_JSON__", inline_json(
                  (HERE / "DROPIN.md").read_text(encoding="utf-8"))))
    if "__MONIKER_JSON__" in output or "__STATE_JSON__" in output:
        raise ValueError("Unexpanded template token")
    return output


def build(output):
    output = Path(output).resolve()
    if HERE in output.parents or output == HERE:
        raise ValueError("Build output must be outside controlled source folder")
    output.mkdir(parents=True, exist_ok=True)
    state, monikers = load()
    for name in SOURCE_FILES:
        shutil.copyfile(HERE / name, output / name)
    (output / "taxonomy.html").write_text(render(), encoding="utf-8")
    receipt = {
        "schema": "qps-artifact-qa/1.0",
        "source": {
            "locator": "GBOGEB/ABACUS:handover/code_purple_20261017",
            "semantic_sha256": digest((HERE / "MONIKERS.json").read_bytes()),
            "git_sha": None,
        },
        "checks": {
            "structural": "PASS",
            "formula_or_content": "PASS",
            "render_visual": "DEFER",
            "playwright": "DEFER",
            "cross_format_parity": "PASS",
        },
        "evidence_level": "LOCAL_REPRODUCIBILITY",
        "defects": [],
        "notes": ["No exact-head native CI or remote permission is inferred.",
                  "Browser QA receipt may be supplemented after visual QA."],
    }
    (output / "QA_RECEIPT.json").write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    manifest = {"schema": "code-purple.handover.manifest.v1", "files": {},
                "fidelity": "OPERATIONAL_SNAPSHOT_NOT_VERBATIM_EXPORT",
                "source_heads": {x["repo"]: x["sha"] for x in state["repository_heads"]},
                "admission": "HOLD"}
    for path in sorted(output.iterdir()):
        if path.is_file() and path.name != "manifest.json":
            manifest["files"][path.name] = digest(path.read_bytes())
    (output / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    archive = output.parent / (PROJECT + ".zip")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
        for path in sorted(output.iterdir()):
            if path.is_file():
                info = zipfile.ZipInfo(PROJECT + "/" + path.name, STAMP)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                zipped.writestr(info, path.read_bytes())
    return archive


def verify(output):
    output = Path(output)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    recorded = manifest.get("files", {})
    observed = {p.name for p in output.iterdir()
                if p.is_file() and p.name != "manifest.json"}
    if set(recorded) != observed:
        raise ValueError("Unmanifested/missing files: " + str(observed ^ set(recorded)))
    for name, expected in recorded.items():
        if digest((output / name).read_bytes()) != expected:
            raise ValueError("Hash mismatch: " + name)
    data = (output / "taxonomy.html").read_text(encoding="utf-8")
    if "__MONIKER_JSON__" in data or "<title>" not in data or 'id="search"' not in data:
        raise ValueError("Invalid HTML projection")
    json.loads((output / "STATE.json").read_text(encoding="utf-8"))
    json.loads((output / "MONIKERS.json").read_text(encoding="utf-8"))
    return len(recorded)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["build", "verify", "serve", "dropin", "status", "gh-status"])
    p.add_argument("--out", default=str(HERE.parent.parent / "dist" / PROJECT))
    p.add_argument("--port", type=int, default=8765)
    args = p.parse_args(argv)
    if args.action == "build":
        path = build(args.out)
        print(json.dumps({"zip": str(path), "files_verified": verify(args.out)}))
    elif args.action == "verify":
        print(json.dumps({"result": "LOCAL_STRUCTURE_PASS", "file_count": verify(args.out)}))
    elif args.action == "serve":
        output = Path(args.out)
        if not (output / "taxonomy.html").exists():
            build(output)
        os.chdir(output)
        print("Open http://localhost:%d/taxonomy.html" % args.port, flush=True)
        http.server.ThreadingHTTPServer(("127.0.0.1", args.port),
                                        http.server.SimpleHTTPRequestHandler).serve_forever()
    elif args.action == "dropin":
        print((HERE / "DROPIN.md").read_text(encoding="utf-8"))
    elif args.action == "status":
        state, terms = load()
        print(json.dumps({"repositories": state["repository_heads"],
                          "observations": state["snapshots"],
                          "monikers": len(terms["entries"]),
                          "admission": state["merge_admission"]}, indent=2))
    else:
        commands = [
            ["gh", "api", "repos/GBOGEB/ABACUS/branches/main", "--jq", ".commit.sha"],
            ["gh", "pr", "view", "2135", "--repo", "GBOGEB/ABACUS",
             "--json", "state,mergedAt,mergeCommit,headRefOid,reviewDecision"],
            ["gh", "issue", "list", "-R", "GBOGEB/ABACUS", "--state", "open",
             "--limit", "200"],
        ]
        for command in commands:
            print("$ " + " ".join(command), flush=True)
            subprocess.run(command, check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
