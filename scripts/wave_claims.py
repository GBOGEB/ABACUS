#!/usr/bin/env python3
"""Wave claims: per-repo validation, federation roll-up and de-duplication.

Each member repo owns its wave declarations in .waves/WAVE_CLAIMS.yaml (its
prerogative). This module checks one claims file against
federation/waves/WAVE_NAMING_RULES.yaml, and rolls every repo's claims up into
one census in which a key has one owner and one name, names and aliases are
unique federation-wide, slugs only carry forward along lineage, and path
boundaries inside a repo do not overlap.

CLI (stdlib + PyYAML, ASCII output):
  python scripts/wave_claims.py validate [.waves/WAVE_CLAIMS.yaml] --expected-repo OWNER/NAME
      Validate a repo's own claims file (run in the member repo; exit 1 on errors).
  python scripts/wave_claims.py propose --repo GBOGEB/NAME [--register PATH]
      Draft a claims file from the observed census for the owner to review.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RULES_FILE = ROOT / "federation" / "waves" / "WAVE_NAMING_RULES.yaml"
REGISTER_FILE = ROOT / "federation" / "waves" / "WAVE_REGISTER.yaml"
CLAIMS_PATH = ".waves/WAVE_CLAIMS.yaml"
KEY_RE = re.compile(r"^(?P<ns>[A-Z]+):(?P<id>\S+)$")
NUM_IN_TEXT = re.compile(r"(?<![0-9])[Ww]?(\d{3})(?![0-9])")


def load_naming_rules(path: Path = RULES_FILE) -> dict:
    rules = yaml.safe_load(path.read_text(encoding="utf-8"))
    rules["_name_re"] = re.compile(rules["canonical_name"]["pattern"])
    rules["_alias_re"] = re.compile(rules["alias"]["pattern"])
    return rules


def tag(text: str) -> str:
    """Normalized comparison form shared by names and aliases (W364_ICD == w364-icd)."""
    return text.strip().lower().replace("_", "-")


def digest(text: str) -> str:
    return hashlib.sha256(tag(text).encode("ascii", "replace")).hexdigest()


def as_list(v) -> list:
    if v is None:
        return []
    return list(v) if isinstance(v, (list, tuple, set, frozenset)) else [v]


def key_number(key: str) -> int | None:
    m = KEY_RE.match(key or "")
    if not m or m.group("ns") != "QPS":
        return None
    n = re.fullmatch(r"W(\d{3})", m.group("id"))
    return int(n.group(1)) if n else None


def violation(code: str, key: str, repos, detail: str, severity: str = "error") -> dict:
    return {
        "code": code,
        "severity": severity,
        "key": key,
        "repos": sorted(set(as_list(repos))),
        "detail": detail,
    }


def slug_of(name: str, rules: dict) -> str | None:
    m = rules["_name_re"].match(name or "")
    return m.group("slug") if m else None


def _overlaps(a: str, b: str) -> bool:
    a, b = a.rstrip("/") + "/", b.rstrip("/") + "/"
    return a.startswith(b) or b.startswith(a)


def validate_claims(
    doc: dict, rules: dict, repo: str | None = None, private: bool = False
) -> list[dict]:
    """Rule checks that a single repo can run on its own claims file."""
    out: list[dict] = []
    repo = repo or (doc or {}).get("repo") or "?"
    if not isinstance(doc, dict) or doc.get("schema") != rules["claims_schema"]:
        return [
            violation(
                "C0_SCHEMA", "-", repo, f"schema must be {rules['claims_schema']}"
            )
        ]
    if repo != "?" and doc.get("repo") not in (None, repo):
        out.append(
            violation(
                "C0_REPO",
                "-",
                repo,
                "claims file 'repo' does not match the repository it lives in",
            )
        )
    cn, al = rules["canonical_name"], rules["alias"]
    statuses = set(rules["status_enum"])
    seen_keys: collections.Counter = collections.Counter()
    owned = []
    for c in as_list(doc.get("owns")):
        key = str(c.get("key", ""))
        seen_keys[key] += 1
        km = KEY_RE.match(key)
        if not km:
            out.append(
                violation(
                    "C1_KEY", key or "-", repo, "key must be <NS>:<id>, e.g. QPS:W364"
                )
            )
            continue
        name = str(c.get("name", ""))
        shown = "<private>" if private else name
        if km.group("ns") in cn["namespaces"]:
            m = rules["_name_re"].match(name)
            if not m or len(name) > cn["max_length"]:
                out.append(
                    violation(
                        "C2_NAME",
                        key,
                        repo,
                        f"name {shown!s} must match {cn['pattern']} and be <= {cn['max_length']} chars",
                    )
                )
            else:
                if cn.get("number_must_match_key") and int(
                    m.group("num")
                ) != key_number(key):
                    out.append(
                        violation(
                            "C3_NAME_NUMBER",
                            key,
                            repo,
                            "the number in the name must equal the key number",
                        )
                    )
                bad = set(m.group("slug").split("_")) & set(cn["reserved_slug_tokens"])
                if bad:
                    out.append(
                        violation(
                            "C4_RESERVED",
                            key,
                            repo,
                            f"slug uses reserved tokens {sorted(bad)}",
                        )
                    )
        elif name and name != km.group("id"):
            out.append(
                violation(
                    "C2_NAME",
                    key,
                    repo,
                    f"namespace {km.group('ns')} keeps its native id as name",
                )
            )
        if c.get("status") not in statuses:
            out.append(
                violation(
                    "C5_STATUS", key, repo, f"status must be one of {sorted(statuses)}"
                )
            )
        aliases = [str(a) for a in as_list(c.get("aliases"))]
        if len(aliases) > al["max_per_wave"]:
            out.append(
                violation(
                    "C6_ALIAS", key, repo, f"at most {al['max_per_wave']} aliases"
                )
            )
        own_num = key_number(key)
        for a in aliases:
            shown_a = "<private>" if private else a
            if not rules["_alias_re"].match(a) or len(a) > al["max_length"]:
                out.append(
                    violation(
                        "C6_ALIAS",
                        key,
                        repo,
                        f"alias {shown_a} must match {al['pattern']} and be <= {al['max_length']} chars",
                    )
                )
            foreign = {int(n) for n in NUM_IN_TEXT.findall(a)} - (
                {own_num} if own_num is not None else set()
            )
            if foreign and al["foreign_wave_numbers"] == "forbidden":
                out.append(
                    violation(
                        "C7_ALIAS_NUMBER",
                        key,
                        repo,
                        f"alias {shown_a} names another wave number",
                    )
                )
        for p in as_list(c.get("parent")):
            if not KEY_RE.match(str(p)):
                out.append(
                    violation("C1_KEY", key, repo, "parent must be a canonical key")
                )
        owned.append(
            {
                "key": key,
                "name": name,
                "aliases": aliases,
                "parents": [str(p) for p in as_list(c.get("parent"))],
                "paths": [str(p) for p in as_list(c.get("paths"))],
            }
        )
    for key, n in seen_keys.items():
        if n > 1:
            out.append(
                violation(
                    "D1_DUP_OWNER",
                    key,
                    repo,
                    "key claimed more than once in the same file",
                )
            )
    # Fail closed for collisions within this member's own file. The federation
    # roll-up also checks across repositories, but cannot be the only gate.
    canonical_by_tag = collections.defaultdict(set)
    aliases_by_tag = collections.defaultdict(list)
    for row in owned:
        canonical_by_tag[tag(row["name"])].add(row["key"])
        for alias in row["aliases"]:
            aliases_by_tag[tag(alias)].append(row["key"])
    for alias_tag, keys in aliases_by_tag.items():
        if len(keys) > 1 or canonical_by_tag.get(alias_tag):
            for key in sorted(set(keys)):
                out.append(
                    violation(
                        "D3_ALIAS_CLASH",
                        key,
                        repo,
                        "alias duplicates another alias or a canonical name in this claims file",
                    )
                )

    roles = set(rules["participant_roles"])
    for p in as_list(doc.get("participates")):
        key = str(p.get("key", ""))
        if not KEY_RE.match(key):
            out.append(
                violation(
                    "C1_KEY", key or "-", repo, "participates key must be <NS>:<id>"
                )
            )
        if p.get("role") not in roles:
            out.append(
                violation(
                    "C8_ROLE", key or "-", repo, f"role must be one of {sorted(roles)}"
                )
            )
        if key in seen_keys:
            out.append(
                violation(
                    "C8_ROLE",
                    key,
                    repo,
                    "a repo cannot own and participate in the same key",
                )
            )
    # D5: path boundaries inside one repo
    for i, a in enumerate(owned):
        for b in owned[i + 1 :]:
            for pa in a["paths"]:
                for pb in b["paths"]:
                    if _overlaps(pa, pb):
                        inner, outer = (a, b) if len(pa) >= len(pb) else (b, a)
                        if outer["key"] not in inner["parents"]:
                            out.append(
                                violation(
                                    "D5_PATH_OVERLAP",
                                    inner["key"],
                                    repo,
                                    f"path boundary overlaps {outer['key']} without declaring it as parent",
                                )
                            )
    return out


def rollup(
    claim_sets: dict[str, tuple[dict, bool]],
    observed: dict[str, set[str]],
    lineage: set[tuple[str, str]],
    rules: dict,
) -> tuple[dict, list[dict], dict]:
    """Merge every repo's claims; return (per-key claims, violations, census)."""
    violations: list[dict] = []
    owners: dict[str, list[tuple[str, dict, bool]]] = collections.defaultdict(list)
    participants: dict[str, dict[str, str]] = collections.defaultdict(dict)
    for repo, (doc, private) in sorted(claim_sets.items()):
        violations += validate_claims(doc, rules, repo, private)
        if not isinstance(doc, dict):
            continue
        for c in as_list(doc.get("owns")):
            owners[str(c.get("key"))].append((repo, c, private))
        for p in as_list(doc.get("participates")):
            participants[str(p.get("key"))][repo] = str(p.get("role"))
    parents = collections.defaultdict(set)
    for child, parent in lineage:
        parents[child].add(parent)
    for key, lst in owners.items():
        for _, c, _ in lst:
            parents[key].update(str(p) for p in as_list(c.get("parent")))

    claims: dict[str, dict] = {}
    claimants: dict[str, set[str]] = {}
    name_index: dict[str, set[str]] = collections.defaultdict(set)
    alias_index: dict[str, set[str]] = collections.defaultdict(set)
    slug_index: dict[str, set[str]] = collections.defaultdict(set)
    for key, lst in sorted(owners.items()):
        claimants[key] = {r for r, _, _ in lst}
        # Every claimant is indexed, so a contested key cannot hide its names or aliases.
        for repo, c, private in lst:
            name_index[digest(str(c.get("name", "")))].add(key)
            for a in as_list(c.get("aliases")):
                alias_index[digest(str(a))].add(key)
            s = slug_of(str(c.get("name", "")), rules)
            if s:
                slug_index[digest(s)].add(key)
        if len(lst) > 1:
            violations.append(
                violation(
                    "D1_DUP_OWNER",
                    key,
                    claimants[key],
                    "more than one repo owns this key",
                )
            )
            claims[key] = {
                "owner": "CONTESTED",
                "claimants": sorted(claimants[key]),
                "status": None,
            }
            if participants.get(key):
                claims[key]["participants"] = dict(sorted(participants[key].items()))
            continue
        repo, c, private = lst[0]
        name = str(c.get("name", ""))
        aliases = [str(a) for a in as_list(c.get("aliases"))]
        rec = {"owner": repo, "status": c.get("status")}
        if private:
            rec["name_sha256"] = digest(name)
            if aliases:
                rec["alias_sha256"] = sorted(digest(a) for a in aliases)
            rec["path_count"] = len(as_list(c.get("paths")))
        else:
            rec["name"] = name
            if aliases:
                rec["aliases"] = aliases
            if c.get("paths"):
                rec["paths"] = [str(p) for p in as_list(c.get("paths"))]
        if as_list(c.get("parent")):
            rec["parent"] = [str(p) for p in as_list(c.get("parent"))]
        if participants.get(key):
            rec["participants"] = dict(sorted(participants[key].items()))
        claims[key] = rec

    for d, keys in name_index.items():
        if len(keys) > 1:
            for k in sorted(keys):
                violations.append(
                    violation(
                        "D2_NAME_REUSE",
                        k,
                        claimants[k],
                        "canonical name also used by " + ", ".join(sorted(keys - {k})),
                    )
                )
    for d, keys in alias_index.items():
        clash = keys | name_index.get(d, set())
        if len(clash) > 1:
            for k in sorted(keys):
                violations.append(
                    violation(
                        "D3_ALIAS_CLASH",
                        k,
                        claimants[k],
                        "alias also resolves to " + ", ".join(sorted(clash - {k})),
                    )
                )
    for d, keys in slug_index.items():
        if len(keys) < 2:
            continue
        chain = sorted(keys, key=lambda k: (key_number(k) or 0, k))
        for position, later in enumerate(chain[1:], start=1):
            if not (parents[later] & set(chain[:position])):
                violations.append(
                    violation(
                        "D4_SLUG_NO_LINEAGE",
                        later,
                        claimants[later],
                        "slug carried forward without declaring an earlier holder as parent",
                    )
                )

    # Numbering: no backfilling unobserved holes.
    observed_nums = [key_number(k) for k in observed if key_number(k) is not None]
    top = max(observed_nums, default=0)
    for key, rec in claims.items():
        n = key_number(key)
        if n is not None and key not in observed and n < top:
            violations.append(
                violation(
                    "N1_BACKFILL",
                    key,
                    claimants[key],
                    f"unobserved number below the observed maximum W{top:03d}",
                )
            )

    # Overlap census: repos that touch an owned key without declaring a role.
    undeclared = 0
    for key, rec in claims.items():
        for r in sorted(
            observed.get(key, set()) - claimants[key] - set(rec.get("participants", {}))
        ):
            undeclared += 1
            violations.append(
                violation(
                    "O1_UNDECLARED_PARTICIPANT",
                    key,
                    r,
                    f"observed in {r} but {r} declares no role",
                    "warning",
                )
            )
    for key, parts in participants.items():
        if key not in claims:
            violations.append(
                violation(
                    "O2_ORPHAN_PARTICIPATION",
                    key,
                    list(parts),
                    "participation in a key nobody owns",
                    "warning",
                )
            )

    claimed_nums = [key_number(k) for k in claims if key_number(k) is not None]
    sev = collections.Counter(v["severity"] for v in violations)
    census = {
        "claims_files": len(claim_sets),
        "claimed_keys": len(claims),
        "observed_keys": len(observed),
        "unclaimed_observed": len(set(observed) - set(claims)),
        "claimed_unobserved": len(set(claims) - set(observed)),
        "multi_repo_observed": sum(1 for v in observed.values() if len(v) > 1),
        "undeclared_participants": undeclared,
        "owners": dict(
            sorted(collections.Counter(r["owner"] for r in claims.values()).items())
        ),
        "contested_keys": sum(1 for r in claims.values() if r["owner"] == "CONTESTED"),
        "next_free": {
            "QPS": f"W{max(claimed_nums + observed_nums, default=9) + 1:03d}"
        },
        "violations": {
            "error": sev.get("error", 0),
            "warning": sev.get("warning", 0),
            "by_code": dict(
                sorted(collections.Counter(v["code"] for v in violations).items())
            ),
        },
    }
    violations.sort(
        key=lambda v: (v["severity"] != "error", v["code"], v["key"], v["repos"])
    )
    return claims, violations, census


def _wave_segment(anchor: str, number: int) -> tuple[str, str] | None:
    """(path prefix up to the wave-specific segment, that segment) or None if the anchor is shared."""
    seg = anchor.rstrip("/").split("/")
    for i, s in enumerate(seg):
        if any(
            int(n) == number
            for n in re.findall(r"(?<![0-9])[Ww]?0*(\d{1,3})(?![0-9])", s)
        ):
            return "/".join(seg[: i + 1]) + "/", s
    return None


VERSION_TOKEN = re.compile(r"^(V\d+|\d+)$")


def _slug_from_text(text: str, number: int, rules: dict) -> str | None:
    s = re.sub(r"[^A-Za-z0-9]+", "_", text).upper()
    words = [w for w in s.split("_") if w]
    keep = [
        w
        for w in words
        if w not in {"QPS", f"W{number}", f"W{number:03d}", f"W0{number}"}
        and not VERSION_TOKEN.match(w)
        and w not in rules["canonical_name"]["reserved_slug_tokens"]
        and not re.fullmatch(r"W\d{1,3}[A-Z]?", w)
    ]
    slug = "_".join(keep[:6])[:36].strip("_")
    return slug or None


def _slug_from_tree(
    files: list[str], prefix: str, number: int, rules: dict
) -> str | None:
    """Most frequent descriptive stem among the wave's own records under its boundary."""
    own = re.compile(r"(?<![0-9A-Za-z])W0*" + str(number) + r"(?![0-9])", re.IGNORECASE)
    stems: collections.Counter = collections.Counter()
    for f in files:
        if not f.startswith(prefix):
            continue
        rest = f[len(prefix) :].split("/")
        name = rest[-1].rsplit(".", 1)[0]
        if own.search(name):
            s = _slug_from_text(name, number, rules)
            if s:
                stems[s] += 3  # a record named after the wave is the strongest signal
        if len(rest) > 1:
            s = _slug_from_text(rest[0], number, rules)
            if s:
                stems[s] += 1
    return stems.most_common(1)[0][0] if stems else None


def propose(
    register: dict, repo: str, rules: dict | None = None, repo_path: Path | None = None
) -> dict:
    """Draft claims for keys where this repo holds the most observed paths.

    Only rule-conforming claims are proposed: a path boundary is proposed only when
    the anchor segment carries the wave's own number, and a name only when a slug can
    be read from that segment and is unique in the draft. Everything else is listed
    under needs_name / contested_ties for the owner. Proposals never set lineage.
    """
    rules = rules or load_naming_rules()
    owns, contested, needs_name = [], [], []
    slugs: collections.Counter = collections.Counter()
    drafts = []
    files = None
    if repo_path is not None:
        out = subprocess.run(
            ["git", "-C", str(repo_path), "ls-tree", "-r", "--name-only", "-z", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        files = [f for f in out.split("\0") if f]
    for e in register.get("waves", []):
        repos = e.get("repos", {})
        if (
            repo not in repos
            or e["namespace"] != "QPS"
            or e.get("confidence") != "exact"
        ):
            continue
        mine, best = repos[repo]["paths"], max(v["paths"] for v in repos.values())
        if mine < best:
            continue
        if sum(1 for v in repos.values() if v["paths"] == best) > 1:
            contested.append(e["key"])
            continue
        num = key_number(e["key"])
        ws = _wave_segment(repos[repo].get("anchor", ""), num)
        slug = None
        if ws:
            slug = _slug_from_text(ws[1], num, rules)
        if not slug and ws and files is not None:
            slug = _slug_from_tree(files, ws[0], num, rules)
        drafts.append((e, num, ws, slug))
        if slug:
            slugs[slug] += 1
    for e, num, ws, slug in drafts:
        if not slug or slugs[slug] > 1:
            needs_name.append(e["key"])
            continue
        claim = {"key": e["key"], "name": f"W{num:03d}_{slug}", "status": "ACTIVE"}
        if ws:
            claim["paths"] = [ws[0]]
        owns.append(claim)
    return {
        "schema": rules["claims_schema"],
        "repo": repo,
        "owns": owns,
        "participates": [],
        "_proposal": {
            "contested_ties": contested,
            "needs_name": needs_name,
            "note": "Draft from the observed census. The owner confirms names, status, paths, parents.",
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate")
    v.add_argument("path", nargs="?", default=CLAIMS_PATH)
    v.add_argument("--rules", default=str(RULES_FILE))
    v.add_argument(
        "--expected-repo",
        required=True,
        help="independently supplied owner/name, never read from the claims file",
    )
    v.add_argument("--private", action="store_true", help="redact names in messages")
    p = sub.add_parser("propose")
    p.add_argument("--repo", required=True)
    p.add_argument("--register", default=str(REGISTER_FILE))
    p.add_argument(
        "--repo-path",
        help="checkout of the owning repo (names are read from its own records)",
    )
    a = ap.parse_args(argv)
    if a.cmd == "validate":
        rules = load_naming_rules(Path(a.rules))
        doc = yaml.safe_load(Path(a.path).read_text(encoding="utf-8"))
        found = validate_claims(doc, rules, a.expected_repo, a.private)
        for f in found:
            print(f"{f['severity'].upper()} {f['code']} {f['key']}: {f['detail']}")
        errors = sum(1 for f in found if f["severity"] == "error")
        print(
            f"wave claims: {len((doc or {}).get('owns') or [])} owned, {errors} errors"
        )
        return 1 if errors else 0
    register = yaml.safe_load(Path(a.register).read_text(encoding="utf-8"))
    draft = propose(
        register, a.repo, repo_path=Path(a.repo_path) if a.repo_path else None
    )
    sys.stdout.write(yaml.safe_dump(draft, sort_keys=False, width=120))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
