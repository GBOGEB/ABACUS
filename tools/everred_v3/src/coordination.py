"""Repository-scoped canonical leases using Git's atomic ref compare-and-swap.

Source mutations remain independently permission-gated. A lease is coordination,
NOT authorization to edit source, merge or approve security. No expiry-based theft.
The dedicated ref must be permission-restricted by the repo administrator.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess

from everred import InvalidEvidence, overlap, stable_json, valid_sha

REF = "refs/heads/everred-v3-lease-registry"
ZERO = "0" * 40


def sane_path(path):
    if (
        not isinstance(path, str)
        or not path
        or path.startswith("/")
        or "\\" in path
        or re.match(r"^[A-Za-z]:", path)
    ):
        raise InvalidEvidence("lease path must be normalized repository-relative POSIX")
    if any(x in ("", ".", "..") for x in path.split("/")):
        raise InvalidEvidence("unsafe lease path segment")
    return path


def registry(repo):
    return {
        "schema": "abacus.everred.leases.v1",
        "repository": repo,
        "generation": 0,
        "active": {},
        "released": [],
        "used_idempotency_keys": [],
    }


def apply_operation(state, op):
    require = lambda pred, msg: (
        (_ for _ in ()).throw(InvalidEvidence(msg)) if not pred else None
    )
    require(
        isinstance(state, dict) and state.get("schema") == "abacus.everred.leases.v1",
        "wrong lease registry schema",
    )
    require(
        isinstance(op, dict) and op.get("type") in ("claim", "release"),
        "invalid operation",
    )
    repo = state["repository"]
    require(isinstance(repo, str) and "/" in repo, "missing repository")
    active = state["active"]
    require(isinstance(active, dict), "corrupt active registry")
    require(
        type(state.get("generation")) is int and state["generation"] >= 0,
        "invalid generation",
    )
    out = json.loads(stable_json(state))
    rid = op.get("root_id")
    require(isinstance(rid, str) and len(rid) > 5, "root identity required")
    key = op.get("idempotency_key")
    require(isinstance(key, str) and len(key) > 7, "idempotency required")
    require(key not in out["used_idempotency_keys"], "duplicate idempotency key")
    if op["type"] == "claim":
        sha = op.get("expected_source_sha")
        require(valid_sha(sha), "invalid source head SHA")
        paths = op.get("paths")
        require(isinstance(paths, list) and bool(paths), "paths required")
        paths = sorted({sane_path(p) for p in paths})
        principal = op.get("principal")
        require(isinstance(principal, str) and principal.strip(), "principal required")
        proof = op.get("authority_reference")
        require(
            isinstance(proof, str) and proof.startswith("https://github.com/"),
            "external authority reference required (not verified by this module)",
        )
        require(rid not in active, "root already owned")
        for lease in active.values():
            require(lease["repository"] == repo, "cross-repo registry contamination")
            require(
                not any(overlap(x, y) for x in paths for y in lease["paths"]),
                "overlapping mutation scope: reconcile with canonical owner",
            )
        out["active"][rid] = {
            "repository": repo,
            "principal": principal,
            "paths": paths,
            "expected_source_sha": sha,
            "authority_reference": proof,
            "claim_id": key,
            "authority_status": "EXTERNALLY_REFERENCED_NOT_VALIDATED",
        }
    else:
        require(rid in active, "no active lease")
        require(
            op.get("claim_id") == active[rid]["claim_id"],
            "release does not own active claim",
        )
        require(
            isinstance(op.get("release_evidence_url"), str)
            and op["release_evidence_url"].startswith("https://github.com/"),
            "release requires auditable evidence reference",
        )
        out["released"].append(
            {
                "root_id": rid,
                "claim_id": active[rid]["claim_id"],
                "evidence_url": op["release_evidence_url"],
            }
        )
        del out["active"][rid]
    out["used_idempotency_keys"].append(key)
    out["generation"] += 1
    return out


class GitCASStore:
    """All authoritative writes are a single lease-guarded Git ref update."""

    def __init__(self, local_repo, *, remote="origin", ref=REF):
        self.root = pathlib.Path(local_repo).resolve()
        self.remote = remote
        self.ref = ref
        if ref != REF:
            raise InvalidEvidence("ref must be dedicated lease registry")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", remote):
            raise InvalidEvidence("unsafe remote name")

    def git(self, *args, input=None, ok=True):
        p = subprocess.run(
            ["git", "-C", str(self.root), *args],
            input=input,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=45,
        )
        if ok and p.returncode:
            raise InvalidEvidence(f"git {args[0]} failed: {p.stderr[:300]}")
        return p

    def read(self, repo):
        lines = self.git(
            "ls-remote", "--refs", self.remote, self.ref
        ).stdout.splitlines()
        require = lambda c, m: (
            (_ for _ in ()).throw(InvalidEvidence(m)) if not c else None
        )
        require(len(lines) <= 1, "ambiguous lease ref")
        if not lines:
            return ZERO, registry(repo)
        old = lines[0].split()[0]
        require(valid_sha(old), "invalid current lease ref")
        self.git("fetch", "--no-tags", self.remote, old)
        blob = self.git("show", f"{old}:registry.json").stdout
        try:
            state = json.loads(blob)
        except ValueError as ex:
            raise InvalidEvidence("invalid lease registry JSON") from ex
        require(
            state.get("repository") == repo
            and state.get("schema") == "abacus.everred.leases.v1",
            "unexpected registry identity",
        )
        return old, state

    def commit(self, old, state):
        blob_sha = self.git(
            "hash-object", "-w", "--stdin", input=stable_json(state) + "\n"
        ).stdout.strip()
        tree_sha = self.git(
            "mktree", input=f"100644 blob {blob_sha}\tregistry.json\n"
        ).stdout.strip()
        parent = ["-p", old] if old != ZERO else []
        return self.git(
            "commit-tree",
            tree_sha,
            *parent,
            "-m",
            f'everred: lease generation {state["generation"]}',
        ).stdout.strip()

    def transact(self, repo, op, *, apply=False):
        old, state = self.read(repo)
        next_state = apply_operation(state, op)
        if not apply:
            return {
                "status": "PROPOSED_NOT_WRITTEN",
                "previous_ref": old,
                "registry": next_state,
            }
        new = self.commit(old, next_state)
        # Atomic receive-pack ref conditional update. A competing worker wins => push fails.
        lease = f'--force-with-lease={self.ref}:{"" if old==ZERO else old}'
        result = self.git("push", lease, self.remote, f"{new}:{self.ref}", ok=False)
        if result.returncode:
            raise InvalidEvidence(
                "atomic lease CAS rejected (stale ref or permission); read fresh registry"
            )
        return {
            "status": "COORDINATION_COMMITTED_NOT_SOURCE_AUTHORIZATION",
            "old_ref": old,
            "new_ref": new,
            "generation": next_state["generation"],
        }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--checkout", required=True)
    p.add_argument("--operation", required=True)
    p.add_argument("--apply", action="store_true")
    a = p.parse_args()
    op = json.loads(pathlib.Path(a.operation).read_text())
    print(
        json.dumps(
            GitCASStore(a.checkout).transact(a.repo, op, apply=a.apply), indent=2
        )
    )


if __name__ == "__main__":
    main()
